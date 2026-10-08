import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

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

    blob = json.dumps(
        {"f": src, "t": arrive, "m": main, "x": meta, "ip": request.client.host if request.client else "-"},
        ensure_ascii=True,
    ).replace("<", "\\u003c").replace(">", "\\u003e")

    old = ""
    if os.path.exists("/var/log/sms.html"):
        old = open("/var/log/sms.html", encoding="utf-8").read()
    i = old.find("<!--SMSDATA\n")
    old = old[i + len("<!--SMSDATA\n"):old.find("\n-->", i)] if i >= 0 else ""

    items = []
    for b in ([blob] + [x for x in old.split("\n") if x.strip()])[:300]:
        try:
            items.append(json.loads(b))
        except Exception:
            pass

    css = (
        "*{box-sizing:border-box;margin:0;padding:0}"
        'body{background:#f4f5f7;color:#1f2328;'
        'font:15px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;'
        "padding:26px 16px 64px}"
        ".wrap{max-width:680px;margin:0 auto}"
        "h1{font-size:19px;font-weight:600;letter-spacing:.3px}"
        ".sub{color:#8b949e;font-size:12.5px;margin:5px 0 20px;font-family:ui-monospace,Menlo,monospace}"
        ".card{background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:15px 17px;"
        "margin-bottom:13px;box-shadow:0 1px 2px rgba(16,24,40,.04)}"
        ".card.new{border-color:#c9d6ff;box-shadow:0 0 0 3px rgba(59,76,202,.08)}"
        ".hd{display:flex;align-items:center;gap:10px;margin-bottom:11px}"
        ".from{font:600 16px/1 ui-monospace,Menlo,monospace;background:#eef1ff;color:#3b4cca;"
        "padding:5px 10px;border-radius:7px;white-space:nowrap}"
        ".t{margin-left:auto;color:#98a2b3;font-size:12px;font-family:ui-monospace,Menlo,monospace}"
        ".bd{white-space:pre-wrap;word-break:break-word}"
        ".code{display:inline-block;margin:9px 0 3px;font:700 23px/1 ui-monospace,Menlo,monospace;"
        "letter-spacing:3px;color:#067647;background:#e9f8ef;border:1px dashed #75c79b;"
        "border-radius:9px;padding:9px 16px}"
        ".ft{margin-top:11px;padding-top:9px;border-top:1px dashed #eceff3;color:#a6adb6;"
        "font:12px/1.5 ui-monospace,Menlo,monospace;word-break:break-all}"
        ".empty{background:#fff;border:1px dashed #d6dae0;border-radius:12px;padding:40px;"
        "text-align:center;color:#98a2b3}"
    )

    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    h = [
        '<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="refresh" content="30">',
        "<title>短信 · %d 条</title>" % len(items),
        "<style>%s</style></head><body><div class=wrap>" % css,
        "<h1>短信接收</h1>",
        '<div class="sub">共 %d 条 · 更新于 %s · 30s 自动刷新</div>' % (len(items), now),
        ]

    if not items:
        h.append('<div class="empty">还没有收到短信</div>')
    for n, it in enumerate(items):
        h.append('<div class="card%s">' % (" new" if n == 0 else ""))
        h.append('<div class="hd"><span class="from">%s</span><span class="t">%s</span></div>'
                 % (html.escape(it["f"]), html.escape(it["t"])))
        h.append('<div class="bd">%s</div>' % html.escape("\n".join(it["m"])))
        txt = "\n".join(it["m"])
        if re.search(r"验证码|校验码|动态码|口令|[Cc]ode", txt):
            mm = re.search(r"(?<!\d)(\d{4,8})(?!\d)", txt)
            if mm:
                h.append('<div class="code">%s</div>' % mm.group(1))
        h.append('<div class="ft">%s</div>' % html.escape("  ·  ".join(it["x"] + [it["ip"]])))
        h.append("</div>")

    h.append("</div></body></html>\n<!--SMSDATA\n")
    for it in items:
        h.append(json.dumps(it, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e") + "\n")
    h.append("-->\n")

    with open("/var/log/sms.html", "w", encoding="utf-8") as fh:
        fh.write("".join(h))

    print("SMS %s | %s | %s" % (arrive, src, " / ".join(main)[:120]), flush=True)
    return {"ok": True}


@router.get("/ssg/sms/gamekun")
def sms_page():
    if not os.path.exists("/var/log/sms.html"):
        return HTMLResponse(
            '<meta charset="utf-8"><title>短信</title>'
            '<div style="font:15px/2 -apple-system,sans-serif;text-align:center;'
            'padding:60px;color:#98a2b3">还没有收到短信</div>',
            headers={"Cache-Control": "no-store"},
        )
    return HTMLResponse(
        open("/var/log/sms.html", encoding="utf-8").read(),
        headers={"Cache-Control": "no-store"},
    )
