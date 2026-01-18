from PIL import Image
from typing import Optional
import pytesseract
from .logger_manager import get_logger

# 设置 Tesseract 路径（Windows 用户）
pytesseract.pytesseract.tesseract_cmd = r'tools\Tesseract-OCR\tesseract.exe'
# ===========================================================
# OCR识别函数
# ===========================================================
def perform_ocr(img: Image.Image, lang: str = "chi_sim", logger=None) -> Optional[str]:
    """执行OCR识别"""
    if logger is None:
        logger = get_logger()
    try:
        text = pytesseract.image_to_string(img, lang=lang)
        logger.info(f"OCR识别结果:\n{text}")
        return text.strip() if text else None
    except Exception as e:
        logger.error(f"[OCR] 识别失败: {e}")
        return None