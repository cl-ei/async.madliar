import os
import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import Header, Query
from fastapi.exceptions import HTTPException
from src.worker import entry
from src.config import APP_KEY, IS_PROD
from src.operations.log_monitor import get_log_streaming_response


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


@router.get("/ssg")
async def ssg() -> HTMLResponse:
    html = render_template("src/tpl/ssg.html")
    return HTMLResponse(html)


@router.post("/ssg/gen")
async def ssg_gen(appkey: str = Header("")):
    if appkey != APP_KEY:
        raise HTTPException(status_code=403, detail="AppKey mismatch")
    flag = entry.create_task("generate")
    return {"code": 0, "msg": "ok", "data": flag}


@router.post("/ssg/upload")
async def ssg_upload(appkey: str | None = Header(None)):
    if appkey != APP_KEY:
        raise HTTPException(status_code=403, detail="AppKey mismatch")

    if IS_PROD:
        flag = entry.create_task("upload")
    else:
        logging.debug("moke upload!")
        flag = "true"

    return {"code": 0, "msg": "ok", "data": flag}


@router.get("/ssg/logs/stream")
def stream_logs(appkey: str | None = Query(None)):
    if appkey != APP_KEY:
        raise HTTPException(status_code=403, detail="AppKey mismatch")
    return get_log_streaming_response()
