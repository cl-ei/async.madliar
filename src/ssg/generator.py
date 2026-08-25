import copy
import hashlib
import logging
import os.path
import traceback
from asyncio.queues import Queue
import re
import yaml
import datetime
from pathlib import Path
import jinja2
from src.error import ErrorWithPrompt
from .schema import SiteConfig, Article, SITE_CONFIG_FILE, ImageRef, ImageProperty
from .filesystem.user_fs_adapter import UserFSAdapter
from .parsing import ArticleBuilder
from .templating import render_layout
from .img_preparing import get_image_size, covert_to_avif
_VALID_LASTMOD = re.compile(
    r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$'
)


async def parse_user_site_config(email: str) -> SiteConfig:
    """
    解析用户站点配置文件

    Args:
        email: 用户 email

    Returns:
        SiteConfig: 解析后的配置对象

    Raises:
        ErrorWithPrompt: 配置解析错误时抛出友好提示
    """
    adapter = UserFSAdapter(email)
    site_config_file = f"{adapter.storage_root.rstrip('/')}/{SITE_CONFIG_FILE}"
    if not await adapter.storage.exists(site_config_file) or not await adapter.storage.is_file(site_config_file):
        raise ErrorWithPrompt(
            f"配置文件不存在。\n\n"
            f"请在站点根目录创建 {SITE_CONFIG_FILE} 文件。\n"
            f"可参考示例配置：_site_config.example.yaml"
        )
    try:
        content = await adapter.storage.read_text(site_config_file)
    except:  # noqa
        raise ErrorWithPrompt("配置文件内容错误")

    try:
        try:
            config_dict = yaml.safe_load(content)
        except yaml.YAMLError as e:
            # 提取更友好的YAML错误信息
            error_line = ""
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                error_line = f"（第 {mark.line + 1} 行，第 {mark.column + 1} 列）"

            raise ErrorWithPrompt(
                f"配置文件语法错误{error_line}：\n"
                f"{str(e)}\n\n"
                f"常见原因：\n"
                f"1. 冒号后缺少空格（正确：'key: value'，错误：'key:value'）\n"
                f"2. 缩进使用Tab键（请使用空格）\n"
                f"3. 字符串包含特殊字符未加引号\n"
                f"4. 列表项格式错误\n\n"
                f"可参考示例配置：_site_config.example.yaml"
            )

    except Exception as e:
        raise ErrorWithPrompt(
            f"无法读取配置文件：{str(e)}\n\n"
            f"请检查文件权限或路径是否正确。"
        )

    # 4. 检查配置内容是否为空
    if not config_dict:
        raise ErrorWithPrompt(
            f"配置文件为空或格式不正确。\n\n"
            f"请确保文件包含有效的YAML配置内容。\n"
            f"可参考示例配置：_site_config.example.yaml"
        )

    # 5. 使用Pydantic V2解析配置
    try:
        site_config = SiteConfig.model_validate(config_dict)  # V2 语法：model_validate
        return site_config

    except ErrorWithPrompt:
        # 直接重新抛出我们自定义的验证错误
        raise
    except Exception as e:
        # 处理Pydantic验证错误
        if hasattr(e, 'errors'):
            # Pydantic验证错误，格式化错误信息
            error_messages = []
            for error in e.errors():
                field_path = ' → '.join(str(loc) for loc in error['loc'])
                message = error['msg']

                # 提供更友好的字段描述
                if 'site' in error['loc']:
                    if 'name' in error['loc']:
                        message = "站点名称不能为空，请设置 site.name"
                    elif 'url' in error['loc']:
                        message = "站点URL不能为空，请设置 site.url"

                error_messages.append(f"字段 '{field_path}': {message}")

            formatted_errors = '\n'.join(f"  • {msg}" for msg in error_messages)
            raise ErrorWithPrompt(
                f"配置文件验证失败，发现 {len(error_messages)} 个问题：\n\n"
                f"{formatted_errors}\n\n"
                f"请修正以上问题后重试。\n"
                f"可参考示例配置：_site_config.example.yaml"
            )
        else:
            # 其他未知错误，不暴露内部细节
            raise ErrorWithPrompt(
                f"配置文件解析失败，请检查格式是否正确。\n\n"
                f"可参考示例配置：_site_config.example.yaml"
            )


