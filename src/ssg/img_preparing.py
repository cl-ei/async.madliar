import os
import logging
from PIL import Image, ImageOps, UnidentifiedImageError, ImageFilter
from PIL.features import check_codec

from pathlib import Path
from typing import Tuple


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
        quality: int = 85,
        speed: int = 5,
        sharpen: bool = True,
) -> Tuple[bool, str]:
    """
    将图片转换为 AVIF，长边不超过 max_size，等比缩放，针对清晰度优化。

    Returns:
        (True, "") 成功
        (False, "<error message>") 失败，不抛异常
    """
    dst_path = Path(dst)
    if dst_path.suffix.lower() != ".avif":
        dst_path = dst_path.with_suffix(".avif")

    try:
        with Image.open(src) as img:
            # 已经是 AVIF → 跳过
            if img.format and img.format.upper() == "AVIF":
                return False, "source image is already AVIF, skip re-encoding"

            # ---- 等比缩放 ----
            w, h = img.size
            long_side = max(w, h)

            if long_side > max_size:
                scale = max_size / long_side
                new_w = int(round(w * scale))
                new_h = int(round(h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # ---- 缩小后轻微锐化，补偿插值带来的软 ----
                if sharpen:
                    img = img.filter(
                        ImageFilter.UnsharpMask(
                            radius=0.8,    # 锐化半径，小一点避免噪点
                            percent=50,    # 锐化强度
                            threshold=3,   # 只锐化差异明显的边缘
                        )
                    )

            # ---- 色彩：保留透明 ----
            if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
            ):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            # ---- 保存：关键改动在这里 ----
            img.save(
                str(dst_path),
                "AVIF",
                quality=80,
                speed=6,
                subsampling="4:2:2",
            )

        return True, ""

    except UnidentifiedImageError:
        return False, f"cannot identify image file: {src}"
    except OSError as e:
        return False, f"OS error during save: {e}"
    except Exception as e:
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
        if os.stat(src).st_size < 100*1024:
            return False, "image file too small, skip"
        return _convert_to_avif(src, dst)

    # if DEBUG:
    with open(src, "rb") as r:
        with open(dst, "wb") as w:
            w.write(r.read())
    return True, ""
