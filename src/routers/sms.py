import json
from datetime import datetime
from urllib.parse import parse_qsl
from fastapi import APIRouter, Request


router = APIRouter()


@router.post("/ssg/sms/kcaqeavz2rnkyufjs0")
async def sms_receiver(request: Request):
    raw = await request.body()
    print()
    print("=" * 80)
    print(" SMS 上报 |", request.client.host if request.client else "-")
    print("-" * 80)
    print(" URL     :", request.url)
    print(" QUERY   :", dict(request.query_params) or "-")
    print(" HEADERS :")
    for k, v in request.headers.items():
        print(f"            {k:<22} {v}")
    print("-" * 80)

    ct = request.headers.get("content-type", "").lower()

    if "json" in ct:
        print(" BODY    : JSON")
        try:
            print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
        except Exception as e:
            print("           解析失败:", e)
            print("           原始:", raw.decode("utf-8", "replace"))

    elif "x-www-form-urlencoded" in ct:
        print(" BODY    : form-urlencoded")
        for k, v in parse_qsl(raw.decode("utf-8", "replace"), keep_blank_values=True):
            if k == "content":
                print(f"           {k:<10}:")
                for line in v.split("\n"):
                    print(f"                | {line}")
            elif k == "timestamp":
                try:
                    t = datetime.fromtimestamp(int(v) / 1000).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    t = "-"
                print(f"           {k:<10}: {v}  ({t})")
            else:
                print(f"           {k:<10}: {v}")

    else:
        print(" BODY    : 其他 (%s)" % (ct or "无 content-type"))
        print("           RAW:", raw.decode("utf-8", "replace"))

    print("=" * 80, flush=True)
    return {"ok": True}
