"""
阿里云 DashScope 配置

包含 Qwen (通义千问) 和 Wanx (通义万相) 的配置常量。
"""

import os

# ==========================================
# Configuration
# ==========================================

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")

# API Endpoints (International)
# 新加坡: dashscope-intl.aliyuncs.com
# 北京: dashscope.aliyuncs.com
DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL", 
    "https://dashscope-intl.aliyuncs.com"
)

# Text API endpoint
TEXT_API_URL = f"{DASHSCOPE_BASE_URL}/api/v1/services/aigc/text-generation/generation"

# Image API endpoint (万相)
IMAGE_API_URL = f"{DASHSCOPE_BASE_URL}/api/v1/services/aigc/multimodal-generation/generation"

# Available models
QWEN_TEXT_MODELS = [
    "qwen-turbo",      # 快速，低成本
    "qwen-plus",       # 平衡
    "qwen-max",        # 最高质量
    "qwen-max-longcontext",  # 长上下文
]

WANX_IMAGE_MODELS = [
    "wanx-v1",         # 万相 v1
    "wan2.6-t2i",      # 万相 2.6 文生图
    "wan2.6-image",    # 万相 2.6 图像编辑
]

# Size mapping: our format -> Wanx format
# 万相使用 "宽*高" 格式
SIZE_MAPPING = {
    "square": "1024*1024",
    "1:1": "1024*1024",
    "landscape_4_3": "1280*960",
    "4:3": "1280*960",
    "portrait_4_3": "960*1280",
    "3:4": "960*1280",
    "landscape_16_9": "1280*720",
    "16:9": "1280*720",
    "portrait_9_16": "720*1280",
    "9:16": "720*1280",
    # 默认
    "1024x1024": "1024*1024",
    "1280x1280": "1280*1280",
}
