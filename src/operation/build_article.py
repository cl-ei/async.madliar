from typing import List, Dict
from pydantic import BaseModel, validator


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
