import os
import re
import shutil
import subprocess
import time
from typing import List, Dict

import git
from pydantic import BaseModel, validator
from xpinyin import Pinyin
from ..config import BLOG_REPO_ROOT, BLOG_DIST_PATH, BLOG_STATIC_PREFIX, LAST_COMMIT_FILE
from ..log4 import website_logger as logging


class ArticleHeader(BaseModel):
    title: str = ""
    category: str = ""
    description: str = ""
    date: str = ""
    ref: str = ""
    author: str = ""
    tags: List[str] = []


class Article(ArticleHeader):
    identity: str
    content: str

    @validator("identity", pre=True)
    def valid_identity(cls, value: str) -> str:
        result = []
        valid_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-+._ /'
        for c in value:
            if c in valid_chars:
                result.append(c)
        if len(result) == 0:
            raise ValueError(f"Error value: {value}")
        return "".join(result)


class DistData(BaseModel):
    articles: Dict[str, Article]  # article.identity to article
    tag_map: Dict[str, List[str]]  # tag to list of article.identity
    category_map: Dict[str, List[str]]  # category to list of article.identity

    @property
    def nature_list(self) -> List[Article]:
        """
        返回自然序列表

        Returns
        -------
        Dict[str, str]: inner title to identity
        """
        art_list: List[Article] = [a for _, a in self.articles.items()]
        art_list.sort(key=lambda a: a.identity, reverse=True)
        return art_list


