import os
import git
import time
import json
from pydantic import BaseModel
from typing import List, Dict
# from ..log4 import website_logger as logging
import logging


class Article(BaseModel):
    title: str
    content: str
    category: str
    description: str
    date: str
    ref: str
    author: str
    tags: List[str]


class DisData(BaseModel):
    articles: Dict[str, Article]  # identity to article
    tag_map: Dict[str, str]
    category_map: Dict[str, str]


class ArticleRender:
    def __init__(self,  dist_path: str, repo_root: str = "git_repo"):
        self.dist_path = dist_path
        self.storage_root = repo_root
        self.last_commit_id_file = os.path.join(repo_root, "last_commit_id")
        self.identity = f"pull_{int(time.time() * 1000)}"
        self.repo_path = os.path.join(self.storage_root, self.identity)

    def get_last_commit_id(self) -> str:
        try:
            with open(self.last_commit_id_file, "r") as f:
                return f.read()
        except:  # noqa
            return ""

    def set_last_commit_id(self, commit: str) -> None:
        with open(self.last_commit_id_file, "wb") as f:
            f.write(commit.encode("utf-8"))

    def pull_repo(self) -> git.Repo:
        repo = git.Repo.clone_from(
            url="git@github.com:cl-ei/blog.git",
            to_path=self.repo_path,
            multi_options=["--depth=1"],
        )
        return repo

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

    def parse_one_article(self, base: str, filename: str) -> Article:
        print(f"thisfile: {base}/  {filename}")

    def run(self):
        repo = self.pull_repo()
        this_commit_id = repo.commit().hexsha
        last_commit_id = self.get_last_commit_id()
        if last_commit_id == this_commit_id:
            logging.info(f"already generated, commit id: {this_commit_id}, skip.")
            return

        content_root = os.path.join(self.repo_path, "content")
        files = self.list_all_file(content_root)
        for file in files:
            base, filename = os.path.split(file)
            if "." in filename and filename.split(".")[-1].lower() == "md":
                self.parse_one_article(base, filename)

        self.set_last_commit_id(this_commit_id)
        # save history


if __name__ == "__main__":
    render = ArticleRender("dist")
    render.run()

