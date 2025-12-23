from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
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
# 2. 智能绘图函数 (保持不变)
# ==========================================
def draw_smart_image(c, img_path, x, y, max_w, max_h, debug_border=False):
    """ 智能绘制图片：保持宽高比 (Aspect Fit)，自动居中。 """
    try:
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Path not found: {img_path}")

        img = ImageReader(img_path)
        img_w, img_h = img.getSize()
        
        # 计算缩放
        scale = min(max_w / img_w, max_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        
        # 居中坐标
        draw_x = x - (new_w / 2)
        draw_y = y - (new_h / 2)
        
        c.drawImage(img, draw_x, draw_y, width=new_w, height=new_h)
        
        if debug_border:
            c.setStrokeColor(colors.blue)
            c.setLineWidth(0.5)
            c.rect(draw_x, draw_y, new_w, new_h, fill=0)
            
    except Exception as e:
        print(f"⚠️ Image Error ({img_path}): {e}")
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x, y, "IMG ERR")

# ==========================================
# 3. 主生成函数 (已修改 padding 逻辑)
# ==========================================
def create_foldable_book(
    image_paths,             
    filename="final_book.pdf",
    paper_type="US_LETTER",  
    show_guides=True,
    draw_outer_border=False,
    padding=None  # <--- 修改点：参数名简化为 padding，默认为 None
):
    """
    padding: 传入具体的数值 (如 0.2*inch)。如果不传(None)，则使用纸张的默认推荐值。
    """
    
    # --- 初始化配置 ---
    config = PAPER_CONFIG.get(paper_type.upper(), PAPER_CONFIG["US_LETTER"])
    raw_w, raw_h = config["size"]
    
    # 强制横向
    if raw_h > raw_w: page_width, page_height = raw_h, raw_w
    else: page_width, page_height = raw_w, raw_h
        
    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    
    # --- 核心修改：决定最终使用的 Padding ---
    # 如果用户传了值，就用用户的；否则用配置里的默认值
    final_padding = padding if padding is not None else config["default_padding"]
    
    col_w = page_width / 4
    row_h = page_height / 2
    
    # 计算安全区域 (Safe Area)
    safe_w = col_w - (final_padding * 2)
    safe_h = row_h - (final_padding * 2)

    # 打印日志确认 Padding 生效
    unit = "inch" if config["unit_display"] == "inch" else "mm"
    display_val = final_padding/inch if unit == "inch" else final_padding/mm
    print(f"🚀 Generating PDF ({config['name']}). Padding: {display_val:.2f} {unit}")

    # --- 绘制辅助线 (Guides) ---
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
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.black)
            c.drawString(5, 5, "Trim Line")

    # --- 数据填充 ---
    if len(image_paths) < 8:
        image_paths += ["missing.jpg"] * (8 - len(image_paths))

    layout_map = [
        # Top Row (倒立)
        (0, 1, image_paths[6], True),  # P7
        (1, 1, image_paths[5], True),  # P6
        (2, 1, image_paths[4], True),  # P5
        (3, 1, image_paths[3], True),  # P4
        # Bottom Row (正立)
        (0, 0, image_paths[7], False), # P8
        (1, 0, image_paths[0], False), # P1
        (2, 0, image_paths[1], False), # P2
        (3, 0, image_paths[2], False), # P3
    ]

    for col, row, img_path, upside_down in layout_map:
        center_x = (col * col_w) + (col_w / 2)
        center_y = (row * row_h) + (row_h / 2)
        
        c.saveState()
        if upside_down:
            c.translate(center_x, center_y)
            c.rotate(180)
            draw_smart_image(c, img_path, 0, 0, safe_w, safe_h)
        else:
            c.translate(center_x, center_y)
            draw_smart_image(c, img_path, 0, 0, safe_w, safe_h)
        c.restoreState()

    c.showPage()
    c.save()
    print(f"✅ Success! Saved to: {filename}")

# ==========================================
# 4. 测试用例：如何传入 Padding
# ==========================================
if __name__ == "__main__":
    dummy_images = [
        "P1.png", "P2.png", "P3.png", "P4.png", 
        "P5.png", "P6.png", "P7.png", "P8.png"
    ]
    
    # 场景 1: 使用默认 Padding (不做任何操作)
    create_foldable_book(
        dummy_images, 
        "result_default.pdf",
        paper_type="A4",
        show_guides=True,
        draw_outer_border=True
    )
    
 