class ArticleRender:
    def __init__(self):
        self.dist_path = BLOG_DIST_PATH
        self.static_root = BLOG_STATIC_PREFIX
        self.storage_root = BLOG_REPO_ROOT

        self.last_commit_id_file = LAST_COMMIT_FILE
        self.identity = f"pull_{int(time.time() * 1000)}"
        self.repo_path = os.path.join(self.storage_root, self.identity)

        self.remote_repo = "git@github.com:cl-ei/blog.git"

    def get_remote_commit_id(self) -> str:
        """return 8 bytes"""
        process = subprocess.Popen(["git", "ls-remote", self.remote_repo], stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        sha = stdout.decode().split("HEAD")[0].split("\t")[0]
        return sha[:8]

    def get_last_commit_id(self) -> str:
        try:
            with open(self.last_commit_id_file, "rb") as f:
                return f.read().decode("utf-8")
        except:  # noqa
            return ""

    def set_last_commit_id(self, commit: str) -> None:
        with open(self.last_commit_id_file, "wb") as f:
            f.write(commit.encode("utf-8"))

    def pull_repo(self) -> git.Repo:
        error = None
        for try_time in range(5):
            try:
                logging.debug("try fetch origin repo...")
                repo = git.Repo.clone_from(url=self.remote_repo, to_path=self.repo_path, multi_options=["--depth=1"])
                return repo
            except git.CommandError as e:
                logging.error(f"try {try_time} cannot fetch repo: {e}")
                error = e
                time.sleep(5)
                continue
        raise ValueError(f"e: {error}") from error

    @staticmethod
    def list_all_file(path: str) -> List[str]:
        scan = [path]
        result = []
        while scan:
            path = scan.pop()
            for file in os.listdir(path):
                rel_path = os.path.join(path, file)
                if os.path.isfile(rel_path):
                    result.append(rel_path)
                elif os.path.isdir(rel_path):
                    scan.append(rel_path)
        result.sort()
        return result

    @staticmethod
    def parse_header(header: str) -> ArticleHeader:
        valid_keys = set(ArticleHeader().dict().keys())
        create_param = {}
        lines = header.split("\n")
        for line in lines:
            kv = line.split(":", 1)
            if len(kv) != 2:
                continue
            key = kv[0].strip(" ")
            if key not in valid_keys:
                continue
            value = kv[1].strip(" ")
            if key == "tags":
                value = [v.strip() for v in value.split(",")]
            if key == "description":
                value = value.replace("\"", "")
            create_param[key] = value
        return ArticleHeader(**create_param)

    @ staticmethod
    def move_image(source: str, dist: str) -> None:
        path, _ = os.path.split(dist)
        os.makedirs(path, exist_ok=True)
        with open(source, "rb") as read_f:
            with open(dist, "wb") as write_f:
                write_f.write(read_f.read())

    def parse_body(self, base: str, body: str, this_commit_id: str, date: str) -> str:
        """
        在这里处理 body，寻找图片、替换路径并移动到static文件夹

        Args
        ----
        base: md 文件所在的路径
        body: md body部分
        this_commit_id: 最新的commit id
        """
        matches = re.findall(r"(!\[[^\n]*?\]\([^\n]+?\))", body)
        replace_map: Dict[str, str] = {}
        for m in matches:
            # m: ![desc](path)
            path_start_index = m.find("](") + 2
            img_path = m[path_start_index:-1]

            origin_image_path = os.path.join(base, img_path)
            dist_image_path = os.path.join(self.dist_path, this_commit_id, date, img_path)
            self.move_image(source=origin_image_path, dist=dist_image_path)

            static_path = os.path.join(self.static_root, this_commit_id, date, img_path)
            replace = m[:path_start_index] + static_path + ")"
            replace_map[m] = replace
            logging.debug(f"img_path: {img_path}, m: {m}, static_path: {static_path}, replace: {replace}")

        for origin, rep in replace_map.items():
            body = body.replace(origin, rep)
        return body

    def parse_one_article(self, base: str, filename: str, this_commit_id: str) -> Article:
        full_path = os.path.join(base, filename)
        with open(full_path, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")

        inner = content.strip("\r\n").lstrip("---").lstrip("\r\n")
        split_index = inner.index("---")
        header, body = inner[:split_index], inner[split_index + 3:].lstrip("\r\n")

        header = self.parse_header(header)
        if not header.date:
            header.date = os.path.split(base.rstrip("/"))[-1]
        if not header.title:
            header.title = filename.split(".", 1)[0]
        if not header.category:
            header.category = "未分类"
        parsed_body = self.parse_body(base, body, this_commit_id, header.date)

        article_id = Pinyin().get_pinyin(f"{header.date}/{header.title}")
        article = Article(identity=article_id, content=parsed_body, **header.dict())
        return article

    def run(self):
        this_commit_id = self.get_last_commit_id()
        if this_commit_id:
            remote_commit_id = self.get_remote_commit_id()
            if this_commit_id == remote_commit_id:
                logging.info(f"already generated, commit id: {this_commit_id}, skip.")
                return

        repo = self.pull_repo()
        this_commit_id = repo.commit().hexsha[:8]
        dist_data = DistData(articles={}, tag_map={}, category_map={})

        content_root = os.path.join(self.repo_path, "content")
        files = self.list_all_file(content_root)
        for file in files:
            base, filename = os.path.split(file)
            if "." in filename and filename.split(".")[-1].lower() == "md":
                article = self.parse_one_article(base, filename, this_commit_id)
                # todo: process conflict
                dist_data.articles[article.identity] = article
                for tag in article.tags:
                    dist_data.tag_map.setdefault(tag, []).append(article.identity)
                if article.category:
                    dist_data.category_map.setdefault(article.category, []).append(article.identity)

        # 整理
        filtered_tags = {}
        for tag, data in dist_data.tag_map.items():
            filtered_tags[tag] = sorted(list(set(data)))
        dist_data.tag_map = filtered_tags
        filtered_categories = {}
        for category, data in dist_data.category_map.items():
            filtered_categories[category] = sorted(data)
        dist_data.category_map = filtered_categories

        # save
        dis_data = os.path.join(self.dist_path, this_commit_id, "__dist.json")
        bash_path, _ = os.path.split(dis_data)
        os.makedirs(bash_path, exist_ok=True)
        with open(dis_data, "wb") as f:
            f.write(dist_data.json(ensure_ascii=False).encode("utf-8", errors="replace"))

        # save history
        self.set_last_commit_id(this_commit_id)
        shutil.rmtree(self.storage_root)
        logging.info("generate finished.")


def pull_and_flush():
    render = ArticleRender()
    render.run()
