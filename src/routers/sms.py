import json
from fastapi import APIRouter, Request


router = APIRouter()


@router.post("/sms/kcaqeavz2rnkyufjs0")
async def sms_receiver(request: Request):
    print("=" * 70)
    print(">> 来源 IP:", request.client.host if request.client else None)
    print(">> 代理链 X-Forwarded-For:", request.headers.get("x-forwarded-for"))
    print(">> 完整 URL:", request.url)
    print(">> URL 参数:", dict(request.query_params))
    print(">> METHOD:", request.method)
    print(">> HEADERS:")
    for k, v in request.headers.items():
        print(f"   {k}: {v}")
    print("-" * 70)

    raw = await request.body()
    print(">> RAW BYTES:", raw)

    if "application/json" in request.headers.get("content-type", "").lower():
        try:
            print(">> JSON:", json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
        except Exception as e:
            print(">> JSON 解析失败:", e)
            print(">> 原始文本:", raw.decode("utf-8", "replace"))
    else:
        print(">> 非 JSON，原始文本:", raw.decode("utf-8", "replace"))

    print("=" * 70, flush=True)
    return {"ok": True}
