import os
import json
import copy
import datetime
import requests
import time
from etc.config import CDN_URL
from app.http import HttpResponse, render_to_response
from etc.log4 import madliar_logger as logging
from model.dao import HansyGiftRecords


class LtOperations(object):
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

    HISTORY_DISPLAY_GIFTS = (
        "王冠小电视", "小电视飞船",
        "幻乐之声", "花之少女", "DokiDoki", "C位光环", "摩天大楼",
        "琴语", "天空之翼",
        "节奏风暴",
    )

    HANSY_GIFT_LIST_FILE = "../stormgift/data/hansy_gift_list.txt"
    HANSY_GUARD_LIST_FILE = "../stormgift/data/hansy_guard_list.txt"

    FACES_DIR = "../statics/static/face"

    @classmethod
    def _download_deficiency_face(cls, uid):
        req_url = f"https://api.bilibili.com/x/space/acc/info?jsonp=jsonp&mid={uid}"
        try:
            r = requests.get(req_url, headers=cls.headers, timeout=10)
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
            filename = f"{cls.FACES_DIR}/{uid}"
            with open(filename, "wb") as f:
                f.write(r.content)
        except Exception as e:
            logging.error(f"Cannot save face, e: {e}, {uid} -> {face}")
            return

        logging.info(f"User face saved, {uid} -> {face}")
        return True

    @classmethod
    async def get_gift_list(cls, req):
        version = f"{datetime.date.today()}-{str(os.path.getmtime(cls.HANSY_GIFT_LIST_FILE))}"
        if version == req.query.get("version"):
            return HttpResponse(json.dumps({"version": version}))

        with open(cls.HANSY_GIFT_LIST_FILE, "r", encoding="utf-8") as f:
            gift_list = f.readlines()

        try:
            existed_uid_list = os.listdir(cls.FACES_DIR)
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
                    face = f"{CDN_URL}/static/face/{uid}"
                else:
                    cost_time = time.time() - download_deficiency_face_start_time
                    if cost_time < 40 and cls._download_deficiency_face(uid) is True:
                        face = f"{CDN_URL}/static/face/{uid}"
                    else:
                        face = f"{CDN_URL}/static/face/default"
                        deficiency_face = True

                gift_img = f"{CDN_URL}/static/gift/{gift_name}"

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
                "face": f"{CDN_URL}/static/face/65568410",
                "gift_name": "不负你的深情",
            })

        packaged_history = []
        for g in history:
            if g["gift_name"] not in cls.HISTORY_DISPLAY_GIFTS:
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
                "face": f"{CDN_URL}/static/face/65568410",
                "gift_name": "不负你的深情",
            }]
        else:
            packaged_history.sort(key=lambda x: (cls.HISTORY_DISPLAY_GIFTS.index(x["gift_name"]), -x["count"]))

        # Do not force update.
        # if deficiency_face:
        #     version += str(random.random())[:10]

        data = {
            "history": packaged_history,
            "today": today,
            "version": version,
        }
        return HttpResponse(json.dumps(data))

    @classmethod
    async def get_page(cls, req):
        bg_color = req.query.get("bg_color")
        today_lines = req.query.get("today_lines", 3)
        demo = int(req.query.get("demo", 0))
        scale = float(req.query.get("scale", 0.65))
        margin_top = int(525 / 2 * (1 - scale))
        margin_left = int(522 / 2 * (1 - scale))

        with open(cls.HANSY_GUARD_LIST_FILE, "rb") as f:
            guard_text = f.read().decode("utf-8")

        gift_dict = {}
        price_dict = {}
        uid_to_uname_map = {}

        gift_list = await HansyGiftRecords.get_log()
        for uid, uname, gift_name, coin_type, price, count, *_ in gift_list:
            uid_to_uname_map[uid] = uname
            price_dict[gift_name] = price

            if gift_name not in gift_dict:
                gift_dict[gift_name] = {}

            if uid in gift_dict[gift_name]:
                gift_dict[gift_name][uid] += count
            else:
                gift_dict[gift_name][uid] = count

        gathered_gift_list = sorted([
            [gift_name, sorted([[uid, count] for uid, count in senders.items()], key=lambda p: p[1], reverse=True)]
            for gift_name, senders in gift_dict.items()
        ], key=lambda x: price_dict[x[0]], reverse=True)

        gift_text = ""
        for gift_name, senders in gathered_gift_list:
            gift_text += f"{gift_name}: <br />"
            gift_text += "".join([
                f"　　{uid_to_uname_map[uid]}: {count}<br />"
                for uid, count in senders
            ])

        context = {
            "today_lines": today_lines,
            "bg_color": bg_color,
            "demo": demo,
            "scale": "%.2f" % scale,
            "margin_top": margin_top,
            "margin_left": margin_left,
            "guard_text": guard_text,
            "gift_text": gift_text,
        }
        return render_to_response("templates/thank_v.html", context=context)

    @classmethod
    async def thank(cls, req):
        get_list = req.query.get("get_gift_list")
        if get_list:
            return await cls.get_gift_list(req)
        else:
            return await cls.get_page(req)
