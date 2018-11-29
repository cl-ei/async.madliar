import sys
import json
import random
import websocket
import time
import datetime
import os
import logging
import redis
import requests
from threading import Thread
from traceback import format_exc

REDIS_CONFIG = {
    "host": "47.104.176.84",
    "port": 19941,
    "password": "redispassword",
    "db": 8
}
redis_conn = redis.Redis(**REDIS_CONFIG)

ROOM_ID = 2516117
monitor_url = "ws://broadcastlv.chat.bilibili.com:2244/sub"
PACKAGE_HEADER_LENGTH = 16
CONST_MIGIC = 16
CONST_VERSION = 1
CONST_PARAM = 1
CONST_HEART_BEAT = 2
CONST_MESSAGE = 7


if sys.platform == "darwin":
    LOG_PATH = "./log/"
else:
    LOG_PATH = "/home/wwwroot/log/hansy/"

fh = logging.FileHandler(os.path.join(LOG_PATH, "prize.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("prize")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
p_logging = logger

fh = logging.FileHandler(os.path.join(LOG_PATH, "chat.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("chat")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
c_logging = logger

fh = logging.FileHandler(os.path.join(LOG_PATH, "gold.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("gold")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
g_logging = logger

fh = logging.FileHandler(os.path.join(LOG_PATH, "mix.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("mix")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


if sys.platform == "darwin":
    cookie_file = "cookie.txt"
else:
    cookie_file = "/home/wwwroot/notebook.madliar/notebook_user/i@caoliang.net/cookie.txt"

with open(cookie_file) as f:
    cookie = f.read().strip()
csrf_token = ""
for kv in cookie.split(";"):
    if "bili_jct" in kv:
        csrf_token = kv.split("=")[-1].strip()
        break
headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Cookie": cookie,
}


def send_danmaku(msg, roomid=ROOM_ID, color=0xffffff):
    data = {
        "color": color,
        "fontsize": 25,
        "mode": 1,
        "msg": msg,
        "rnd": int(time.time()),
        "roomid": roomid,
        "csrf_token": csrf_token,
    }
    r = requests.post(url="https://live.bilibili.com/msg/send", data=data, headers=headers)
    try:
        response = json.loads(r.content.decode("utf-8"))
        if response.get("code") == 0:
            return True
        c_logging.error("SEND_DANMAKU ERROR: req: %s, response: %s" % (data, r.content))
    except Exception as e:
        c_logging.error("SEND_DANMAKU ERROR: %s, data: %s" % (e, data))


def parse_danmaku(msg):
    cmd = msg.get("cmd")
    datetime_str = str(datetime.datetime.now())
    if cmd == "DANMU_MSG":
        content = msg.get("info", "")
        raw_msg = content[1]
        user = content[2][1]
        ul = content[4][0]
        try:
            decoration = content[3][1]
            dl = content[3][0]
        except Exception:
            decoration = ""
            dl = ""

        msg = '[{}] [UL {: >2}] [{:　<4}{: >2}] {} -> {}'.format(datetime_str, ul, decoration, dl, user, raw_msg)
        c_logging.info(msg)
        logging.info(msg)
        print(msg)
        if user in ("蓝屏一天掰个头", "偷闲一天打个盹"):
            return

        redis_conn.set("HANSY_TIME", int(time.time()))
        raw_msg = raw_msg.strip()
        if "好听" in raw_msg:
            if random.randint(0, 10) > 3:
                return
            danmaku_msg = random.choice([
                "φ(≧ω≦*)♪好听好听！ 打call ᕕ( ᐛ )ᕗ",
                "好听！给跪了! ○|￣|_ (这么好听还不摁个关注？！",
                "好听! 我的大仙泡最美最萌最好听 ´･∀･)乂(･∀･｀",
            ])
            send_danmaku(danmaku_msg)
        elif "晚上好" in raw_msg:
            send_danmaku("%s 小可爱晚上好鸭(*ﾟ∀ ﾟ)" % user)
        elif "挥挥" in raw_msg or "灰灰" in raw_msg:
            send_danmaku("( σ'ω')σ %s 小可爱挥挥~ (情敌-1 " % user[:10])
        elif raw_msg.replace("#", "").replace("＃", "").replace(" ", "").replace("　", "").startswith("点歌"):
            if decoration != "电磁泡":
                send_danmaku("%s：点歌失败...要佩戴「电磁泡」勋章才能点歌成功哦o( =•ω•= )m ~" % user)
                time.sleep(1)
                send_danmaku("获取「电磁泡」勋章：赠送1个B坷垃，或充电50电池，或给up的投稿累计投20币~")

    elif cmd == "SEND_GIFT":
        data = msg.get("data")
        uid = data.get("uid", "        ")
        user = data.get("uname", "")
        gift_name = data.get("giftName", "")
        gift_type = data.get("coin_type", "")
        count = data.get("num", "")
        message = "[{}] [{: ^14}][{}] -> [{}][{}] * [{}]".format(datetime_str, uid, user, gift_name, gift_type, count)
        p_logging.info(message)
        logging.info(message)
        if gift_type == "gold":
            g_logging.info(message)
            print(message)

    elif cmd == "COMBO_END":
        data = msg.get("data")
        uid = "       "
        user = data.get("uname", "")
        gift_name = data.get("gift_name", "")
        gift_type = ""
        count = data.get("combo_num", "")
        msg = "[{}] [{: ^14}][{}] -> [{}][{}] * [{}]".format(datetime_str, uid, user, gift_name, gift_type, count)
        print(msg)
        p_logging.info(msg)
        logging.info(msg)
        if gift_type == "gold":
            g_logging.info(msg)


def on_message(ws_obj, message):
    while message:
        length = (message[0] << 24) + (message[1] << 16) + (message[2] << 8) + message[3]
        current_msg = message[:length]
        message = message[length:]
        if len(current_msg) > 16 and current_msg[16] != 0:
            try:
                msg = current_msg[16:].decode("utf-8", errors="ignore")
                msg = json.loads(msg)
                parse_danmaku(msg)
            except Exception as e:
                print("e: %s, m: %s" % (e, current_msg))
                c_logging.error(format_exc())


def on_error(ws_obj, error):
    print(error)
    raise RuntimeError("WS Error!")


def on_close(ws_obj):
    raise RuntimeError("WS Closed!")


def on_open(ws_obj):
    print("ws opened: %s" % ws_obj)
    send_join_room(ws_obj)


def send_heart_beat(ws_obj):
    hb = generate_packet(CONST_HEART_BEAT)
    while True:
        time.sleep(10)
        ws_obj.send(hb)


def send_join_room(ws_obj, uid=None):
    roomid = ROOM_ID
    if not uid:
        from random import random
        from math import floor
        uid = int(1E15 + floor(2E15 * random()))

    package = '{"uid":%s,"roomid":%s}' % (uid, roomid)
    binmsg = generate_packet(CONST_MESSAGE, package)
    ws_obj.send(binmsg)
    t = Thread(target=send_heart_beat, args=(ws_obj, ))
    t.start()


def generate_packet(action, payload=""):
    payload = payload.encode("utf-8")
    packet_length = len(payload) + PACKAGE_HEADER_LENGTH
    buff = bytearray(PACKAGE_HEADER_LENGTH)

    # package length
    buff[0] = (packet_length >> 24) & 0xFF
    buff[1] = (packet_length >> 16) & 0xFF
    buff[2] = (packet_length >> 8) & 0xFF
    buff[3] = packet_length & 0xFF

    # migic & version
    buff[4] = 0
    buff[5] = 16
    buff[6] = 0
    buff[7] = 1

    # action
    buff[8] = 0
    buff[9] = 0
    buff[10] = 0
    buff[11] = action

    # migic parma
    buff[12] = 0
    buff[13] = 0
    buff[14] = 0
    buff[15] = 1

    return buff + payload


if __name__ == "__main__":
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        url=monitor_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()
