import logging
import os.path
import re
import yaml
import datetime
from xpinyin import Pinyin
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
from src.error import ErrorWithPrompt
from .schema import SiteConfig, Article, SITE_CONFIG_FILE, ImageProperty
from src.ssg.marked.bridge import covert_to_html


DATE_FORMAT = "%Y-%m-%d"

# 针对 slug 提取的规则
MULTI_DASH_RE = re.compile(r'-+')                                    # 匹配连续中划线
ALLOWED_CHARS = set(
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "/_.-"
)

def normalize_identifier(content: str) -> str:
    """
    规范化字符串，专为SSG的slug、文件名、URL路径生成设计：
    1. 将所有不可见字符（含空格、换行、零宽字符等）替换为中划线`-`
    2. 仅保留数字、大小写字母，以及 `-` `/` `_` `.` 四类符号
    3. 合并连续的中划线为单个
    4. 去除首尾的中划线
    5. 去除/前后的-

    参数:
        s: 原始输入字符串（如文章标题、分类名等）
    返回:
        规范化后的字符串，全为非法字符时返回空串

        "/t//Cortex-M33-zhong-duan-（-yi-）/-1--/" =>
        '/t//Cortex-M33-zhong-duan-yi/1/'
    """
    def proc_one_seg(s: str):
        s = "".join(c if c in ALLOWED_CHARS else '-' for c in s)
        s = MULTI_DASH_RE.sub('-', s).strip('-').lower()
        return s

    return "/".join([proc_one_seg(x) for x in content.split("/")])


