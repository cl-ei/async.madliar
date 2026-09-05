import logging
import os.path
import re
import yaml
import datetime
from xpinyin import Pinyin
from src.error import ErrorWithPrompt
from bs4 import BeautifulSoup
from pathlib import Path
from .schema import SiteConfig, Article, ImageProcResult, ImageRef
from src.ssg.marked.bridge import covert_to_html
from src.ssg.img_preparing import process_image


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

    def __init__(self, config: SiteConfig, storage_root: str, write_root: str):
        self.config = config
        self.storage_root = storage_root
        self.write_root: str = write_root

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

        abs_filepath = (Path(self.storage_root) / file_path.lstrip("/")).as_posix()
        html, images = self.process_images_in_html(
            html=result["html"],
            filepath=abs_filepath,
            storage_root=self.storage_root,
            write_root=self.write_root,
            dest_url=dest_url,
        )

        return Article(
            src_path=file_path,
            dest_url=dest_url,
            fm=fm,
            raw_content=body,
            rendered_html=html,
            toc=result["toc"],
            images=images,
            used_code=bool(result.get("usedCode")),
            used_math=bool(result.get("usedMath")),
        )

    @staticmethod
    def process_images_in_html(
            html: str, filepath: str, storage_root: str, write_root: str, dest_url: str) -> tuple[str, list[ImageRef]]:
        """
        处理每篇文章的图片路径

        Args:
            html: marked 输出的 HTML 字符串
            filepath: 该 markdown 文件所在的【绝对路径】
            storage_root: 用户的根目录
            write_root: 写入目录的根路径
            dest_url: 文章的目标 URL

        Returns:
            str: html
            images: List[ImageRef]

        由于 windows 不允许存在与目录同名的文件，必须曲线救国了。这里的做法是 write_root 下建一个 images 文件夹，这样可以避免冲突
        针对绝对路径引用的情况：
            - 保留其绝对路径，相当于把文件从 storage_root 节点连带路径，切到 write_root/images 下。
            - src 即它原来的绝对路径
        相对路径：
            - 获取原始文件路径
            - 写入到 write_root/images/<dest_url>/<rel_path> 下面
        src 为该文件相对于 write_root 的剩余路径
        """
        collected_images: list[ImageRef] = []
        soup = BeautifulSoup(html, 'html.parser')
        imgs = soup.find_all('img')

        # target_path 走过了 resolve()，必须用同样 resolve 过的根来算相对路径，
        # 否则 write_root 是相对路径、或含 .. 时 relative_to 会直接抛 ValueError
        write_root_resolved = Path(write_root).resolve()
        # 同一篇文章里多处引用同一张图时只处理一次（avif 编码很慢）
        handled: dict[str, ImageProcResult] = {}

        for img in imgs:
            # 1. 拿到原始 src（Markdown 里写的路径）
            raw_src = img.get('src', '')
            if not raw_src:
                continue

            # 2. 外链 / 内联数据等，不参与静态资源迁移
            if raw_src.startswith(("https://", "http://", "//", "file://", "data:", "blob:", "#", "?")):
                continue

            # 3. 解析为磁盘绝对路径与目标写入路径
            if raw_src.startswith("/"):  # 绝对路径，参照用户根目录
                source_path = (Path(storage_root) / raw_src.lstrip("/")).resolve()
                target_path = (write_root_resolved / "images" / raw_src.lstrip("/")).resolve()
            else:  # 相对路径，参照 md 文件所在目录
                source_path = (Path(filepath).parent / raw_src).resolve()
                target_path = (write_root_resolved / "images" / dest_url.lstrip("/") / raw_src).resolve()

            src = "/" + target_path.relative_to(write_root_resolved).as_posix()

            if not source_path.exists():
                print(f"  ⚠ 图片不存在: {source_path}, filepath: {filepath}, raw_src: {raw_src}, storage root: {storage_root}")
                continue

            key = target_path.as_posix()
            if key not in handled:
                handled[key] = process_image(source_path.as_posix(), target_path.as_posix())
            result: ImageProcResult = handled[key]

            img['src'] = src
            img['loading'] = 'lazy'
            img['decoding'] = 'async'

            # ---- 私有扩展：![描述 powerstyle={...}](url) ----
            # 样式写在 alt 里只为书写顺手，渲染时必须剥离：
            # alt 是无障碍语义（屏幕阅读器朗读、图片加载失败时的替代文本），不能混入样式
            raw_alt = img.get('alt') or ''
            style_match = re.search(r'\s*powerstyle=\{([^}]*)\}', raw_alt)
            if style_match:
                # 黑名单剔除：只干掉能逃逸 HTML 属性/标签边界的字符，
                # 其余一律放行（; : % # ( ) + 等在 CSS 里都是合法且必需的）
                img['style'] = re.sub(r'[<>"\'&\\\r\n]', '', style_match.group(1).strip())
                raw_alt = (raw_alt[:style_match.start()] + raw_alt[style_match.end():]).strip()
            img['alt'] = raw_alt or source_path.stem

            # 解析失败时宽高为 0，此时不写死尺寸，留给浏览器按原图自适应
            if result.width > 0 and result.height > 0:
                img['width'] = str(result.width)
                img['height'] = str(result.height)

            # avif 与主图同目录同名，仅扩展名不同；主图本身就是 avif 时无需再包一层
            avif_path = target_path.with_suffix('.avif')
            avif_src = ""
            if result.avif and avif_path != target_path:
                picture = soup.new_tag('picture')
                img.wrap(picture)  # 用 picture 占据 img 原位，img 成为其子节点
                source = soup.new_tag('source')
                avif_src = '/' + avif_path.relative_to(write_root_resolved).as_posix()
                source['srcset'] = avif_src
                source['type'] = 'image/avif'
                picture.insert(0, source)  # source 必须排在 img 之前

            collected_images.append(ImageRef(
                src=img['src'],
                alt=img['alt'],
                title=img['alt'],
                width=result.width,
                height=result.height,
                avif_src=avif_src,
            ))
        return str(soup), collected_images
