import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from io import BytesIO

# 导入模块
from story_generator import generate_story_json
from image_generator import generate_8_images
from zine_generator import create_foldable_book

app = FastAPI()

class StoryRequest(BaseModel):
    topic: str

class ImageRequest(BaseModel):
    prompts: List[str]

class PdfRequest(BaseModel):
    image_urls: List[str]
    texts: List[str]

@app.get("/")
def home():
    return {"message": "MagicZine API is running!"}

@app.post("/api/generate-story")
def api_generate_story(req: StoryRequest):
    data = generate_story_json(req.topic, model="gpt-4o-mini")
    if not data:
        raise HTTPException(500, "Story generation failed")
    return data

@app.post("/api/generate-images")
async def api_generate_images(req: ImageRequest):
    # 生成并上传到 Supabase，返回 URLs
    urls, task_id = await generate_8_images(req.prompts)
    return {"task_id": task_id, "image_urls": urls}

@app.post("/api/generate-pdf")
def api_generate_pdf(req: PdfRequest):
    # 创建内存 Buffer
    pdf_buffer = BytesIO()
    
    try:
        create_foldable_book(
            image_paths=req.image_urls, # 传入 URL 列表
            text_list=req.texts,
            output_buffer=pdf_buffer,   # 传入 Buffer
            draw_outer_border=True
        )
        pdf_buffer.seek(0) # 指针回退到开头
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=magic_zine.pdf"}
        )
    except Exception as e:
        raise HTTPException(500, str(e))