class ArticleBuilder:
    """构建Article对象"""

    def __init__(self, config: SiteConfig, storage_root: str):
        self.config = config
        self.storage_root = storage_root

    @staticmethod
    def parse_front_matter(content: str, fm_delimiter: str = "---") -> tuple[dict, str]:
        """解析文件头和正文"""
        if not content.startswith(fm_delimiter):
            # 没有FM，视为普通页面
            return {}, content

        try:
            _, fm_raw, body = content.split(fm_delimiter, 2)
        except ValueError:
            # 格式错误，兜底处理
            return {}, content

        try:
            fm = yaml.safe_load(fm_raw) or {}
        except yaml.YAMLError as e:
            raise ErrorWithPrompt(f"Front Matter解析失败: {e}")

        return fm, body.strip()

    @staticmethod
    def _extract_slug(fm: dict, file_path: str) -> str:
        """提取 Slug：优先取 FM 的 slug 字段，无则取文件名转拼音后的字符串"""
        slug = None
        for key in ("slug", "title", "subtitle"):
            if key in fm:
                slug = fm[key]
                break
        if slug is None:
            filename = file_path.split("/")[-1]
            slug, _ = os.path.splitext(filename)
        fallback_slug = Pinyin().get_pinyin(slug)
        return normalize_identifier(fallback_slug)

    def _generate_permalink(self, fm: dict, slug: str, file_path: str, file_mtime: float) -> str:
        """
        生成 Permalink

        Args:
            slug: 文章唯一标识
            fm: Front Matter 字典，必须包含 date 字段
            file_path: 文件相对路径 (用于错误提示)
            file_mtime: 文件修改时间戳 (作为 date 的兜底)

        Returns:
            规范化后的 permalink

        Raises:
            ErrorWithPrompt: 遇到不支持的占位符或日期解析失败时抛出
        """

        # 1. 解析日期 (优先级: FM > 文件名 > 文件时间戳)
        pub_date: datetime.datetime | None = None

        # 尝试从 FM 读取
        if "date" in fm:
            try:
                pub_date = datetime.datetime.fromisoformat(str(fm["date"]).split("T")[0])
            except (ValueError, TypeError):
                raise ErrorWithPrompt(
                    f"文章 {file_path} 的 date 字段格式错误\n"
                    f"期望格式: YYYY-MM-DD (如 2026-07-16)\n"
                    f"当前值: {fm.get('date')}"
                )

        # 兜底使用文件修改时间
        if not pub_date:
            pub_date = self._extract_date(file_path, file_mtime)

        # 2. 准备替换映射 (仅支持这三个)
        replacements = {
            ":slug": slug,
            ":year": f"{pub_date.year:04d}",
            ":month": f"{pub_date.month:02d}",
            ":date": f"{pub_date.strftime(DATE_FORMAT)}",
        }

        # 3. 执行替换并校验
        result = fm.get("permalink", self.config.build.permalink)
        for placeholder, value in replacements.items():
            if placeholder in result:
                result = result.replace(placeholder, value)
        return result

    @staticmethod
    def _extract_date(filepath: str, mtime: float) -> datetime.datetime:
        """
        从文件路径中提取日期（从左往右扫描，找到第一个符合格式的目录/文件名）。
        支持格式：YYYY-MM-DD 或 YYYY_MM_DD
        若未找到，则使用文件修改时间 mtime；若 mtime 无效，则返回 1970-01-01。

        example:
            - /blog/_posts/content/2023_07_10/custom_font_library.md
            - /blog/_posts/content/2023-03-14/modify_nginx.md
        """
        # 1. 从左往右遍历路径中的每一级（包括根目录、各级目录、文件名）
        p = Path(filepath)
        for part in p.parts:
            # 尝试两种日期格式
            for fmt in ("%Y-%m-%d", "%Y_%m_%d"):
                try:
                    return datetime.datetime.strptime(part, fmt)
                except ValueError:
                    continue  # 此部分不匹配，继续尝试下一种格式

        # 2. 若路径中无日期信息，使用文件的修改时间
        try:
            return datetime.datetime.fromtimestamp(mtime)
        except (OSError, ValueError):
            # 3. 终极兜底
            return datetime.datetime.strptime("1970-01-01", "%Y-%m-%d")

    @staticmethod
    def _extract_description(html: str, max_chars: int = 120) -> str:
        # 1. 干掉噪音块（代码、图片、表格——技术博客最大的干扰源）
        cleaned = re.sub(
            r'<(pre|code|img|table|script|style)[^>]*>.*?</\1>',
            '',
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

        # 2. 提取所有 <p> 标签内的文本
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', cleaned, flags=re.DOTALL | re.IGNORECASE)

        for p in paragraphs:
            # 3. 去掉 <p> 内部的 HTML 标签，得到纯文本
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = re.sub(r'\s+', ' ', text)  # 合并多余空白

            # 4. 跳过太短或看起来像纯代码的行
            if len(text) < 20:
                continue
            if re.match(r'^[\w\s\.\-\>\(\)\{\}\=\+\*\/]+$', text):
                continue

            # 5. 按中英文标点断句，拼到 max_chars 为止
            sentences = re.split(r'([。！？\!?])', text)
            result_text = ''
            for i in range(0, len(sentences) - 1, 2):
                chunk = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
                if len(result_text) + len(chunk) <= max_chars:
                    result_text += chunk
                else:
                    break

            # 6. fallback：没拼出句子就用前 max_chars 字符
            if not result_text.strip():
                result_text = text[:max_chars]

            # 7. 加省略号
            if len(result_text) >= max_chars:
                result_text = result_text.rstrip('。！？.!?') + '…'

            return result_text

        # 终极 fallback：连 <p> 都没有（比如友链页、首页）
        return ""

    def build_one_post(self, file_path: str, raw_content: str, file_mtime: float) -> Article | None:
        """
        从文件路径和内容构建 Article，在这里只处理渲染流程，不负责如产物搬运等其他流程

        """
        fm, body = self.parse_front_matter(raw_content)
        if not fm:
            raise ErrorWithPrompt("解析Front Matter 错误")
        if fm.get("draft", False) is True:
            raise ErrorWithPrompt("已经设定为 draft")

        # 1. 提取或生成Slug
        slug = self._extract_slug(fm, file_path)

        # 2. 生成目标URL
        dest_url = self._generate_permalink(fm, slug, file_path, file_mtime)

        # 3. 获取必要数据，生成html
        toc = fm["x-toc"] if "x-toc" in fm else self.config.features.toc
        result = covert_to_html(body, toc=toc)

        # 4. 补充默认元数据
        fm.setdefault("layout", self.config.build.default_layout)
        fm.setdefault("title", slug)
        fm.setdefault("date", self._extract_date(file_path, file_mtime).strftime(DATE_FORMAT))

        # 统一为 str 类型
        if isinstance(fm["date"], (datetime.datetime, datetime.date)):
            fm["date"] = fm["date"].strftime(DATE_FORMAT)

        if "description" not in fm:
            description = self._extract_description(result["html"])
            if not description:
                description = fm.get("title", slug)
            fm["description"] = description

        # TODO: 在这里处理 images
        # lazy_load = fm["x-lazy-load"] if "x-lazy-load" in fm else self.config.features.lazy_load

        return Article(
            src_path=file_path,
            dest_url=dest_url,
            fm=fm,
            raw_content=body,
            rendered_html=result["html"],
            toc=result["toc"],
            images=[],
            used_code=bool(result.get("usedCode")),
            used_math=bool(result.get("usedMath")),
        )

    """
    logging.info(f"start covert one! images cache len: {len(images_cache)}")
    for img in all_images:
        try:
            full_img_path = self.adapter.storage_root + "/" + img.path.lstrip("/")
            w, h = get_image_size(full_img_path)
            img_property = ImageProperty(width=w, height=h, avif_full_path="", avif_href="")
            images_cache[img.path] = img_property

            # 计算 avif 写入路径，这里是绝对路径，根据原图的 path 替换为 avif 的 path
            base, _ = os.path.splitext(img.path)
            avif_path = base + ".avif"
            avif_full_path = self.avif_tmp_dir + "/" + avif_path.lstrip("/")
            flag, msg = covert_to_avif(full_img_path, avif_full_path)
            logging.info(f"Covert img to avif: {img.path}, result: {flag}, msg:\n\t{msg}")
            if not flag:
                continue

            # 转换成功，进行赋值
            href_base, _ = os.path.splitext(img.href)
            avif_href = href_base + ".avif"

            img_property.avif_full_path = avif_full_path
            img_property.avif_href = avif_href

        except Exception as e:
            logging.error(f"error in process image: {img.path}, e: {e}\n{traceback.format_exc()}")
    """
    # async def copy_images(self, config: SiteConfig, images: list[dict]) -> int:
    #     """
    #     迁移 md文件关联的图片文件，分三种情况：
    #
    #     # ![alt](./a.jpg)      → 相对当前页面，将图片挪动到相对于当前文件的路径下
    #     # ![alt](/a.jpg)       → 相对站点根目录 _build/ 下）
    #     # ![alt](https://...)  → 不做任何处理
    #
    #     Args:
    #         config: SiteConfig, md 文件渲染的 html 的目标位置，是包括 storage_root 的绝对路径
    #         images: list[dict], 元素为 ImageRef 结构: {
    #             'path': 'board.jpg',
    #             'href': 'board.jpg',
    #             'alt': '',
    #             'title': '',
    #         }
    #
    #
    #     # 进行静态资源的迁移
    #     count = await self.copy_images(config, post["images"])
    #     self.record_log(f"已处理 {count} 个图像对象。")
    #     """
    #     proc_count = 0
    #     if not images:
    #         return proc_count
    #
    #     logging.info(f"start copy image files, total: {len(images)}")
    #     for item in images:
    #         img_path = item["path"]
    #         target = item["href"]
    #         ip = item.get("property") or {}
    #         if ip.get("avif_full_path") and ip.get("avif_href"):
    #             # 拷贝AVIF
    #             avif_full_path = item["property"]["avif_full_path"]
    #             avif_href = item["property"]["avif_href"]
    #
    #             if config.build.base_path:
    #                 avif_href = Path(avif_href).relative_to(config.build.base_path).as_posix()
    #
    #             target_avif = "%s/%s" % (self.write_root_tmp, avif_href)
    #             target_parent, _ = os.path.split(target_avif)
    #             os.makedirs(target_parent, exist_ok=True)
    #             with open(avif_full_path, "rb") as r:
    #                 with open(target_avif, "wb") as w:
    #                     w.write(r.read())
    #
    #         if not img_path:
    #             continue
    #
    #         if config.build.base_path:
    #             target = Path(target).relative_to(config.build.base_path).as_posix()
    #
    #         img_src = "%s/%s" % (self.adapter.storage_root, img_path.lstrip('/'))
    #         img_dst = "%s/%s" % (self.write_root_tmp, target)
    #
    #         logging.debug(f"copy img file by abs way:\n"
    #                       f"\timg_src:  {img_src}\n"
    #                       f"\timg_dst: {img_dst}\n"
    #                       f"\ttarget: {target}")
    #
    #         if await self.adapter.storage.exists(img_src) and \
    #                 await self.adapter.storage.is_file(img_src):
    #             await self.adapter.storage.copy(img_src, img_dst)
    #             logging.debug(f"source img copy success: {img_src}")
    #         else:
    #             logging.warning(f"source img not exist: {img_src}")
    #         proc_count += 1
    #
    #     return proc_count