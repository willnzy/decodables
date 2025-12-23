from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.lib import colors
import os

# ==========================================
# 1. 全局配置
# ==========================================
PAPER_CONFIG = {
    "US_LETTER": {
        "size": letter,        
        "name": "US Letter",
        "unit_display": "inch",
        "default_padding": 0.05 * inch 
    },
    "A4": {
        "size": A4,            
        "name": "International A4",
        "unit_display": "mm",
        "default_padding": 2 * mm 
    }
}

# ==========================================
# 2. 智能绘图函数
# ==========================================
def draw_smart_image(c, img_path, x, y, max_w, max_h, debug_border=False):
    try:
        if not img_path or not os.path.exists(img_path):
            raise FileNotFoundError(f"Missing: {img_path}")

        img = ImageReader(img_path)
        img_w, img_h = img.getSize()
        
        # Aspect Fit
        scale = min(max_w / img_w, max_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        
        draw_x = x - (new_w / 2)
        draw_y = y - (new_h / 2)
        
        c.drawImage(img, draw_x, draw_y, width=new_w, height=new_h)
        
        if debug_border:
            c.setStrokeColor(colors.blue)
            c.setLineWidth(0.5)
            c.rect(draw_x, draw_y, new_w, new_h, fill=0)
            
    except Exception as e:
        pass

# ==========================================
# 3. 智能文字函数
# ==========================================
def draw_wrapped_text(c, text, x, y, max_w, font_name="Helvetica", font_size=10):
    if not text:
        return

    lines = simpleSplit(text, font_name, font_size, max_w)
    line_height = font_size * 1.2 
    total_text_height = len(lines) * line_height
    start_y = y + (total_text_height / 2) - font_size
    
    c.setFont(font_name, font_size)
    c.setFillColor(colors.black)
    
    for i, line in enumerate(lines):
        current_y = start_y - (i * line_height)
        c.drawCentredString(x, current_y, line)

# ==========================================
# 4. 主生成函数
# ==========================================
def create_foldable_book(
    image_paths,             
    text_list=None,          
    filename="final_book.pdf",
    paper_type="US_LETTER",  
    show_guides=True,
    draw_outer_border=False,
    padding=None      
):
    config = PAPER_CONFIG.get(paper_type.upper(), PAPER_CONFIG["US_LETTER"])
    raw_w, raw_h = config["size"]
    if raw_h > raw_w: page_width, page_height = raw_h, raw_w
    else: page_width, page_height = raw_w, raw_h
        
    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    
    final_padding = padding if padding is not None else config["default_padding"]
    col_w = page_width / 4
    row_h = page_height / 2
    
    if show_guides:
        c.setStrokeColor(colors.gray)
        c.setLineWidth(0.5)
        c.setDash(4, 4)
        for i in range(1, 4): c.line(col_w * i, 0, col_w * i, page_height)
        c.line(0, row_h, page_width, row_h)
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(3, 3) 
        c.line(col_w, row_h, col_w * 3, row_h)
        if draw_outer_border:
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.setDash(4, 4)
            c.rect(0, 0, page_width, page_height)

    # 补齐数据
    if len(image_paths) < 8: image_paths += [None] * (8 - len(image_paths))
    if text_list is None: text_list = [""] * 8
    if len(text_list) < 8: text_list += [""] * (8 - len(text_list))

    # 映射表
    grid_to_index = [
        (0, 1, 6, True), (1, 1, 5, True), (2, 1, 4, True), (3, 1, 3, True),
        (0, 0, 7, False), (1, 0, 0, False), (2, 0, 1, False), (3, 0, 2, False)
    ]

    for col, row, idx, upside_down in grid_to_index:
        img_path = image_paths[idx]
        text_content = text_list[idx]
        
        center_x = (col * col_w) + (col_w / 2)
        center_y = (row * row_h) + (row_h / 2)
        
        c.saveState()
        
        if upside_down:
            c.translate(center_x, center_y)
            c.rotate(180)
        else:
            c.translate(center_x, center_y)
        
        # 布局计算
        safe_w = col_w - (final_padding * 2)
        safe_h = row_h - (final_padding * 2)
        
        img_ratio = 0.70
        txt_ratio = 0.30
        
        img_area_h = safe_h * img_ratio
        img_center_y = (safe_h / 2) - (img_area_h / 2)
        
        txt_area_h = safe_h * txt_ratio
        txt_center_y = (-safe_h / 2) + (txt_area_h / 2)

        # 绘制图片
        if img_path:
            draw_smart_image(c, img_path, 0, img_center_y, safe_w, img_area_h)
            
        # 绘制文字
        if text_content:
            draw_wrapped_text(c, text_content, 0, txt_center_y, safe_w)

        # 绘制页码 (这里就是你缺失的部分)
        page_num_str = str(idx + 1)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        c.drawCentredString(0, -safe_h/2 + 5, page_num_str)
            
        c.restoreState()

    c.showPage()
    c.save()
    print(f"✅ PDF Generated: {filename}")

if __name__ == "__main__":
    dummy_images = ["P1.png"] * 8 
    dummy_texts = [f"This is page {i+1}" for i in range(8)]
    create_foldable_book(dummy_images, text_list=dummy_texts, filename="test_full.pdf", draw_outer_border=True)