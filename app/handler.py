import os
import sys
import json
import copy
import datetime
import asyncio
import random
import requests
import time
from app.http import HttpResponse, render_to_response
from etc import (
    DIST_ARTICLE_PATH,
    CDN_URL,
    MUSIC_FOLDER,
    DEBUG,
)
from etc.log4 import logging


async def robots_response(request):
    response = HttpResponse(
        content=(
            "User-agent:  *\n"
            "Disallow:  /static/\n"
        ),
        content_type="text/plain",
        charset="utf-8"
    )
    return response


async def record_response(request):
    return HttpResponse("")


async def delay_response(request):
    delay = int(request.query.get("delay", 0))
    await asyncio.sleep(delay)
    if request.query.get("json"):
        return HttpResponse('{"code": 0, "msg": "OK"}')
    else:
        return HttpResponse('response "ok!"')


async def game_response(request):
    return render_to_response("templates/game.html")


async def index(request):
    article_js_file_name = ""
    for f in os.listdir(DIST_ARTICLE_PATH):
        if f.lower().endswith(".js"):
            article_js_file_name = f
            break
    if DEBUG:
        article_js_link = os.path.join(DIST_ARTICLE_PATH, article_js_file_name)
    else:
        article_js_link = CDN_URL + "/dist_article/" + article_js_file_name
    context = {
        "article_js_link": article_js_link,
        "page": {
            "author": "CL",
            "description": u"CL，编程爱好者，这是CL的官方博客，记录生活感悟和学习点滴。",
            "keywords": u"MADLIAR, CL, CL's 疯言疯语, 疯言疯语, 风言风语, CL博客",
        },
        "CDN_URL": CDN_URL,
    }
    return render_to_response(
        "templates/index.html",
        context=context
    )


async def thank(req):
    get_list = req.query.get("get_gift_list")
    if get_list:
        return await get_gift_list(req)

    bg_color = req.query.get("bg_color")
    today_lines = req.query.get("today_lines", 3)
    demo = int(req.query.get("demo", 0))
    scale = float(req.query.get("scale", 0.65))
    margin_top = int(525 / 2 * (1 - scale))
    margin_left = int(522 / 2 * (1 - scale))

    with open("../stormgift/data/guard_list.txt", "rb") as f:
        guard_text = f.read().decode("utf-8")

    context = {
        "today_lines": today_lines,
        "bg_color": bg_color,
        "demo": demo,
        "scale": "%.2f" % scale,
        "margin_top": margin_top,
        "margin_left": margin_left,
        "guard_text": guard_text,
    }
    return render_to_response("templates/thank_v.html", context=context)


def _download_deficiency_face(uid):
    req_url = f"https://api.bilibili.com/x/space/acc/info?jsonp=jsonp&mid={uid}"
    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,image/apng,*/*;q=0.8"
        ),
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/70.0.3538.110 Safari/537.36"
        ),
    }
    try:
        r = requests.get(req_url, headers=headers, timeout=10)
        face = json.loads(r.text).get("data", {}).get("face", "") or ""
        if not face:
            raise RuntimeError("Bad face url")
    except Exception as e:
        logging.error(f"Cannot get user face, uid -> {uid}, e: {e}")
        return

    try:
        r = requests.get(face, timeout=30)
        if r.status_code != 200:
            raise Exception("Request error when get face!")
        if "linux" in sys.platform:
            filename = f"/home/wwwroot/statics/static/face/{uid}"
        else:
            filename = f"./temp_data/{uid}"
        with open(filename, "wb") as f:
            f.write(r.content)
    except Exception as e:
        logging.error(f"Cannot save face, e: {e}, {uid} -> {face}")
        return

    logging.info(f"User face saved, {uid} -> {face}")
    return True


HISTORY_DISPLAY_GIFTS = (
    "王冠小电视", "小电视飞船",
    "幻乐之声", "花之少女", "DokiDoki", "C位光环", "摩天大楼",
    "琴语", "天空之翼",
    "节奏风暴",
)


async def get_gift_list(req):
    file_name = "../stormgift/data/gift_list.txt"
    version = f"{datetime.date.today()}-{str(os.path.getmtime(file_name))}"
    if version == req.query.get("version"):
        return HttpResponse(json.dumps({"version": version}))

    with open(file_name, "r", encoding="utf-8") as f:
        gift_list = f.readlines()

    try:
        existed_uid_list = os.listdir("/home/wwwroot/statics/static/face")
    except Exception:
        existed_uid_list = []

    history = []
    today = []
    today_str = f"{datetime.date.today()}"
    deficiency_face = False
    download_deficiency_face_start_time = time.time()
    for line in gift_list:
        try:
            data = json.loads(line)
            created_time = data["created_time"]

            uid = data["uid"]
            sender = data["sender"]
            gift_name = data["gift_name"]
            count = data["count"]
            if str(uid) in existed_uid_list:
                face = f"https://statics.madliar.com/static/face/{uid}"
            else:
                cost_time = time.time() - download_deficiency_face_start_time
                if cost_time < 40 and _download_deficiency_face(uid) is True:
                    face = f"https://statics.madliar.com/static/face/{uid}"
                else:
                    face = f"https://statics.madliar.com/static/face/default"
                    deficiency_face = True

            gift_img = f"https://statics.madliar.com/static/gift/{data['gift_name']}"

            if created_time[:10] == today_str:
                today.append({
                    "sender": sender,
                    "face": face,
                    "count": count,
                    "send_text": "赠送",
                    "gift_name": gift_name,
                    "gift_img": gift_img,
                })
            elif created_time[:7] == today_str[:7]:
                history.append({
                    "sender": sender,
                    "face": face,
                    "count": count,
                    "send_text": "赠送",
                    "gift_name": gift_name,
                    "gift_img": gift_img,
                })
        except Exception as e:
            pass

    if not today:
        today.append({
            "sender": "管珩心",
            "face": "https://statics.madliar.com/static/face/65568410",
            "gift_name": "不负你的深情",
        })

    packaged_history = []
    for g in history:
        if g["gift_name"] not in HISTORY_DISPLAY_GIFTS:
            continue

        for d in packaged_history:
            if d["sender"] == g["sender"] and d["gift_name"] == g["gift_name"]:
                d["count"] += g["count"]
                break
        else:
            packaged_history.append(copy.deepcopy(g))

    if not packaged_history:
        packaged_history = [{
            "sender": "管珩心",
            "face": "https://statics.madliar.com/static/face/65568410",
            "gift_name": "不负你的深情",
        }]
    else:
        packaged_history.sort(key=lambda x: (HISTORY_DISPLAY_GIFTS.index(x["gift_name"]), -x["count"]))

    if deficiency_face:
        version += str(random.random())[:10]
    data = {
        "history": packaged_history,
        "today": today,
        "version": version,
    }
    return HttpResponse(json.dumps(data))


async def music_response(request):
    if request.query.get("ref"):
        if not os.path.exists(MUSIC_FOLDER):
            os.mkdir(MUSIC_FOLDER)

        view_data = {
            "ref": True,
            "music_list": json.dumps(os.listdir(MUSIC_FOLDER), ensure_ascii=False)
        }
    else:
        view_data = {"ref": False}

    view_data["CDN_URL"] = CDN_URL
    return render_to_response(
        "templates/music/index.html",
        context=view_data
    )
