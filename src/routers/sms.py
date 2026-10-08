import fcntl
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request, Response


router = APIRouter()


@router.post("/ssg/sms/kcaqeavz2rnkyufjs0")
async def sms_receiver(request: Request):
    raw = await request.body()

    src, body, ts = "", "", ""
    if "json" in request.headers.get("content-type", "").lower():
        try:
            j = json.loads(raw)
            src, body, ts = str(j.get("from", "")), str(j.get("content", "")), str(j.get("timestamp", ""))
        except Exception:
            src, body, ts = "", "", ""
    else:
        f = dict(parse_qsl(raw.decode("utf-8", "replace"), keep_blank_values=True))
        src, body, ts = f.get("from", ""), f.get("content", ""), f.get("timestamp", "")

    try:
        arrive = datetime.fromtimestamp(int(ts) / 1000, tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        arrive = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

    lines = body.split("\n")
    if lines and lines[0].strip() == src.strip():
        lines = lines[1:]

    meta, main = [], []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", s):
            continue
        if s.startswith("SIM") or s.startswith("SubId"):
            meta.append(s)
        else:
            main.append(s)

    block = "#SMS#\n" + "=" * 74 + "\n"
    block += f" {arrive}    {src or '-'}\n"
    block += "-" * 74 + "\n"
    for l in main:
        block += f" {l}\n"
    block += "-" * 74 + "\n"
    block += " " + "  ·  ".join(meta + [request.client.host if request.client else "-"]) + "\n"
    block += "=" * 74 + "\n\n"

    with open("/var/log/sms.txt", "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        old = fh.read()
        fh.seek(0)
        fh.truncate()
        fh.write(block + "#SMS#".join(old.split("#SMS#")[:200]))

    print(block.replace("#SMS#", ""), flush=True)
    return {"ok": True}


@router.get("/ssg/sms/gamekun")
def sms_read():
    if not os.path.exists("/var/log/sms.txt"):
        return Response("还没有收到短信\n", media_type="text/plain; charset=utf-8")
    with open("/var/log/sms.txt", "r", encoding="utf-8") as fh:
        txt = fh.read().replace("#SMS#", "")
    return Response(txt, media_type="text/plain; charset=utf-8", headers={"Cache-Control": "no-store"})
