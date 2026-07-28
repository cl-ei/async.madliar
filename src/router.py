import os
from typing import Dict
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template


router = APIRouter()


class CachedTPL:
    cache: Dict[str, Template] = {}

    @classmethod
    def get(cls, file_name: str) -> Template:
        if file_name in cls.cache:
            return cls.cache[file_name]

        with open(file_name, "rb") as tpl_f:
            content = tpl_f.read().decode("utf-8")
        cls.cache[file_name] = Template(content)
        return cls.cache[file_name]


@router.get("/")
async def home_page() -> RedirectResponse:
    return RedirectResponse(url="/notebook/publish/i/caoliang.net/index.html")


@router.get("/old")
async def old_blog() -> HTMLResponse:
    DIST_ARTICLE_PATH = "src/static/blog/dist_article"  # noqa

    article_js_file_name = ""
    for file in os.listdir(DIST_ARTICLE_PATH):
        if file.lower().endswith(".js"):
            article_js_file_name = file
            break

    article_js_link = f"/static/blog/dist_article/{article_js_file_name}"
    context = {
        "article_js_link": article_js_link,
        "page": {
            "author": "CL",
            "description": u"CL，编程爱好者，这是CL的官方博客，记录生活感悟和学习点滴。",
            "keywords": u"MADLIAR, CL, CL's 疯言疯语, 疯言疯语, 风言风语, CL博客",
        },
        "CDN_URL": "",
    }
    html = CachedTPL.get("src/tpl/old.html").render(context)
    return HTMLResponse(html)
