import numpy as np
from PIL import Image
from typing import Dict

def preprocess_image(img, game_id):
    """
    根据游戏ID对图像进行预处理
    """
    if game_id == "ark" or "arknights" in game_id:  # 明日方舟相关游戏ID
        return preprocess_image_for_arknights(img)
    else:
        # 对于其他游戏，返回原图或应用其他预处理
        return img

def preprocess_image_for_arknights(img):
    """
    明日方舟图像预处理：将深灰色文字转换为黑色
    """
    img_array = np.array(img)
    
    # 目标颜色：RGB(31,31,31)
    target_color = np.array([31, 31, 31])
    tolerance = 15
    
    # 计算颜色差异
    color_diff = np.abs(img_array[:, :, :3] - target_color)
    mask = np.all(color_diff <= tolerance, axis=2)
    
    # 将匹配的像素设为黑色
    img_array[mask, :3] = [0, 0, 0]
    
    return Image.fromarray(img_array)

def crop_image_to_table(img: Image.Image, config: Dict) -> Image.Image:
    """
    裁剪图像到表格区域
    """
    bounds = config["table_area"]["bounds"]
    w, h = img.size
    left = int(w * bounds["left_ratio"])
    right = int(w * bounds["right_ratio"])
    top = int(h * bounds["top_ratio"])
    bottom = int(h * bounds["bottom_ratio"])
    return img.crop((left, top, right, bottom))