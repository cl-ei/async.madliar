import json
import os
import logging
import datetime
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import Header, Query, Body
from fastapi.exceptions import HTTPException
from src.worker import entry
from src.config import APP_KEY, IS_PROD, LOG_FILE
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


@router.get("/ssg/")
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


COMMENT_DIR = Path("/var/log/comments")
MAX_FILE_SIZE = 500 * 1024  # 500KB
MIN_ELAPSE_SECONDS = 3


@router.post("/ssg/comment")
async def submit_comment(
    request: Request,
    content: str = Body(""),
    email: str = Body(""),
    bot: str = Body(""),
    ts: float = Body(""),
    url: str = Body(""),
):
    # ---- 1. honeypot 检测 ----
    if bot:
        return {"ok": False, "error": "bot_fill_honeypot"}

    # ---- 2. 填写耗时检测 ----
    # skip, 因为服务端时间和客户端需要同步，这里有较大误差

    # ---- 3. 内容校验 ----
    content = (content or "").strip()
    if not content:
        return {"ok": False, "error": "empty_content"}
    if len(content) > 2000:
        return {"ok": False, "error": "content_too_long"}

    # ---- 4. 邮箱校验（可选） ----
    if email:
        email = email.strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            return {"ok": False, "error": "invalid_email"}
    else:
        email = None

    # ---- 5. 写文件（每天一个） ----
    COMMENT_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.datetime.now().strftime("%Y-%m-%d") + ".jsonl"
    fpath = COMMENT_DIR / fname

    if fpath.exists() and fpath.stat().st_size > MAX_FILE_SIZE:
        return {"ok": False, "error": "storage_full"}

    record = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "ip": request.client.host if request.client else "",
        "ua": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
        "email": email,
        "content": content,
        "url": url,
        "ts": ts,
    }

    with open(fpath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"ok": True}