def is_markdown_file(filename: str) -> bool:
    """
    Markdown文件过滤器，支持常见扩展名、大小写不敏感、自动排除临时文件
    支持的扩展名覆盖：
    - 标准扩展名：.md/.markdown
    - 常用别名：.mdown/.mkd/.mkdn/.mdwn/.mdtxt
    - 生态扩展名：.mdx(RMarkdown)/.rmd(RStudio)/.jmd(Julia)/.qmd(Quarto)/.litmd(Literate)
    """
    # 支持的Markdown扩展名集合（frozenset保证O(1)查找效率+不可变性）
    md_extensions = frozenset({
        '.md', '.markdown',  # 最通用标准扩展名
        '.mdown', '.mkd', '.mkdn', '.mdwn', '.mdtxt',  # 历史别名/小众变种
        '.mdx',  # React MDX
        '.rmd',  # R Markdown
        '.jmd',  # Julia Markdown
        '.qmd',  # Quarto Markdown
        '.litmd',  # Literate Markdown
    })

    # 需排除的临时/备份文件后缀（避免编辑器生成的临时文件被误判）
    excluded_suffixes = frozenset({'~', '.bak', '.swp', '.swap', '.tmp'})

    # 空文件名直接排除
    if not filename:
        return False

    # 排除隐藏文件（以.开头的文件，如.config.md，可按需调整）
    if filename.startswith('.'):
        return False

    # 排除临时/备份文件
    if any(filename.endswith(suffix) for suffix in excluded_suffixes):
        return False

    # 提取扩展名（转小写，兼容Windows/macOS/Linux的大小写差异）
    file_ext = Path(filename).suffix.lower()
    return file_ext in md_extensions


