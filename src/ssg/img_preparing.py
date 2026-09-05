import logging
import os
import shutil
import traceback

from PIL import Image
from .schema import ImageProcResult

logging.getLogger("PIL").setLevel(logging.WARNING)


def process_image(img: str, target: str) -> ImageProcResult:
    """
    处理单张图片并落盘到 target（父目录会自动创建）。

    规则：
      - 原图 < 100KB 且 最长边 < 1300  → 原样搬运，不缩放、不生成 avif
      - 其余情况：
          最长边 > 1300 时等比缩放到长边 1300（不变形）
          再按落盘后的实际体积决定：<= 100KB 不生成 avif，否则在同目录生成同名 .avif

    注意：进入缩放/压缩流程的图片，落盘内容可能是重新编码的结果；
          尺寸合规但体积超标的图片仍然搬运原文件（保真），由 avif 兜底体积。
    """
    os.makedirs(os.path.dirname(target) or '.', exist_ok=True)

    try:
        im = Image.open(img)
        im.load()  # 真正的解码，避免懒加载把错误推迟到 save 阶段
    except Exception:
        # 解析失败：原样搬运，尺寸置 0 交由调用方决定如何处理
        shutil.copyfile(img, target)
        return ImageProcResult(width=0, height=0, avif=False)

    w, h = im.size

    # 小图且尺寸不大：直接搬运原文件，不做任何重新编码
    if os.path.getsize(img) < 100 * 1024 and max(w, h) < 1300:
        shutil.copyfile(img, target)
        return ImageProcResult(width=w, height=h, avif=False)

    if max(w, h) > 1300:
        # 等比缩放，int 截断保证缩放后长边不超过 1300
        scale = 1300 / max(w, h)
        w, h = max(1, int(w * scale)), max(1, int(h * scale))
        im = im.resize((w, h), Image.Resampling.LANCZOS)
        _write_image(im, target)
    else:
        # 尺寸合规但体积超标：保留原文件字节，交给 avif 兜底
        shutil.copyfile(img, target)

    # 以落盘后的实际体积作为是否生成 avif 的依据
    if os.path.getsize(target) <= 100 * 1024:
        return ImageProcResult(width=w, height=h, avif=False)

    avif_path = os.path.splitext(target)[0] + '.avif'
    if avif_path == target:
        # 原图扩展名本就是 .avif，主图即 avif，无需重复编码
        return ImageProcResult(width=w, height=h, avif=True)

    try:
        im.save(avif_path, format='AVIF', quality=60)
    except Exception as e:
        logging.warning(f"cannot generate avif, e: {e}\n{traceback.format_exc()}")
        # 环境不支持 avif 编码时降级：主图已就位，不阻断构建
        return ImageProcResult(width=w, height=h, avif=False)

    return ImageProcResult(width=w, height=h, avif=True)


def _write_image(im: Image.Image, path: str) -> None:
    """按扩展名落盘，处理有损格式不接受 alpha 通道的情况"""
    lower = path.lower()
    if lower.endswith(('.jpg', '.jpeg')):
        # JPEG 不支持 alpha，带透明通道的图必须先转 RGB
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGB')
        im.save(path, quality=85)
    else:
        im.save(path)
