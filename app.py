import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import json

# 导入服务模块
from db_service import *
from payment_service import create_checkout_session, construct_event
from image_generator import generate_8_images
from zine_generator import create_foldable_book
# from story_generator import generate_story_json # 按需保留

app = FastAPI(title="MagicZine AI API v1.9")

# ==========================
# 0. 配置与中间件
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境请修改
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# 1. 鉴权依赖 (Mock)
# ==========================

async def get_current_user(authorization: str = Header(None)):
    """
    验证 Bearer Token (Clerk)。
    此处为简化版，实际需使用 clerk-sdk-python 验证 JWT 签名。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    
    # TODO: 集成 Clerk SDK 验证 token
    # user_data = clerk.verify(token)
    # user_id = user_data['sub']
    # role = user_data['public_metadata'].get('role', 'user')
    
    # 模拟返回 (假设 Token 就是 UserID)
    user_id = token 
    
    # 查库获取完整信息
    profile = get_user_profile(user_id)
    if not profile:
         # 可能是新用户，但 Webhook 还没到，临时放行或报错
         raise HTTPException(status_code=401, detail="User profile not found")
    
    return profile

async def require_admin(user: dict = Depends(get_current_user)):
    """Admin 守卫"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==========================
# 2. 数据模型 (Pydantic)
# ==========================

class ProjectCreate(BaseModel):
    pass # 创建空项目无需参数

class ProjectUpdate(BaseModel):
    canvas_data: dict
    thumbnail_url: Optional[str] = None

class ImageGenRequest(BaseModel):
    project_id: str
    prompts: List[str] # 对应要生成的页面 Prompt

class PdfGenRequest(BaseModel):
    project_id: str
    current_hash: str
    image_urls: List[str]
    texts: List[str]

class CheckoutRequest(BaseModel):
    plan_type: str # 'credits_100', 'starter', 'pro'

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

# ==========================
# 3. 接口实现
# ==========================

# --- 系统 ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Webhooks (无鉴权，验签名) ---
@app.post("/api/webhooks/clerk")
async def clerk_webhook(request: Request):
    # TODO: 验证 Svix 签名
    payload = await request.json()
    if payload["type"] == "user.created":
        data = payload["data"]
        user_id = data["id"]
        email = data["email_addresses"][0]["email_address"]
        create_user_profile(user_id, email, data.get("username"), data.get("image_url"))
    return {"status": "processed"}

@app.post("/api/webhooks/stripe")
async def stripe_webhook_endpoint(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 逻辑迁移至 Payment Service 或在此处理
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan_type")
        
        if plan == "credits_100":
            add_credits(user_id, 100, "Purchase 100 Credits")
        elif plan in ["starter", "pro"]:
            update_subscription_tier(user_id, plan, session.get("customer"))
            amount = 500 if plan == "starter" else 1000
            add_credits(user_id, amount, f"{plan.capitalize()} Subscription Grant", "sub_grant")
            
    elif event['type'] == 'invoice.payment_succeeded':
        # 续费逻辑
        # 需要根据 customer_id 反查用户 (此处略，建议在 Profile 存 stripe_sub_id)
        pass 

    return {"status": "success"}

# --- 用户 ---
@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "credits": user["credits"],
        "tier": user["tier"],
        "avatar_url": user["avatar_url"]
    }

@app.get("/api/user/history")
def get_history(page: int = 1, user: dict = Depends(get_current_user)):
    # 简单分页实现
    start = (page-1)*20
    res = supabase.table("credit_transactions")\
        .select("*").eq("user_id", user["id"])\
        .order("created_at", desc=True).range(start, start+19).execute()
    return res.data

@app.get("/api/user/assets")
def get_user_assets(project_id: Optional[str] = None, scope: Optional[str] = None, user: dict = Depends(get_current_user)):
    # 权益检查
    if scope == "all" and user["tier"] == "free":
         raise HTTPException(status_code=403, detail="History access requires Pro plan")
    
    # 若 scope != all, 必须传 project_id
    target_project = project_id if scope != "all" else None
    return get_assets(user["id"], target_project)

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    # 简单权限过滤
    query = supabase.table("system_resources").select("*").eq("type", "sticker")
    if user["tier"] == "free":
        query = query.eq("is_pro_only", False)
    return query.execute().data

# --- 项目 ---
@app.get("/api/projects")
def list_projects(page: int = 1, user: dict = Depends(get_current_user)):
    return get_user_projects(user["id"], page)

@app.post("/api/projects")
def create_new_project(user: dict = Depends(get_current_user)):
    project = create_project(user["id"])
    log_activity(user["id"], "create_project")
    return project

@app.get("/api/projects/{id}")
def get_project(id: str, user: dict = Depends(get_current_user)):
    proj = get_project_detail(id, user["id"])
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.put("/api/projects/{id}")
def update_project(id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url)
    return {"status": "saved"}

@app.delete("/api/projects/{id}")
def delete_project(id: str, user: dict = Depends(get_current_user)):
    supabase.table("projects").update({"is_deleted": True}).eq("id", id).eq("user_id", user["id"]).execute()
    return {"status": "deleted"}

