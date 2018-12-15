import json
import socket
import requests
import websocket
import time
import datetime
import os
import sys
import logging
import pickle
from threading import Thread

ROOM_ID = 357983
monitor_url = "ws://broadcastlv.chat.bilibili.com:2244/sub"
PACKAGE_HEADER_LENGTH = 16
CONST_MIGIC = 16
CONST_VERSION = 1
CONST_PARAM = 1
CONST_HEART_BEAT = 2
CONST_MESSAGE = 7

if sys.platform in ("darwin", "win32"):
    LOG_PATH = "./log/"
    cookie_file = "./cookie.txt"
else:
    LOG_PATH = "/home/wwwroot/log/"
    cookie_file = "/home/wwwroot/notebook.madliar/notebook_user/i@caoliang.net/cookie.txt"

fh = logging.FileHandler(os.path.join(LOG_PATH, "tv_accepter.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("tv_accepter")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
tv_logging = logger


fh = logging.FileHandler(os.path.join(LOG_PATH, "self_monotor.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("self_monotor")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


with open(cookie_file) as f:
    cookie = f.read().strip()
csrf_token = ""
for kv in cookie.split(";"):
    if "bili_jct" in kv:
        csrf_token = kv.split("=")[-1].strip()
        break
if not csrf_token:
    logging.error("Error csrf token!")
    sys.exit(0)
headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Cookie": cookie,
}


def get_gift_id(room_id):
    req_url = "https://api.live.bilibili.com/gift/v3/smalltv/check?roomid=%s" % room_id
    req_data = {"roomid": room_id}
    for _ in range(0, 3):
        try:
            time.sleep(0.2)
            r = requests.get(url=req_url, data=req_data, headers=headers, timeout=5)
            if r.status_code == 200:
                data = json.loads(r.content.decode("utf-8"))
                if data.get("code", 0) == 0:
                    return [(int(d["raffleId"]), d["title"]) for d in data.get("data", {}).get("list", []) if "raffleId" in d and d["raffleId"]]
        except Exception as e:
            tv_logging.error("Get gift id ERROR: %s, room id: %s" % (e, room_id))
            pass
    return []


def send_request_for_accept_prize(room_id, gift_id):
    req_url = "https://api.live.bilibili.com/gift/v3/smalltv/join"

    data = {
        "roomid": room_id,
        "raffleId": gift_id,
        "type": "Gift",
        "csrf_token": csrf_token,
        "csrf": csrf_token,
        "visit_id": "",
    }
    r = None
    for _ in range(3):
        time.sleep(0.2)
        r = requests.post(url=req_url, data=data, headers=headers)
        if r.status_code == 200:
            break
    content = getattr(r, "content", b"")
    try:
        code = json.loads(content.decode("utf-8")).get("code", -1)
        message = "\taccept_prize, room id: %s -> %s, code: %s" % (room_id, gift_id, code)
        print(message)
        tv_logging.info(message)
    except Exception as e:
        message = "\taccept_prize ERROR: %s, room id: %s" % (e, room_id)
        print(message)
        tv_logging.error(message)


def accept_prize(room_id):
    g_id_list = get_gift_id(room_id)
    msg = "Found prize room: %s, gift id: %s" % (room_id, g_id_list)
    tv_logging.info(msg)
    print(msg)
    for gift_id, _ in g_id_list:
        send_request_for_accept_prize(room_id, gift_id)


def parse_danmaku(msg):
    cmd = msg.get("cmd")
    if cmd == "NOTICE_MSG":
        message_type = msg.get("msg_type")
        if message_type in (2, 3):
            room_id = msg.get("roomid")
            message = msg.get("msg_self", "")
            real_roomid = msg.get("real_roomid", "")

            datetime_str = str(datetime.datetime.now())
            msg = "[{}] [{}] [{}][{}]".format(datetime_str, message_type, room_id, message)
            print(msg)
            logging.info(msg)
            accept_prize(real_roomid)


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
