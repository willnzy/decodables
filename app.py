import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from io import BytesIO

# 导入我们写好的三个核心模块
from story_generator import generate_story_json
from image_generator import generate_8_images
from zine_generator import create_foldable_book

# 初始化 FastAPI 应用
app = FastAPI(title="MagicZine AI API")

# ==========================================
# 1. 配置 CORS (跨域资源共享) - 必做！
# ==========================================
# 如果不配置这个，你的前端网页(localhost 或 Vercel)无法调用这个后端的接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源 (生产环境建议改为你的前端域名)
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (POST, GET, OPTIONS 等)
    allow_headers=["*"],  # 允许所有请求头
)

# ==========================================
# 2. 定义数据模型 (Request Models)
# ==========================================
class StoryRequest(BaseModel):
    topic: str
    # 可选参数，未来可以扩展风格选择
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

@app.post("/api/generate-story")
def api_generate_story(req: StoryRequest):
    """
    第一步:生成故事脚本
    输入:主题 (Topic)
    输出:JSON 格式的故事大纲 (包含 8 页文字和 Prompt)
    """
    try:
        # 调用 story_generator.py
        data = generate_story_json(req.topic, model="gpt-4o-mini")
        
        if not data:
            raise HTTPException(status_code=500, detail="Story generation returned empty result")
        
        return data
        
    except Exception as e:
        print(f"Error generating story: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-images")
async def api_generate_images(req: ImageRequest):
    """
    第二步:生成图片并上传到 Supabase
    输入:8 个 Prompts
    输出:8 个云端图片 URL 和 Task ID
    """
    try:
        if len(req.prompts) != 8:
             # 为了容错，如果不足8个，后端可以自动补全，或者报错。这里选择报错提示前端。
             # 实际业务中也可以选择只是 warning
             pass 

        # 调用 image_generator.py (异步并发)
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
    """
    第三步:生成 PDF (内存流处理)
    输入:图片 URL 列表 + 文字列表
    输出:PDF 文件流 (直接触发浏览器下载)
    """
    try:
        # 创建一个内存缓冲区，代替本地文件
        pdf_buffer = BytesIO()
        
        # 调用 zine_generator.py
        create_foldable_book(
            image_paths=req.image_urls,  # 这里传入的是 URL 列表
            text_list=req.texts,
            output_buffer=pdf_buffer,    # 传入内存 buffer
            draw_outer_border=True       # 画出裁剪边框方便用户制作
        )
        
        # 将指针重置到文件开头，准备读取
        pdf_buffer.seek(0)
        
        # 返回流媒体响应，告诉浏览器这是一个 PDF 文件
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=magic_zine.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition" # 允许前端读取文件名
            }
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 本地调试用 (Railway 部署时不会执行这里，而是通过 Procfile 启动)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)