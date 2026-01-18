from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from .logger_manager import get_logger
from .perform_ocr import perform_ocr

# Crop the table area from the image (assumes right part of the image contains the table)
def crop_table_area(img, config=None):
    if config:
        # 使用配置文件中的参数
        bounds = config["table_area"]["bounds"]
        w, h = img.size
        left = int(w * bounds["left_ratio"])
        right = int(w * bounds["right_ratio"])
        top = int(h * bounds["top_ratio"])
        bottom = int(h * bounds["bottom_ratio"])
        return img.crop((left, top, right, bottom))
    else:
        # 使用默认参数
        w, h = img.size
        left = int(w * 0.24)
        right = int(w * 0.92)
        top = int(h * 0.27)
        bottom = int(h * 0.854)
        return img.crop((left, top, right, bottom))

# Function to process images
def process_image(image_path, config=None, logger=None):
    if logger is None:
        logger = get_logger()
    img = Image.open(image_path)
    table = crop_table_area(img, config)  # Crop table area
    ocr_text = perform_ocr(table, logger=logger)  # Run OCR

    # Show both original and processed images for visual comparison
    plt.figure(figsize=(12, 6))

    # Original image
    plt.subplot(1, 2, 1)
    plt.imshow(img)
    plt.title("Original Image")
    plt.axis('off')

    # Processed image (cropped and enhanced)
    plt.subplot(1, 2, 2)
    plt.imshow(table, cmap="gray")
    plt.title("Processed Image (Cropped & Enhanced)")
    plt.axis('off')

    plt.show()

    if ocr_text is None:
        logger.error(f"OCR failed for image: {image_path}")
        return None
    else:
        logger.info(f"OCR result for {image_path}:\n{ocr_text}")
    return ocr_text

# 自动读取指定路径下的所有图片文件
def get_image_paths(directory):
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')  # 支持的图片格式
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(supported_extensions)]

def test_ocr_with_config(image_path, config, lang='chi_sim', custom_bounds=None, logger=None):
    """
    使用配置文件对图像进行OCR测试
    """
    if logger is None:
        logger = get_logger()
    img = Image.open(image_path)
    
    # 如果提供了自定义边界，则使用它覆盖配置中的边界
    if custom_bounds:
        # 创建临时配置副本
        temp_config = config.copy()
        if "table_area" not in temp_config:
            temp_config["table_area"] = {}
        if "bounds" not in temp_config["table_area"]:
            temp_config["table_area"]["bounds"] = {}
        temp_config["table_area"]["bounds"] = custom_bounds
        table = crop_table_area(img, temp_config)
    else:
        table = crop_table_area(img, config)
        
    ocr_text = perform_ocr(table, lang=lang, logger=logger)  # Run OCR with specified language

    # Show both original and processed images for visual comparison
    plt.figure(figsize=(12, 6))

    # Original image
    plt.subplot(1, 2, 1)
    plt.imshow(img)
    plt.title("Original Image")
    plt.axis('off')

    # Processed image (cropped and enhanced)
    plt.subplot(1, 2, 2)
    plt.imshow(table, cmap="gray")
    plt.title("Processed Image (Cropped & Enhanced)")
    plt.axis('off')

    plt.show()

    if ocr_text is None:
        logger.error(f"OCR failed for image: {image_path}")
        return None
    else:
        logger.info(f"OCR result for {image_path}:\n{ocr_text}")
    return ocr_text
