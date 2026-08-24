import os
import logging
from PIL import Image, ImageOps, UnidentifiedImageError
from pathlib import Path
from typing import Tuple

from PIL import Image, UnidentifiedImageError
from PIL.features import check_codec

from src.config import IS_PROD

logging.getLogger("PIL").setLevel(logging.WARNING)

# 模块加载时即检测 AVIF 编码器是否可用，避免每次调用都重复检查。
# 旧版 Pillow（<11.3 或未编译 AVIF 支持）会把 "avif" 视为未知 codec 并抛 ValueError，
# 此时视为不可用，函数将返回明确的错误提示。
try:
    _AVIF_ENCODER_OK = check_codec("avif")
except ValueError:
    _AVIF_ENCODER_OK = False


def _convert_to_avif(
        src: str,
        dst: str,
        max_size: int = 1300,
        quality: int = 80,
        speed: int = 6,
) -> Tuple[bool, str]:
    """
    将图片转换为 AVIF，确保输出长边不超过 max_size，等比缩放不变形。

    Args:
        src:      源图片绝对路径（调用方保证存在且为文件）
        dst:      目标 AVIF 绝对路径（父目录已存在）
        max_size: 输出长边上限，默认 1300
        quality:  AVIF 质量 0-100，默认 80
        speed:    AVIF 编码速度 0-10，默认 6

    Returns:
        (True, "") 成功
        (False, "<error message>") 失败，不抛异常
    """
    # ---- 后缀修正：dst 统一以 .avif 结尾 ----
    dst_path = Path(dst)
    if dst_path.suffix.lower() != ".avif":
        dst_path = dst_path.with_suffix(".avif")

    try:
        # ---- 打开并校验 ----
        with Image.open(src) as img:
            # 先检查真实编码格式
            if img.format and img.format.upper() == "AVIF":
                return False, "source image is already AVIF, skip re-encoding"

            # ---- 等比缩放：长边不超过 max_size ----
            w, h = img.size
            long_side = max(w, h)
            if long_side > max_size:
                scale = max_size / long_side
                new_w = int(round(w * scale))
                new_h = int(round(h * scale))
                # LANCZOS 是高质量下采样滤镜
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # ---- 色彩处理：保留透明 ----
            if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
            ):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            # ---- 编码保存 ----
            img.save(
                str(dst_path),
                "AVIF",
                quality=quality,
                speed=speed,
            )

        return True, ""

    except UnidentifiedImageError:
        return False, f"cannot identify image file: {src}"
    except OSError as e:
        # Pillow 编码失败（编码器不可用、磁盘满等）
        return False, f"OS error during save: {e}"
    except Exception as e:
        # 兜底，绝不抛出
        return False, f"unexpected error: {e}"


def get_image_size(
        image_path: str | Path,
        respect_orientation: bool = False
) -> Tuple[int, int]:
    """
    获取图像尺寸。

    Args:
        image_path: 图像路径。
        respect_orientation: 是否根据 EXIF Orientation 标签调整尺寸。
                             手机竖拍照通常存为横图+旋转标记，设为 True
                             会返回旋转后的实际显示尺寸。

    Returns:
        (width, height)
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")

    try:
        with Image.open(path) as img:
            if respect_orientation:
                # exif_transpose 会根据 Orientation 标签自动旋转/翻转
                img = ImageOps.exif_transpose(img)
            w, h = img.size
            if max(w, h) > 1300:
                scale = 1300 / max(w, h)
                w, h = int(w * scale), int(h * scale)
            return w, h

    except UnidentifiedImageError:
        raise ValueError(f"无法识别图像格式: {path}")


def covert_to_avif(src: str, dst: str) -> tuple[bool, str]:
    parent, _ = os.path.split(dst)
    os.makedirs(parent, exist_ok=True)

    if IS_PROD:
        return _convert_to_avif(src, dst)

    # if DEBUG:
    with open(src, "rb") as r:
        with open(dst, "wb") as w:
            w.write(r.read())
    return True, ""
