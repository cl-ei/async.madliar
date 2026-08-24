import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import Header
from fastapi.exceptions import HTTPException
from src.ssg.generator import StaticSiteGenerator
from src.worker import entry


def render_template(template_name: str, context: dict = None) -> str:
    layouts_dir = os.getcwd()  # 入口文件的路径
    env = Environment(
        loader=FileSystemLoader(layouts_dir),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,      # 移除块后的第一个换行
        lstrip_blocks=True,    # 移除块前的空格
    )
    template = env.get_template(template_name)
    context = context or {}
    return template.render(**context)


router = APIRouter()


@router.get("/original-intention")
async def old_blog() -> HTMLResponse:
    html = render_template("src/tpl/original-intention.html")
    return HTMLResponse(html)


@router.get("/ssg")
async def ssg() -> HTMLResponse:
    html = render_template("src/tpl/ssg.html")
    return HTMLResponse(html)


def _appkey_valid(appkey: str | None) -> bool:
    expected = os.getenv("APP_KEY")
    if not expected:
        return True
    return appkey == expected


@router.post("/original-intention/ssg/gen")
async def ssg_gen(appkey: str | None = Header(None)):
    if not _appkey_valid(appkey):
        raise HTTPException(status_code=403, detail="AppKey mismatch")
    flag = entry.create_task("generate")
    return {"code": 0, "msg": "ok", "data": flag}


@router.post("/original-intention/ssg/log")
async def ssg_log(appkey: str | None = Header(None)):
    if not _appkey_valid(appkey):
        raise HTTPException(status_code=403, detail="AppKey mismatch")
    try:
        email = "i@caoliang.net"
        s = StaticSiteGenerator(email)
        await s.load_config()
        logfile = f"{s.write_root}/build.log"
        with open(logfile, "r", encoding="utf-8") as f:
            content = f.read()
        return {"code": 0, "msg": "ok", "data": content}
    except HTTPException:
        raise
    except Exception as e:
        return {"code": 1, "msg": str(e), "data": None}


@router.post("/original-intention/ssg/upload")
async def ssg_upload(appkey: str | None = Header(None)):
    if not _appkey_valid(appkey):
        raise HTTPException(status_code=403, detail="AppKey mismatch")
    flag = entry.create_task("upload")
    return {"code": 0, "msg": "ok", "data": flag}
