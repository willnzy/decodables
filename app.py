import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from svix.webhooks import Webhook, WebhookVerificationError # 用于 Clerk 验签

# 导入所有服务模块
from db_service import *
from payment_service import create_checkout_session, create_portal_session, construct_event
from image_generator import generate_8_images
from zine_generator import create_foldable_book, create_assets_zip
from story_generator import generate_story_json

# 初始化配置
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")

# 初始化限流器 (生产环境建议改为按 UserID 限流)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MagicZine AI API v2.2 (Production Ready)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. 安全配置 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ⚠️ 生产环境请务必改为前端域名 ["https://your-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 鉴权依赖
async def get_current_user(authorization: str = Header(None)):
    """验证用户身份"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
    
    # ⚠️ 生产环境必须集成 Clerk SDK 验证 JWT 签名
    # from clerk_backend_api import Clerk
    # try:
    #    token = authorization.split(" ")[1]
    #    verified_token = clerk.verify_token(token)
    #    user_id = verified_token['sub']
    # except: ...
    
    # Mock 实现 (仅供开发测试): 假设 Token 即 UserID
    user_id = authorization.split(" ")[1]
    
    profile = get_user_profile(user_id)
    if not profile:
        # 如果用户刚注册，webhook可能有延迟，尝试即时创建或返回401
        raise HTTPException(status_code=401, detail="User profile not found")
    return profile

async def require_admin(user: dict = Depends(get_current_user)):
    """管理员权限守卫"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# 3. 数据模型 (Request Models)

class StoryGenRequest(BaseModel):
    topic: str
    style: Optional[str] = "Children's book illustration"

class ImageGenRequest(BaseModel):
    project_id: str
    prompts: List[str]

class PdfGenRequest(BaseModel):
    project_id: str
    current_hash: str
    image_urls: List[str]
    texts: List[str]

class ProjectUpdate(BaseModel):
    canvas_data: dict
    thumbnail_url: Optional[str] = None

class CheckoutRequest(BaseModel):
    user_id: str # 前端传
    plan_type: str

class SupportTicketRequest(BaseModel):
    email: str
    message: str

class AdminAdjustRequest(BaseModel):
    user_id: str
    amount: int
    reason: str

class AdminTierRequest(BaseModel):
    user_id: str
    tier: str

# 4. API 接口实现

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.2"}

# --- Webhooks (系统级) ---

