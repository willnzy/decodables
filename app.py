import os
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from io import BytesIO

# ==========================================
# 0. 模块导入
# ==========================================
# 导入原有的 AI 核心模块
from story_generator import generate_story_json
from image_generator import generate_8_images
from zine_generator import create_foldable_book

# [NEW] 导入数据库与支付服务模块 (请确保您已创建 db_service.py 和 payment_service.py)
from db_service import add_credits, update_subscription_tier
from payment_service import create_checkout_session, construct_event

# 初始化 FastAPI 应用
app = FastAPI(title="MagicZine AI API")

# ==========================================
# 1. 配置 CORS (跨域资源共享)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议改为您的前端域名 (如 https://your-app.vercel.app)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 定义数据模型 (Request Models)
# ==========================================

# [NEW] 支付请求模型
class CheckoutRequest(BaseModel):
    user_id: str      # 用户 ID (Clerk ID)
    plan_type: str    # 'credits_100', 'starter', 'pro'

# 原有模型
class StoryRequest(BaseModel):
    topic: str
    style: Optional[str] = "Children's book illustration" 

class ImageRequest(BaseModel):
    prompts: List[str]

class PdfRequest(BaseModel):
    image_urls: List[str]
    texts: List[str]

# ==========================================
# 3. API 接口定义
# ==========================================

@app.get("/")
def home():
    """健康检查接口"""
    return {"status": "ok", "message": "MagicZine AI API is running on Railway!"}

# ------------------------------------------
# [NEW] 💰 支付与积分相关接口
# ------------------------------------------

@app.post("/api/payment/checkout")
def api_checkout(req: CheckoutRequest):
    """
    前端点击“购买”或“订阅”时调用
    返回: Stripe 的支付页面 URL (checkout_url)
    """
    url = create_checkout_session(req.user_id, req.plan_type)
    if not url:
        raise HTTPException(status_code=400, detail="Failed to create checkout session")
    return {"url": url}

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    [系统回调] Stripe 支付成功后自动调用此接口
    注意: 
    1. 这是 Stripe 服务器调用的，不是前端调用的。
    2. 它会验证签名，确保安全。
    3. 支付成功后，它会自动给数据库加积分。
    """
    payload = await request.body()
    
    try:
        # 验证签名并构造事件
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        # 签名验证失败，直接返回 400，Stripe 会记录失败
        raise HTTPException(status_code=400, detail=str(e))

    # 处理 "支付成功" 事件
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # 从 metadata 中提取我们在创建订单时塞进去的 user_id 和 plan_type
        user_id = session.get("metadata", {}).get("user_id")
        plan_type = session.get("metadata", {}).get("plan_type")
        
        if user_id and plan_type:
            print(f"💰 Payment success for User: {user_id}, Plan: {plan_type}")
            
            # 情况 A: 购买积分 (一次性)
            if plan_type == "credits_100":
                # 假设这个包是 100 积分
                add_credits(user_id, 100, "Purchase 100 Credits")
            
            # 情况 B: 订阅 Starter
            elif plan_type == "starter":
                update_subscription_tier(user_id, "starter", session.get("customer"))
                add_credits(user_id, 500, "Starter Subscription (Month 1)")
                
            # 情况 C: 订阅 Pro
            elif plan_type == "pro":
                update_subscription_tier(user_id, "pro", session.get("customer"))
                add_credits(user_id, 1000, "Pro Subscription (Month 1)")
                
    return {"status": "success"}

# ------------------------------------------
# 原有 AI 生成接口
# ------------------------------------------

@app.post("/api/generate-story")
def api_generate_story(req: StoryRequest):
    """第一步: 生成故事脚本"""
    try:
        data = generate_story_json(req.topic, model="gpt-4o-mini")
        if not data:
            raise HTTPException(status_code=500, detail="Story generation returned empty result")
        return data
    except Exception as e:
        print(f"Error generating story: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-images")
async def api_generate_images(req: ImageRequest):
    """第二步: 生成图片"""
    try:
        if len(req.prompts) != 8:
             pass # 暂时忽略长度检查

        urls, task_id = await generate_8_images(req.prompts)
        
        if not urls:
            raise HTTPException(status_code=500, detail="Image generation failed")

        return {
            "status": "success",
            "task_id": task_id,
            "image_urls": urls
        }
    except Exception as e:
        print(f"Error generating images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-pdf")
def api_generate_pdf(req: PdfRequest):
    """第三步: 生成 PDF"""
    try:
        pdf_buffer = BytesIO()
        create_foldable_book(
            image_paths=req.image_urls,
            text_list=req.texts,
            output_buffer=pdf_buffer,
            draw_outer_border=True
        )
        pdf_buffer.seek(0)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=magic_zine.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)