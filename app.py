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

# 导入所有服务模块
from db_service import *
from payment_service import create_checkout_session, create_portal_session, construct_event
from image_generator import generate_8_images
from zine_generator import create_foldable_book, create_assets_zip
from story_generator import generate_story_json

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MagicZine AI API v2.1")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 鉴权 ---
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
    user_id = authorization.split(" ")[1]
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=401, detail="User not found")
    return profile

async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# --- Models ---
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

# --- Routes ---

@app.get("/health")
def health():
    return {"status": "ok"}

# Webhooks
@app.post("/api/webhooks/clerk")
async def clerk_webhook(request: Request):
    payload = await request.json()
    if payload["type"] == "user.created":
        data = payload["data"]
        create_user_profile(data["id"], data["email_addresses"][0]["email_address"], data.get("username"), data.get("image_url"))
    return {"status": "ok"}

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
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
                update_subscription_tier(uid, plan, session.get('customer'))
                amt = 500 if plan == 'starter' else 1000
                add_credits(uid, amt, f"{plan} Sub", "sub_grant")
    return {"status": "ok"}

# User & Resources
@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.get("/api/user/assets")
def my_assets(project_id: Optional[str]=None, scope: Optional[str]=None, user: dict = Depends(get_current_user)):
    if scope == "all" and user["tier"] == "free":
        raise HTTPException(403, "Pro required for history")
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    # [已修复] 真实查询数据库
    is_pro = user["tier"] in ["starter", "pro"]
    return get_system_resources("sticker", is_pro)

# Project
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
    if not p: raise HTTPException(404)
    return p

@app.put("/api/projects/{id}")
def save_proj(id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url)
    return {"status": "saved"}

# Gen & Tools
@app.post("/api/generate/story")
@limiter.limit("20/minute")
def gen_story(request: Request, req: StoryGenRequest, user: dict = Depends(get_current_user)):
    try:
        return generate_story_json(req.topic)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/generate/images")
@limiter.limit("10/minute")
async def gen_images(request: Request, req: ImageGenRequest, user: dict = Depends(get_current_user)):
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")
        
    cost = len(req.prompts) * 5
    try:
        deduct_credits_atomic(user["id"], cost, "generation", f"Gen {len(req.prompts)}")
    except Exception:
        raise HTTPException(402, "Insufficient credits")
        
    urls, _ = await generate_8_images(req.prompts)
    for url, prompt in zip(urls, req.prompts):
        save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
    return {"image_urls": urls, "balance": user["credits"] - cost}

@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
def ocr_tool(request: Request, user: dict = Depends(get_current_user)):
    """[已补全] 智能识图接口 (Mock)"""
    if user["tier"] == "free":
        raise HTTPException(403, "Pro feature only")
    # 实际对接 GPT-4o-Vision
    return {"text": "Mock OCR Result: A cat sitting on a mat."}

# Export
@app.post("/api/generate/pdf")
def dl_pdf(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    proj = get_project_detail(req.project_id, user["id"])
    if req.current_hash != proj.get("last_downloaded_hash"):
        try:
            deduct_credits_atomic(user["id"], 50, "download_pdf", "PDF Export")
            # 应该更新 Hash
            supabase.table("projects").update({"last_downloaded_hash": req.current_hash}).eq("id", req.project_id).execute()
        except:
            raise HTTPException(402, "Insufficient credits")
            
    buf = BytesIO()
    # 注意：为了体现编辑效果，前端应将 Canvas 导出为图片并传入 image_urls，texts 传空
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)
    log_activity(user["id"], "download_pdf")
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=zine.pdf"})

@app.post("/api/export/zip")
def dl_zip(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade required")
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=assets.zip"})

# Pay & Support
@app.post("/api/payment/checkout")
def pay(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    return {"url": create_checkout_session(user["id"], req.plan_type)}

@app.post("/api/payment/portal")
def portal(user: dict = Depends(get_current_user)):
    if not user.get("stripe_customer_id"): raise HTTPException(400, "No sub")
    return {"url": create_portal_session(user["id"], user["stripe_customer_id"])}

@app.post("/api/support/email")
def ticket(req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    create_support_ticket(user["id"], req.email, req.message)
    return {"status": "ok"}

# Admin
@app.get("/api/admin/users")
def adm_users(query: str, admin: dict = Depends(require_admin)):
    return search_users(query)

@app.get("/api/admin/user/{uid}")
def adm_audit(uid: str, admin: dict = Depends(require_admin)):
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

@app.get("/api/user/history")
def get_history(page: int = 1, user: dict = Depends(get_current_user)):
    """获取积分流水历史"""
    try:
        return get_credit_history(user["id"], page)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/projects/{id}")
def delete_proj(id: str, user: dict = Depends(get_current_user)):
    """删除项目 (软删除)"""
    try:
        soft_delete_project(id, user["id"])
        return {"status": "deleted"}
    except Exception:
        raise HTTPException(404, "Project not found")