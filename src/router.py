import os
import json
from multiprocessing import Process
from typing import Dict
from fastapi import APIRouter, Query, Path, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
from .config import LAST_COMMIT_FILE, BLOG_DIST_PATH
from .operation.build_article import DistData, pull_and_flush
from . import error


router = APIRouter()


class CachedDistData:
    cache: Dict[str, DistData] = {}

    @classmethod
    def get(cls) -> DistData:
        with open(LAST_COMMIT_FILE, "rb") as f:
            last_commit_id = f.read().decode("utf-8")

        if last_commit_id in cls.cache:
            return cls.cache[last_commit_id]

        with open(os.path.join(BLOG_DIST_PATH, last_commit_id, "__dist.json"), "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        dist_data = DistData(**json.loads(content))
        cls.cache[last_commit_id] = dist_data

        # pop old
        antiquated_keys = [k for k in cls.cache if k != last_commit_id]
        for k in antiquated_keys:
            cls.cache.pop(k)

        return dist_data


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


@router.get("/music")
async def music(ref: str = Query("")) -> HTMLResponse:
    context = {"ref": bool(ref), "music_list": [], "CDN_URL": ""}
    return HTMLResponse(CachedTPL.get("src/tpl/music.html").render(context))


@router.get("/blog")
async def blog_home() -> HTMLResponse:
    dist_data = CachedDistData.get()
    ctx = {"page": "home", "articles": [a.dict() for a in dist_data.nature_list]}
    html = CachedTPL.get("src/tpl/new_home.html").render(ctx)
    return HTMLResponse(html)


@router.get("/blog/category")
async def blog_category() -> HTMLResponse:
    dist_data = CachedDistData.get()
    ctx = {"page": "category", "dist_data": dist_data}
    html = CachedTPL.get("src/tpl/new_home.html").render(ctx)
    return HTMLResponse(html)


@router.get("/blog/about")
async def blog_about() -> HTMLResponse:
    ctx = {"page": "about"}
    html = CachedTPL.get("src/tpl/new_home.html").render(ctx)
    return HTMLResponse(html)


@router.get("/blog/article/{date}/{sub_identity}")
async def blog_article(date: str = Path(...), sub_identity: str = Path(..., )) -> HTMLResponse:
    identity = f"{date}/{sub_identity}"
    dist_data = CachedDistData.get()
    if identity not in dist_data.articles:
        raise error.NotFound()

    article = dist_data.articles[identity].dict()
    ctx = {"page": "article", "article": article}
    html = CachedTPL.get("src/tpl/new_home.html").render(ctx)
    return HTMLResponse(html)


@router.post("/blog/flush")
async def blog_flush(password: str = Body(..., embed=True)):
    if password != "3.141592653589797":
        raise error.Forbidden()
    p = Process(target=pull_and_flush)
    p.start()
    return {"code": 0, "msg": "ok"}


@router.get("/fake")
async def fake_img():
    html = CachedTPL.get("src/tpl/fake.html").render({})
    return HTMLResponse(html)
