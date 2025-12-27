from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.lib import colors
import os
from io import BytesIO
import zipfile
import requests
import base64
import re

# 纸张配置
PAPER_CONFIG = {
    "US_LETTER": {
        "size": letter, "name": "US Letter", "unit_display": "inch", "default_padding": 0.05 * inch 
    },
    "A4": {
        "size": A4, "name": "International A4", "unit_display": "mm", "default_padding": 2 * mm 
    }
}

def decode_base64_image(data_url):
    """
    解码 Base64 Data URL 为 BytesIO 对象
    支持格式: data:image/png;base64,xxxxx
    """
    if not data_url or not data_url.startswith('data:'):
        return None
    
    try:
        # 提取 base64 数据部分
        match = re.match(r'data:image/[^;]+;base64,(.+)', data_url)
        if match:
            base64_data = match.group(1)
            image_data = base64.b64decode(base64_data)
            return BytesIO(image_data)
    except Exception as e:
        print(f"Base64 decode error: {e}")
    return None

def draw_smart_image(c, img_source, x, y, max_w, max_h):
    """
    智能绘制图片：支持 URL、本地路径、Base64 Data URL，自动保持比例居中 (Contain 模式)
    x, y: 绘制区域的左下角坐标
    max_w, max_h: 绘制区域的最大宽高
    """
    if not img_source:
        return
        
    try:
        # 检查是否为 Base64 Data URL
        if isinstance(img_source, str) and img_source.startswith('data:'):
            img_buffer = decode_base64_image(img_source)
            if img_buffer:
                img = ImageReader(img_buffer)
            else:
                return
        else:
            # ImageReader 自动支持 URL 读取 (ReportLab内置功能)
            img = ImageReader(img_source) 
        
        img_w, img_h = img.getSize()
        
        # 计算缩放比例 (Contain 模式)
        scale = min(max_w / img_w, max_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        
        # 居中计算: 在给定的 bounding box (x, y, max_w, max_h) 内居中
        draw_x = x + (max_w - new_w) / 2
        draw_y = y + (max_h - new_h) / 2
        
        c.drawImage(img, draw_x, draw_y, width=new_w, height=new_h)
    except Exception as e:
        print(f"Image Draw Error ({img_source[:50] if img_source else 'None'}...): {e}")
        # 绘制红色占位框表示失败
        c.setStrokeColor(colors.red)
        c.rect(x, y, max_w, max_h)

def draw_wrapped_text(c, text, x, y, max_w, font_name="Helvetica", font_size=10):
    """
    绘制自动换行的文字
    """
    if not text: return
    lines = simpleSplit(text, font_name, font_size, max_w)
    line_height = font_size * 1.2 
    total_text_height = len(lines) * line_height
    
    # 垂直居中
    start_y = y + (total_text_height / 2) - font_size
    
    c.setFont(font_name, font_size)
    c.setFillColor(colors.black)
    for i, line in enumerate(lines):
        current_y = start_y - (i * line_height)
        c.drawCentredString(x, current_y, line)

def create_foldable_book(
    image_paths,             
    text_list=None,          
    output_buffer=None,
    paper_type="US_LETTER",  
    show_guides=True,
    draw_outer_border=False,
    padding=None      
):
    """
    生成 8 页折叠书 PDF (核心逻辑)
    """
    config = PAPER_CONFIG.get(paper_type.upper(), PAPER_CONFIG["US_LETTER"])
    raw_w, raw_h = config["size"]
    
    # 强制横向布局 (Landscape)
    if raw_h > raw_w: 
        page_width, page_height = raw_h, raw_w
    else: 
        page_width, page_height = raw_w, raw_h
        
    c = canvas.Canvas(output_buffer, pagesize=(page_width, page_height))
    
    final_padding = padding if padding is not None else config["default_padding"]
    col_w = page_width / 4
    row_h = page_height / 2
    
    # 1. 绘制折叠辅助线 (Guides)
    if show_guides:
        c.setStrokeColor(colors.gray)
        c.setLineWidth(0.5)
        c.setDash(4, 4)
        # 垂直折痕
        for i in range(1, 4): 
            c.line(col_w * i, 0, col_w * i, page_height)
        # 水平折痕
        c.line(0, row_h, page_width, row_h)
        # 剪切线 (中间部分)
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(3, 3) 
        c.line(col_w, row_h, col_w * 3, row_h)
        
        if draw_outer_border:
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.setDash(4, 4)
            c.rect(0, 0, page_width, page_height)

    # 2. 补齐数据
    if len(image_paths) < 8: 
        image_paths += [None] * (8 - len(image_paths))
    if text_list is None: 
        text_list = [""] * 8
    if len(text_list) < 8: 
        text_list += [""] * (8 - len(text_list))

    # ==========================================
    # 核心映射逻辑 (不要修改!)
    # (列号, 行号, 页面索引0-7, 是否倒置180度)
    # ==========================================
    grid_to_index = [
        (0, 1, 6, True),  # Page 7 (Back Cover)
        (1, 1, 5, True),  # Page 6
        (2, 1, 4, True),  # Page 5
        (3, 1, 3, True),  # Page 4
        (0, 0, 7, False), # Page 8 (Front Cover)
        (1, 0, 0, False), # Page 1 (Intro)
        (2, 0, 1, False), # Page 2
        (3, 0, 2, False)  # Page 3
    ]

    for col, row, idx, upside_down in grid_to_index:
        img_path = image_paths[idx]
        text_content = text_list[idx]
        
        # 计算当前格子的中心点
        center_x = (col * col_w) + (col_w / 2)
        center_y = (row * row_h) + (row_h / 2)
        
        c.saveState()
        
        # 坐标变换：移动原点到格子中心 -> 旋转 -> 移回 (逻辑上)
        if upside_down:
            c.translate(center_x, center_y)
            c.rotate(180)
            # 旋转后，坐标系倒置，后续绘制以 (0,0) 为中心
        else:
            c.translate(center_x, center_y)
        
        # 定义安全绘制区域 (相对于新的中心点 (0,0))
        # 此时左上角是 (-col_w/2, -row_h/2)
        # 我们需要在中心区域绘制，所以计算半宽半高
        safe_w = col_w - (final_padding * 2)
        safe_h = row_h - (final_padding * 2)
        
        # ==========================================
        # [修改] 动态布局逻辑：全图模式 vs 图文模式
        # ==========================================
        if text_content and text_content.strip():
            # [模式 A] 图文混排 (图片70%, 文字30%)
            img_ratio = 0.70
            txt_ratio = 0.30
            
            img_area_h = safe_h * img_ratio
            # 图片区域：在上方
            # 计算图片区域底部的Y坐标：从整体底部(-safe_h/2) 往上加文字区域高度
            img_y_bottom = -safe_h/2 + (safe_h * txt_ratio)
            
            txt_area_h = safe_h * txt_ratio
            txt_y_bottom = -safe_h/2
            txt_center_y = txt_y_bottom + (txt_area_h / 2)

            # 绘制图片
            if img_path:
                # draw_smart_image 需要的是绘制区域左下角坐标
                # X: -safe_w/2 (左边界)
                # Y: img_y_bottom
                draw_smart_image(c, img_path, -safe_w/2, img_y_bottom, safe_w, img_area_h)
            
            # 绘制文字
            draw_wrapped_text(c, text_content, 0, txt_center_y, safe_w)
            
        else:
            # [模式 B] 无文字模式 (所见即所得/全页铺满)
            # 此时前端已将Canvas合成一张图，我们让它尽可能大
            if img_path:
                # 绘制区域为整个 safe area
                # 左下角坐标为 (-safe_w/2, -safe_h/2)
                draw_smart_image(c, img_path, -safe_w/2, -safe_h/2, safe_w, safe_h)

        # 5. 绘制页码 (辅助)
        page_num_str = str(idx + 1)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        # 页码画在最底部边缘
        c.drawCentredString(0, -safe_h/2 + 2, page_num_str)
            
        c.restoreState()

    c.showPage()
    c.save()

def create_assets_zip(image_urls, output_buffer):
    """
    [新增] 打包所有素材为 ZIP
    """
    with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, url in enumerate(image_urls):
            if not url: continue
            try:
                # 下载图片
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    # 写入 ZIP，文件名为 Page_1.png 等
                    zip_file.writestr(f"Page_{i+1}.png", resp.content)
            except Exception as e:
                print(f"Zip Error {url}: {e}")