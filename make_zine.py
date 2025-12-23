from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import os

# ==========================================
# 1. 全局配置 (Paper Registry)
# ==========================================
PAPER_CONFIG = {
    "US_LETTER": {
        "size": letter,        
        "name": "US Letter",
        "unit_display": "inch",
        "default_padding": 0.1 * inch
    },
    "A4": {
        "size": A4,            
        "name": "International A4",
        "unit_display": "mm",
        "default_padding": 6 * mm 
    }
}

# ==========================================
# 2. 核心工具：智能绘图函数 (Smart Image Drawer)
# ==========================================
def draw_smart_image(c, img_path, x, y, max_w, max_h, debug_border=False):
    """
    智能绘制图片：保持宽高比 (Aspect Fit)，自动居中。
    x, y: 目标格子的中心点坐标
    max_w, max_h: 安全区域的最大宽高
    """
    try:
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Path not found: {img_path}")

        # 1. 读取图片
        img = ImageReader(img_path)
        img_w, img_h = img.getSize()
        
        # 2. 计算缩放比例 (Min Scale 保证不溢出)
        scale = min(max_w / img_w, max_h / img_h)
        
        # 3. 计算实际显示尺寸
        new_w = img_w * scale
        new_h = img_h * scale
        
        # 4. 计算左下角绘制点 (ReportLab 以左下角为原点)
        # 因为我们传入的 x,y 是中心点，所以要减去一半的宽高
        draw_x = x - (new_w / 2)
        draw_y = y - (new_h / 2)
        
        # 5. 绘制图片
        c.drawImage(img, draw_x, draw_y, width=new_w, height=new_h)
        
        # (可选) 调试模式：画出图片实际边界
        if debug_border:
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.rect(draw_x, draw_y, new_w, new_h, fill=0)
            
    except Exception as e:
        # 容错处理：如果图片挂了，画红色文字代替，不中断程序
        print(f"⚠️ Image Error ({img_path}): {e}")
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x, y, "IMAGE MISSING")
        c.setFont("Helvetica", 8)
        c.drawCentredString(x, y - 12, os.path.basename(img_path))

# ==========================================
# 3. 主生成函数 (Main Generator)
# ==========================================
def create_foldable_book(
    image_paths,             # 接收 8 张图片路径的列表
    filename="final_book.pdf",
    paper_type="US_LETTER",  
    show_guides=True,
    custom_padding=None      
):
    """
    image_paths 顺序必须是: 
    [Page1, Page2, Page3, Page4, Page5, Page6, BackCover, FrontCover]
    """
    
    # --- 初始化配置 ---
    config = PAPER_CONFIG.get(paper_type.upper(), PAPER_CONFIG["US_LETTER"])
    raw_w, raw_h = config["size"]
    
    # 强制横向 (Landscape)
    if raw_h > raw_w:
        page_width, page_height = raw_h, raw_w
    else:
        page_width, page_height = raw_w, raw_h
        
    c = canvas.Canvas(filename, pagesize=(page_width, page_height))
    
    # 计算尺寸
    padding = custom_padding if custom_padding is not None else config["default_padding"]
    col_w = page_width / 4
    row_h = page_height / 2
    safe_w = col_w - (padding * 2)
    safe_h = row_h - (padding * 2)

    print(f"🚀 Generating PDF on {config['name']}...")

    # --- 绘制辅助线 (Guides) ---
    if show_guides:
        # 折叠线 (灰色虚线)
        c.setStrokeColor(colors.gray)
        c.setLineWidth(0.5)
        c.setDash(4, 4)
        for i in range(1, 4): c.line(col_w * i, 0, col_w * i, page_height)
        c.line(0, row_h, page_width, row_h)
        
        # 剪切线 (红色明显虚线)
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(3, 3) 
        c.line(col_w, row_h, col_w * 3, row_h)
        
        # 剪切标记
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.red)
        c.drawCentredString(page_width/2, row_h + 5, "")
    
    # --- 校验输入数据 ---
    if len(image_paths) < 8:
        print("⚠️ Warning: Not enough images provided. Filling with None.")
        image_paths += ["missing.jpg"] * (8 - len(image_paths))

    # ==========================================
    # 核心映射逻辑 (Topology Map)
    # ==========================================
    # 输入列表顺序: [P1, P2, P3, P4, P5, P6, Back, Front]
    # 索引对应:      0   1   2   3   4   5   6     7
    
    layout_map = [
        # Top Row (倒立): 格子从左到右对应 P4 -> P3 -> P2 -> P1
        (0, 1, image_paths[3], True),  # Top-Left  = Page 4
        (1, 1, image_paths[2], True),  # Top-Mid-L = Page 3
        (2, 1, image_paths[1], True),  # Top-Mid-R = Page 2
        (3, 1, image_paths[0], True),  # Top-Right = Page 1
        
        # Bottom Row (正立): 格子从左到右对应 P5 -> P6 -> Back -> Front
        (0, 0, image_paths[4], False), # Bot-Left  = Page 5
        (1, 0, image_paths[5], False), # Bot-Mid-L = Page 6
        (2, 0, image_paths[6], False), # Bot-Mid-R = Back Cover
        (3, 0, image_paths[7], False), # Bot-Right = Front Cover
    ]

    # --- 渲染循环 ---
    for col, row, img_path, upside_down in layout_map:
        # 1. 计算格子绝对中心
        center_x = (col * col_w) + (col_w / 2)
        center_y = (row * row_h) + (row_h / 2)
        
        c.saveState()
        
        # 2. 坐标变换 (处理倒立)
        if upside_down:
            c.translate(center_x, center_y)
            c.rotate(180)
            # 旋转后，(0,0) 就是格子中心
            draw_smart_image(c, img_path, 0, 0, safe_w, safe_h)
            
            # (可选) 打印页码标记方便调试
            # c.setFillColor(colors.lightgrey)
            # c.drawCentredString(0, -safe_h/2 - 5, "Top Row")
        else:
            c.translate(center_x, center_y)
            # 正立模式
            draw_smart_image(c, img_path, 0, 0, safe_w, safe_h)
            
        c.restoreState()

    c.showPage()
    c.save()
    print(f"✅ Success! PDF saved to: {filename}")

# ==========================================
# 测试入口
# ==========================================
if __name__ == "__main__":
    # 为了演示，我们需要伪造 8 张图片路径
    # 在真实项目中，这里是你从 Flux 下载下来的文件路径列表
    
    # 假设你当前文件夹下没有这些图，脚本会显示 "IMAGE MISSING" 红色占位符
    dummy_images = [
        "page2.png", "page3.png", "page4.png", "page5.png",
        "page6.png", "page7.png", "page8.png", "page1.png"
    ]
    
    # 1. 生成美国标准版
    create_foldable_book(
        dummy_images, 
        "result_US_Letter.pdf", 
        paper_type="US_LETTER"
    )
    
    # 2. 生成国际 A4 版 (无辅助线)
    create_foldable_book(
        dummy_images, 
        "result_A4_Clean.pdf", 
        paper_type="A4",
        show_guides=False
    )