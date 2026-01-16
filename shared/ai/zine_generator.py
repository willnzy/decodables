import logging
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

logger = logging.getLogger(__name__)

# 
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
     Base64 Data URL  BytesIO 
    : data:image/png;base64,xxxxx
    """
    if not data_url or not data_url.startswith('data:'):
        return None
    
    try:
        #  base64 
        match = re.match(r'data:image/[^;]+;base64,(.+)', data_url)
        if match:
            base64_data = match.group(1)
            image_data = base64.b64decode(base64_data)
            return BytesIO(image_data)
    except Exception as e:
        logger.warning(f"Base64 decode error: {e}")
    return None

def draw_smart_image(c, img_source, x, y, max_w, max_h):
    """
    ： URL、、Base64 Data URL， (Contain )
    x, y: 
    max_w, max_h: 
    """
    if not img_source:
        return
        
    try:
        #  Base64 Data URL
        if isinstance(img_source, str) and img_source.startswith('data:'):
            img_buffer = decode_base64_image(img_source)
            if img_buffer:
                img = ImageReader(img_buffer)
            else:
                return
        else:
            # ImageReader  URL  (ReportLab)
            img = ImageReader(img_source) 
        
        img_w, img_h = img.getSize()
        
        #  (Contain )
        scale = min(max_w / img_w, max_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        
        # :  bounding box (x, y, max_w, max_h) 
        draw_x = x + (max_w - new_w) / 2
        draw_y = y + (max_h - new_h) / 2
        
        c.drawImage(img, draw_x, draw_y, width=new_w, height=new_h)
    except Exception as e:
        logger.warning(f"Image draw error ({img_source[:50] if img_source else 'None'}...): {e}")
        # 
        c.setStrokeColor(colors.red)
        c.rect(x, y, max_w, max_h)

def draw_wrapped_text(c, text, x, y, max_w, font_name="Helvetica", font_size=10):
    """
    
    """
    if not text: return
    lines = simpleSplit(text, font_name, font_size, max_w)
    line_height = font_size * 1.2 
    total_text_height = len(lines) * line_height
    
    # 
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
     8  PDF ()
    """
    config = PAPER_CONFIG.get(paper_type.upper(), PAPER_CONFIG["US_LETTER"])
    raw_w, raw_h = config["size"]
    
    #  (Landscape)
    if raw_h > raw_w: 
        page_width, page_height = raw_h, raw_w
    else: 
        page_width, page_height = raw_w, raw_h
        
    c = canvas.Canvas(output_buffer, pagesize=(page_width, page_height))
    
    final_padding = padding if padding is not None else config["default_padding"]
    col_w = page_width / 4
    row_h = page_height / 2
    
    # 1.  (Guides)
    if show_guides:
        c.setStrokeColor(colors.gray)
        c.setLineWidth(0.5)
        c.setDash(4, 4)
        # 
        for i in range(1, 4): 
            c.line(col_w * i, 0, col_w * i, page_height)
        # 
        c.line(0, row_h, page_width, row_h)
        #  ()
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(3, 3) 
        c.line(col_w, row_h, col_w * 3, row_h)
        
        if draw_outer_border:
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.setDash(4, 4)
            c.rect(0, 0, page_width, page_height)

    # 2. 
    if len(image_paths) < 8: 
        image_paths += [None] * (8 - len(image_paths))
    if text_list is None: 
        text_list = [""] * 8
    if len(text_list) < 8: 
        text_list += [""] * (8 - len(text_list))

    # ==========================================
    #  (!)
    # (, , 0-7, 180)
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
        
        # 
        center_x = (col * col_w) + (col_w / 2)
        center_y = (row * row_h) + (row_h / 2)
        
        c.saveState()
        
        # ： ->  ->  ()
        if upside_down:
            c.translate(center_x, center_y)
            c.rotate(180)
            # ，， (0,0) 
        else:
            c.translate(center_x, center_y)
        
        #  ( (0,0))
        #  (-col_w/2, -row_h/2)
        # ，
        safe_w = col_w - (final_padding * 2)
        safe_h = row_h - (final_padding * 2)
        
        # ==========================================
        # [] ： vs 
        # ==========================================
        if text_content and text_content.strip():
            # [ A]  (70%, 30%)
            img_ratio = 0.70
            txt_ratio = 0.30
            
            img_area_h = safe_h * img_ratio
            # ：
            # Y：(-safe_h/2) 
            img_y_bottom = -safe_h/2 + (safe_h * txt_ratio)
            
            txt_area_h = safe_h * txt_ratio
            txt_y_bottom = -safe_h/2
            txt_center_y = txt_y_bottom + (txt_area_h / 2)

            # 
            if img_path:
                # draw_smart_image 
                # X: -safe_w/2 ()
                # Y: img_y_bottom
                draw_smart_image(c, img_path, -safe_w/2, img_y_bottom, safe_w, img_area_h)
            
            # 
            draw_wrapped_text(c, text_content, 0, txt_center_y, safe_w)
            
        else:
            # [ B]  (/)
            # Canvas，
            if img_path:
                #  safe area
                #  (-safe_w/2, -safe_h/2)
                draw_smart_image(c, img_path, -safe_w/2, -safe_h/2, safe_w, safe_h)

        # 5.  ()
        page_num_str = str(idx + 1)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        # 
        c.drawCentredString(0, -safe_h/2 + 2, page_num_str)
            
        c.restoreState()

    c.showPage()
    c.save()

def create_assets_zip(image_urls, output_buffer):
    """
    []  ZIP
    """
    with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, url in enumerate(image_urls):
            if not url: continue
            try:
                # 
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    #  ZIP， Page_1.png 
                    zip_file.writestr(f"Page_{i+1}.png", resp.content)
            except Exception as e:
                logger.warning(f"Zip error for {url}: {e}")