# --- 核心业务: 生成 ---
@app.post("/api/generate/images")
async def generate_images(req: ImageGenRequest, user: dict = Depends(get_current_user)):
    """AI 生图: 风控 -> 扣费 -> 生图 -> 存库"""
    # 1. 风控 (Keyword Filter)
    blacklist = ["nsfw", "nude", "disney", "marvel"]
    for p in req.prompts:
        if any(w in p.lower() for w in blacklist):
            raise HTTPException(status_code=400, detail="Content Policy Violation")

    # 2. 计算费用 (每图 5 分)
    cost = len(req.prompts) * 5
    
    # 3. 原子扣费
    try:
        deduct_credits_atomic(user["id"], cost, "generation", f"Generate {len(req.prompts)} images")
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(status_code=402, detail="Insufficient credits")
        raise e

    # 4. 调用 AI (Fal.ai)
    try:
        # 复用原 image_generator 的逻辑，但需修改使其支持返回 URL 列表
        urls, _ = await generate_8_images(req.prompts) 
        
        # 5. 存入 Assets 表
        for url, prompt in zip(urls, req.prompts):
            save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
            
        return {"image_urls": urls, "balance_remaining": user["credits"] - cost}
        
    except Exception as e:
        # TODO: 失败应该退款 (Rollback credits)
        print(f"Gen Error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed")

@app.post("/api/tools/ocr")
def smart_scan(user: dict = Depends(get_current_user)):
    if user["tier"] not in ["pro"]:
        raise HTTPException(status_code=403, detail="Pro feature only")
    # TODO: Implement OpenAI Vision logic
    return {"message": "Mock OCR result"}

@app.post("/api/generate/pdf")
def download_pdf(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """下载 PDF: Hash 校验扣费"""
    # 1. 获取项目查看 Hash
    proj = get_project_detail(req.project_id, user["id"])
    last_hash = proj.get("last_downloaded_hash")
    
    # 2. 判断是否扣费
    if req.current_hash != last_hash:
        cost = 50
        try:
            deduct_credits_atomic(user["id"], cost, "download_pdf", "PDF Export")
        except Exception as e:
            raise HTTPException(status_code=402, detail="Insufficient credits")
        
        # 更新 Hash
        supabase.table("projects").update({"last_downloaded_hash": req.current_hash})\
            .eq("id", req.project_id).execute()
    
    # 3. 生成 PDF
    pdf_buffer = BytesIO()
    create_foldable_book(req.image_urls, req.texts, pdf_buffer)
    pdf_buffer.seek(0)
    
    # 4. 记录日志
    log_activity(user["id"], "download_pdf")
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=magic_zine.pdf"}
    )

# --- 支付 ---
@app.post("/api/payment/checkout")
def checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    url = create_checkout_session(user["id"], req.plan_type)
    log_activity(user["id"], "click_checkout", {"plan": req.plan_type})
    return {"url": url}

@app.post("/api/payment/portal")
def portal(user: dict = Depends(get_current_user)):
    # 需在 payment_service 实现 portal 逻辑
    return {"url": "https://billing.stripe.com/..."}

# --- 客服与管理 ---
@app.post("/api/support/email")
def support(req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    create_support_ticket(user["id"], req.email, req.message)
    # TODO: Send real email via SMTP/Resend
    return {"status": "ticket_created"}

@app.get("/api/admin/users")
def admin_search(query: str, admin: dict = Depends(require_admin)):
    return search_users(query)

@app.get("/api/admin/user/{uid}")
def admin_audit(uid: str, admin: dict = Depends(require_admin)):
    profile = get_user_profile(uid)
    txs = supabase.table("credit_transactions").select("*").eq("user_id", uid).execute().data
    logs = supabase.table("activity_logs").select("*").eq("user_id", uid).execute().data
    tickets = supabase.table("support_tickets").select("*").eq("user_id", uid).execute().data
    return {"profile": profile, "transactions": txs, "logs": logs, "tickets": tickets}

@app.post("/api/admin/credits/adjust")
def admin_adjust(req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    # 1. 调账
    if req.amount > 0:
        add_credits(req.user_id, req.amount, req.reason, "admin_adj")
    else:
        deduct_credits_atomic(req.user_id, abs(req.amount), "admin_adj", req.reason)
    
    # 2. 记运营日志
    supabase.table("support_tickets").insert({
        "category": "admin_adjustment_credits",
        "admin_id": admin["id"],
        "user_id": req.user_id,
        "content": f"Adjusted {req.amount}. Reason: {req.reason}",
        "status": "resolved"
    }).execute()
    return {"status": "ok"}

@app.post("/api/admin/tier/update")
def admin_tier(req: AdminTierRequest, admin: dict = Depends(require_admin)):
    update_subscription_tier(req.user_id, req.tier)
    # 记运营日志
    supabase.table("support_tickets").insert({
        "category": "admin_change_tier",
        "admin_id": admin["id"],
        "user_id": req.user_id,
        "content": f"Changed tier to {req.tier}",
        "status": "resolved"
    }).execute()
    return {"status": "ok"}