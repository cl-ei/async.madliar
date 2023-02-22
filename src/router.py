import os
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from jinja2 import Template
from typing import Dict


router = APIRouter()


class CachedTPL:
    cache: Dict[str, Template] = {}

    @classmethod
    def get(cls, file_name: str) -> Template:
        if file_name in cls.cache:
            return cls.cache[file_name]

        with open(file_name, "r") as tpl_f:
            content = tpl_f.read()
        cls.cache[file_name] = Template(content)
        return cls.cache[file_name]


@router.get("/")
async def home_page() -> HTMLResponse:
    html = CachedTPL.get("src/tpl/home.html").render({"CDN_URL": ""})
    return HTMLResponse(content=html)


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


@router.get("/music")
async def music(ref: str = Query("")) -> HTMLResponse:
    context = {"ref": bool(ref), "music_list": [], "CDN_URL": ""}
    return HTMLResponse(CachedTPL.get("src/tpl/music.html").render(context))