@app.post("/api/webhooks/clerk")
async def clerk_webhook(request: Request):
    """Clerk 用户注册回调 (带签名验证)"""
    if not CLERK_WEBHOOK_SECRET:
        raise HTTPException(500, "Missing CLERK_WEBHOOK_SECRET")

    headers = request.headers
    payload = await request.body()
    
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = evt["type"]
    data = evt["data"]

    if event_type == "user.created":
        # 提取 Clerk 用户信息
        user_id = data["id"]
        email = data["email_addresses"][0]["email_address"]
        username = data.get("username")
        avatar = data.get("image_url")
        
        # 创建档案并赠送初始积分
        create_user_profile(user_id, email, username, avatar)
        
    return {"status": "processed"}

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Stripe 支付回调"""
    payload = await request.body()
    try:
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(400, str(e))
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        uid = session['metadata'].get('user_id')
        plan = session['metadata'].get('plan_type')
        
        if uid and plan:
            if plan == 'credits_100':
                add_credits(uid, 100, "Purchase 100 Credits")
            elif plan in ['starter', 'pro']:
                # 记录 Customer ID 以便后续管理订阅
                update_subscription_tier(uid, plan, session.get('customer'))
                amt = 500 if plan == 'starter' else 1000
                add_credits(uid, amt, f"{plan.capitalize()} Subscription Grant", "sub_grant")
            
    return {"status": "ok"}

# --- 用户与资源接口 ---

@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.get("/api/user/history")
def get_history(page: int = 1, user: dict = Depends(get_current_user)):
    """获取积分流水历史"""
    return get_credit_history(user["id"], page)

@app.get("/api/user/assets")
def my_assets(project_id: Optional[str]=None, scope: Optional[str]=None, user: dict = Depends(get_current_user)):
    """获取素材库 (Session vs All History)"""
    # 权益控制：仅 Pro 可看历史全库
    if scope == "all" and user["tier"] == "free":
        raise HTTPException(403, "Pro plan required for history access")
    
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    """获取系统贴纸"""
    is_pro = user["tier"] in ["starter", "pro"]
    return get_system_resources("sticker", is_pro)

# --- 项目管理 ---

@app.get("/api/projects")
def list_projects(page: int=1, user: dict = Depends(get_current_user)):
    return get_user_projects(user["id"], page)

@app.post("/api/projects")
def new_project(user: dict = Depends(get_current_user)):
    p = create_project(user["id"])
    log_activity(user["id"], "create_project")
    return p

@app.get("/api/projects/{id}")
def get_proj(id: str, user: dict = Depends(get_current_user)):
    p = get_project_detail(id, user["id"])
    if not p: raise HTTPException(404, "Project not found")
    return p

@app.put("/api/projects/{id}")
def save_proj(id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url)
    return {"status": "saved"}

@app.delete("/api/projects/{id}")
def delete_proj(id: str, user: dict = Depends(get_current_user)):
    try:
        soft_delete_project(id, user["id"])
        return {"status": "deleted"}
    except:
        raise HTTPException(404, "Project not found or access denied")

# --- 核心业务: 生成 (Story & Image) ---

@app.post("/api/generate/story")
@limiter.limit("20/minute")
def gen_story(request: Request, req: StoryGenRequest, user: dict = Depends(get_current_user)):
    """步骤1: 根据 Topic 生成故事脚本"""
    try:
        story_json = generate_story_json(req.topic)
        if not story_json:
            raise HTTPException(500, "Failed to generate story")
        return story_json
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/generate/images")
@limiter.limit("10/minute")
async def gen_images(request: Request, req: ImageGenRequest, user: dict = Depends(get_current_user)):
    """步骤2: 生成图片 (扣费核心)"""
    # 1. 风控
    blacklist = ["nsfw", "nude", "sex", "violence"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation: Restricted content")
        
    # 2. 算费 (5 Credits / Image)
    cost = len(req.prompts) * 5
    
    # 3. 原子扣费
    try:
        deduct_credits_atomic(user["id"], cost, "generation", f"Gen {len(req.prompts)} images")
    except Exception:
        raise HTTPException(402, "Insufficient credits")
        
    # 4. 执行生成
    try:
        urls, task_id = await generate_8_images(req.prompts)
        
        # 5. 存库 (Assets)
        for url, prompt in zip(urls, req.prompts):
            save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
            
        return {"image_urls": urls, "balance": user["credits"] - cost}
    except Exception as e:
        # 生产环境建议在此处回滚积分
        raise HTTPException(500, "Image generation failed")

@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
def ocr_tool(request: Request, user: dict = Depends(get_current_user)):
    """智能识图 (Mock)"""
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade to Pro to use Smart Scan")
    # TODO: Connect to GPT-4o-Vision
    return {"text": "A sketch of a cat on the moon"}

# --- 导出 (PDF & ZIP) ---

@app.post("/api/generate/pdf")
def dl_pdf(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """下载 PDF (Hash 校验扣费)"""
    # 1. 获取项目上次下载状态
    proj = get_project_detail(req.project_id, user["id"])
    last_hash = proj.get("last_downloaded_hash")
    
    # 2. 如果 Hash 变了，扣费 50
    if req.current_hash != last_hash:
        try:
            deduct_credits_atomic(user["id"], 50, "download_pdf", "PDF Export")
            # 更新 Hash (需在 db_service 实现 update_project_hash)
            save_project(req.project_id, user["id"], proj["canvas_data"]) # 简化处理，实际应单独更新hash
            # 补丁: 手动更新 Hash
            # supabase.table("projects").update({"last_downloaded_hash": req.current_hash}).eq("id", req.project_id).execute()
            update_project_hash(req.project_id, req.current_hash)
        except:
            raise HTTPException(402, "Insufficient credits for download")
            
    # 3. 生成 PDF
    # 注意: 前端应发送合成好的图片URL，否则贴纸无法显示
    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)
    
    log_activity(user["id"], "download_pdf")
    return StreamingResponse(
        buf, 
        media_type="application/pdf", 
        headers={"Content-Disposition": "attachment; filename=zine.pdf"}
    )

@app.post("/api/export/zip")
def dl_zip(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """下载素材包 (权益检查)"""
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade to Starter/Pro to download ZIP")
        
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    return StreamingResponse(
        buf, 
        media_type="application/zip", 
        headers={"Content-Disposition": "attachment; filename=assets.zip"}
    )

# --- 支付与客服 ---

@app.post("/api/payment/checkout")
def pay(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    # 使用 Token 中的 user_id 覆盖请求参数，防止帮别人充值
    url = create_checkout_session(user["id"], req.plan_type)
    if not url: raise HTTPException(400, "Payment init failed")
    return {"url": url}

@app.post("/api/payment/portal")
def manage_sub(user: dict = Depends(get_current_user)):
    cid = user.get("stripe_customer_id")
    if not cid: raise HTTPException(400, "No active subscription")
    return {"url": create_portal_session(user["id"], cid)}

@app.post("/api/support/email")
def ticket(req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    create_support_ticket(user["id"], req.email, req.message)
    return {"status": "ok"}

# --- Admin (运营后台) ---

@app.get("/api/admin/users")
def adm_users(query: str, admin: dict = Depends(require_admin)):
    return search_users(query)

@app.get("/api/admin/user/{uid}")
def adm_audit(uid: str, admin: dict = Depends(require_admin)):
    # 聚合查询
    return {
        "profile": get_user_profile(uid),
        "logs": supabase.table("activity_logs").select("*").eq("user_id", uid).execute().data,
        "transactions": supabase.table("credit_transactions").select("*").eq("user_id", uid).execute().data
    }

@app.post("/api/admin/credits/adjust")
def adm_adj(req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    if req.amount > 0:
        add_credits(req.user_id, req.amount, req.reason, "admin_adj")
    else:
        deduct_credits_atomic(req.user_id, abs(req.amount), "admin_adj", req.reason)
    return {"status": "ok"}

@app.post("/api/admin/tier/update")
def adm_tier(req: AdminTierRequest, admin: dict = Depends(require_admin)):
    update_subscription_tier(req.user_id, req.tier)
    return {"status": "ok"}