class StaticSiteGenerator:
    def __init__(self, email: str):
        self.email = email
        self.adapter = UserFSAdapter(email)
        self.err_q: Queue = Queue()

        self._config: SiteConfig | None = None
        self._write_root: str = ""
        self._layouts_root: str = ""

    async def load_config(self) -> SiteConfig:
        if self._config is None:
            self._config = await parse_user_site_config(self.email)
        return self._config

    @property
    def write_root_tmp(self) -> str:
        return f"{self.adapter.meta_root}/static_site"

    @property
    def avif_tmp_dir(self) -> str:
        return f"{self.adapter.storage_root}/__avif_tmp__"

    @property
    def write_root(self) -> str:
        if self._write_root:
            return self._write_root

        if not self._config:
            raise ErrorWithPrompt("配置不正确，未能获取 write_root")

        write_root = "%s/%s/%s" % (self.adapter.storage_root, self._config.build.source_root.strip('/'), "_build")
        self._write_root = self.adapter.resolve(write_root)
        return self._write_root

    @property
    def layouts_root(self) -> str:
        if self._layouts_root:
            return self._layouts_root

        if not self._config:
            raise ErrorWithPrompt("配置不正确，未能获取 layouts_root")
        layouts_root = "%s/%s/%s" % (self.adapter.storage_root, self._config.build.source_root, "_layouts")
        self._layouts_root = self.adapter.resolve(layouts_root)
        return self._layouts_root

    def record_log(self, msg: str):
        self.err_q.put_nowait(f"{datetime.datetime.now()} {msg}")

    async def _do_generate(self, config: SiteConfig):
        logging.info(f"start generate static site: {self.email}")

        self.record_log(f"{SITE_CONFIG_FILE} 加载成功。")

        # 扫描所有Markdown文件
        # 有两种生成方式：
        # 1. 全部读取、转换、构建context，然后挨个渲染，可能会在文章过多时造成内存占用过高。目前
        #   使用此方法生成。
        # 2. 第一遍扫描所有文章的元信息，再挨个读取文章的content、转换、构建context，然后
        #   挨个渲染。能够控制内存占用，后续可以按此法优化。
        posts_path = f"{config.build.source_root.rstrip('/')}/_posts"
        all_files: list[str] = await self.adapter.find_files(posts_path, is_markdown_file)
        self.record_log(f"已获取posts总数：{len(all_files)}。")

        # 统计静态资源
        all_images: list[ImageRef] = []
        collector = ArticleBuilder(config, self.adapter.storage_root, {})
        for file_path in all_files:
            try:
                # 读取源文件
                full_path = f"{self.adapter.storage_root}/{file_path.lstrip('/')}"
                raw_content = await self.adapter.storage.read_text(full_path)
                filesize, file_mtime = await self.adapter.storage.stat(full_path)

                # 构建Article对象
                try:
                    article: Article = collector.build_one_post(file_path, raw_content, file_mtime)
                    all_images.extend(article.images)
                except ErrorWithPrompt:
                    pass
            except Exception as e:
                logging.warning(f"error happened when collect: {e}\n{traceback.format_exc()}")
                continue

        # 准备写入！清除临时输出目录
        if (await self.adapter.storage.exists(self.write_root_tmp) and
                await self.adapter.storage.is_dir(self.write_root_tmp)):
            await self.adapter.storage.remove_tree(self.write_root_tmp)

        logging.info(f"total images: {len(all_images)}")
        images_cache: dict[str, ImageProperty] = {}  # path -> ImageProperty
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
                if not flag:
                    logging.error(f"cannot covert img {img.path}, msg:\n\t{msg}")
                    continue

                # 转换成功，进行赋值
                href_base, _ = os.path.splitext(img.href)
                avif_href = href_base + ".avif"

                img_property.avif_full_path=avif_full_path
                img_property.avif_href=avif_href

            except Exception as e:
                logging.error(f"error in process image: {img.path}, e: {e}\n{traceback.format_exc()}")

        # 构建文章列表，解析基础信息
        logging.info(f"start covert one! images cache len: {len(images_cache)}")
        url_to_src_path: dict[str, str] = {}  # 检测 URL 冲突之用
        article_builder = ArticleBuilder(config, self.adapter.storage_root, images_cache)
        all_posts: dict[str, list[Article]] = {}  # layout -> [articles...]
        for file_path in all_files:
            try:
                # 读取源文件
                full_path = f"{self.adapter.storage_root}/{file_path.lstrip('/')}"
                raw_content = await self.adapter.storage.read_text(full_path)
                filesize, file_mtime = await self.adapter.storage.stat(full_path)

                # 构建Article对象
                try:
                    article: Article = article_builder.build_one_post(file_path, raw_content, file_mtime)
                except ErrorWithPrompt as e:
                    self.record_log(f"文件{file_path}解析时发生错误：{e.msg}。")
                    continue
                except Exception as e:
                    logging.error(f"error happened when build one post: {e}\n{traceback.format_exc()}")
                    self.record_log(f"文件{file_path}解析时发生错误。")
                    continue

                # 套用模板
                layout_name = article.fm["layout"]

                layout_filename = layout_name if layout_name.endswith(".html") else f"{layout_name}.html"
                layout = f"{self.layouts_root}/{layout_filename}"
                if not await self.adapter.storage.exists(layout):
                    self.record_log(f"未找到文件{file_path}声明的layout “{layout_name}”，跳过处理。")
                    continue

                all_posts.setdefault(layout_name, []).append(article)
            except Exception as e:
                self.record_log(f"在解析{file_path}时发生错误：{e}。")
                print(f"parse one error: {e}\n{traceback.format_exc()}")
                # 继续处理其他文件，不中断构建
                continue

            # 检查地址冲突
            if article.dest_url in url_to_src_path:
                raise ErrorWithPrompt(f"URL已被占用，重复文件：{article.src_path}, {url_to_src_path[article.dest_url]}")
            url_to_src_path[article.dest_url] = article.src_path

        # 聚合数据
        context = {"site": config.site.model_dump()}
        user_defined_layouts: list[str] = []
        tags_map: dict[str, list] = {}
        categories_map: dict[str, list] = {}
        for layout_name, articles in all_posts.items():
            articles.sort(key=lambda a: a.fm.get("date", ""), reverse=True)
            for i, article in enumerate(articles):
                article.index = i

            user_defined_layouts.append(layout_name)
            context[layout_name] = [a.model_dump() for a in articles]

            for data in context[layout_name]:
                sa: dict = copy.deepcopy(data)
                for key in ("raw_content", "rendered_html", "toc", "images", "code_css"):
                    sa.pop(key)
                for tag in sa["fm"].get("tags", []):
                    tags_map.setdefault(tag, []).append(sa)

                raw_cate = sa["fm"].get("category")
                if isinstance(raw_cate, str):
                    categories_map.setdefault(raw_cate, []).append(sa)
                elif isinstance(raw_cate, (list, tuple)):
                    for cate in raw_cate:
                        categories_map.setdefault(cate, []).append(sa)
        context["tags"] = tags_map
        context["categories"] = categories_map

        user, service = self.email.split("@", 1)
        context["email"] = self.email
        context["user"] = user
        context["service"] = service

        # 写入文件，移动产物
        sitemap = []
        create_sitemap = False
        if config.build.sitemap is True and config.site.url:
            self.record_log("将创建sitemap。")
            create_sitemap = True
        else:
            self.record_log("不会创建sitemap。")

        for layout_name in user_defined_layouts:
            for post in context[layout_name]:
                ctx = copy.deepcopy(context)
                ctx["this"] = copy.deepcopy(post)
                ctx["_ctx"] = ctx

                layout_filename = layout_name if layout_name.lower().endswith(".html") else f"{layout_name}.html"
                layout = f"{self.layouts_root}/{layout_filename}"
                try:
                    final_html = await render_layout(
                        layouts_root=self.layouts_root,
                        layout_file=layout,
                        context=ctx,
                        adapter=self.adapter,
                    )
                except jinja2.exceptions.TemplateNotFound:
                    self.record_log(f"未找到layout文件“{layout_name}”，跳过处理：{post['src_path']}。")
                    continue

                except jinja2.exceptions.UndefinedError as e:
                    self.record_log(f"渲染文件{post['src_path']}时出错：{e}, 已跳过。")
                    continue

                except jinja2.exceptions.TemplateSyntaxError as e:
                    self.record_log(f"渲染文件{post['src_path']}时检测到模板格式错误：{e}, 已跳过。")
                    continue

                # 写入文件
                # 分两步，避免 permalink 为“/”或空，导致生成包含非预期的“//”的问题
                dst_url = post["dest_url"]
                if not dst_url:
                    filepath = f"{self.write_root_tmp}/index.html"
                elif dst_url.endswith("/"):
                    filepath = f"{self.write_root_tmp}/{dst_url}/index.html"
                else:
                    filepath = f"{self.write_root_tmp}/{dst_url}.html"
                await self.adapter.storage.write_text(filepath, final_html)
                self.record_log(f"已生成：{post['dest_url']}。")

                # 进行静态资源的迁移
                count = await self.copy_images(config, post["images"])
                self.record_log(f"已处理 {count} 个图像对象。")

                # 添加进 site map
                if create_sitemap:
                    sitemap.append([post.get("fm", {}).get("lastmod"), f"{config.site.url}{post['dest_url']}"])

        if create_sitemap:
            content = self._gen_sitemap_content(sitemap)
            filepath = f"{self.write_root_tmp}/sitemap.xml"
            await self.adapter.storage.write_text(filepath, content)
            self.record_log(f"sitemap已生成，大小：{len(content)}。")

        # 写日志
        print("generate complete!\n")
        self.record_log(f"生成结束。")
        log_file = f"{self.write_root_tmp}/build.log"
        contents = []
        while not self.err_q.empty():
            contents.append(self.err_q.get_nowait())
        await self.adapter.storage.write_text(log_file, '\n'.join(contents))

        # 移动到目标目录
        if await self.adapter.storage.exists(self.write_root) and \
                await self.adapter.storage.is_dir(self.write_root):
            await self.adapter.storage.remove_tree(self.write_root)
        await self.adapter.move_meta_to_storage(self.write_root_tmp, self.write_root)

        # 拷贝静态文件，这里必须将其设置为真实的 self.write_root
        # 实际上，这里会产生毫秒级的中断，因为是先切目录、后拷贝。
        # 不愿意破坏 copy_tree 只在用户 storage 目录下操作的规定，因此这个问题不修复
        statics_dir = "%s/%s" % (self.adapter.storage_root, config.build.statics_dir)
        if config.build.statics_dir and \
                await self.adapter.storage.exists(statics_dir) and \
                await self.adapter.storage.is_dir(statics_dir):
            await self.adapter.copy_tree(src=statics_dir, dst=self.write_root)
            self.record_log(f"静态文件拷贝成功。")
        else:
            self.record_log(f"跳过拷贝静态文件。")

    @staticmethod
    def _gen_sitemap_content(sitemap: list) -> str:
        parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

        for lastmod, loc in sitemap:
            entry = '  <url>\n'
            entry += f'    <loc>{loc}</loc>'
            if isinstance(lastmod, str) and _VALID_LASTMOD.match(lastmod.strip()):
                entry += f'\n    <lastmod>{lastmod.strip()}</lastmod>'
            entry += '\n  </url>'
            parts.append(entry)

        parts.append('</urlset>')
        return '\n'.join(parts)

    async def copy_images(self, config: SiteConfig, images: list[dict]) -> int:
        """
        迁移 md文件关联的图片文件，分三种情况：

        # ![alt](./a.jpg)      → 相对当前页面，将图片挪动到相对于当前文件的路径下
        # ![alt](/a.jpg)       → 相对站点根目录 _build/ 下）
        # ![alt](https://...)  → 不做任何处理

        Args:
            config: SiteConfig, md 文件渲染的 html 的目标位置，是包括 storage_root 的绝对路径
            images: list[dict], 元素为 ImageRef 结构: {
                'path': 'board.jpg',
                'href': 'board.jpg',
                'alt': '',
                'title': '',
            }
        """
        proc_count = 0
        if not images:
            return proc_count

        logging.info(f"start copy image files, total: {len(images)}")
        for item in images:
            img_path = item["path"]
            target = item["href"]
            ip = item.get("property") or {}
            if ip.get("avif_full_path") and ip.get("avif_href"):
                # 拷贝AVIF
                avif_full_path = item["property"]["avif_full_path"]
                avif_href = item["property"]["avif_href"]

                if config.build.base_path:
                    avif_href = Path(avif_href).relative_to(config.build.base_path).as_posix()

                target_avif = "%s/%s" % (self.write_root_tmp, avif_href)
                target_parent, _ = os.path.split(target_avif)
                os.makedirs(target_parent, exist_ok=True)
                with open(avif_full_path, "rb") as r:
                    with open(target_avif, "wb") as w:
                        w.write(r.read())

            if not img_path:
                continue

            if config.build.base_path:
                target = Path(target).relative_to(config.build.base_path).as_posix()

            img_src = "%s/%s" % (self.adapter.storage_root, img_path.lstrip('/'))
            img_dst = "%s/%s" % (self.write_root_tmp, target)

            logging.debug(f"copy img file by abs way:\n"
                          f"\timg_src:  {img_src}\n"
                          f"\timg_dst: {img_dst}\n"
                          f"\ttarget: {target}")

            if await self.adapter.storage.exists(img_src) and \
                    await self.adapter.storage.is_file(img_src):
                await self.adapter.storage.copy(img_src, img_dst)
                logging.debug(f"source img copy success: {img_src}")
            else:
                logging.warning(f"source img not exist: {img_src}")
            proc_count += 1

        return proc_count

    async def gen(self) -> tuple[bool, str]:
        error_msg = ""

        try:
            config = await self.load_config()
            if config is None:
                return False, "未能加载 _site_config.yaml"

            await self._do_generate(config)
        except ErrorWithPrompt as e:
            self.record_log(f"发生错误：{e.msg}。")
            error_msg = e.msg
        except Exception as e:
            logging.error(f"error happened in _do_generate: {e}\n{traceback.format_exc()}")
            self.record_log(f"发生未知错误。")
            error_msg = "致命错误"

        return False if error_msg else True, error_msg
