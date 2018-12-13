import os
import sys
import logging
import pickle
import datetime
import socket
import random
import requests
import json


if sys.platform == "darwin":
    DEBUG = True
    LOG_PATH = "./log/"
else:
    DEBUG = False
    LOG_PATH = "/home/wwwroot/log/"

fh = logging.FileHandler(os.path.join(LOG_PATH, "qqchat.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
logger = logging.getLogger("qqchat")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
chat_logging = logger


fh = logging.FileHandler(os.path.join(LOG_PATH, "qqbot.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("qqbot")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


def push_prize_info(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(pickle.dumps(msg), ('127.0.0.1', 11111))
        s.close()
    except Exception:
        pass


def prize_dispatcher(content):
    detail, url = content.split("\n")
    time_roomid, gtype = detail.split("→")
    room_id = time_roomid.split(" ")[-1]
    msg = {"gtype": gtype, "roomid": room_id}
    push_prize_info(msg)

    print("QQBOT: %s -> %s" % (gtype, room_id))
    logging.info("%s: %s -> %s" % (str(datetime.datetime.now()), gtype, room_id))


def get_reply(msg):
    req_param = {
        "reqType": 0,
        "perception": {"inputText": {"text": msg}},
        "userInfo": {
            "apiKey": "c83e8c03c71d43b6b0ce271d485896d8",
            "userId": "248138"
        }
    }
    try:
        r = requests.post(url="http://openapi.tuling123.com/openapi/api/v2", json=req_param)
        data = json.loads(r.content.decode("utf-8"))
        response = data.get("results", [])[0].get("values", {}).get("text", "")
    except Exception:
        response = None
    return response


def auto_reply(bot, contact, member, content):
    req_m = content[:127]
    response = get_reply(req_m)
    if response:
        bot.SendTo(contact, "🤖 " + response)


def onQQMessage(bot, contact, member, content):
    if not content:
        return True

    if str(getattr(member, "uin", None)) == "3139399240":
        if "live.bilibili.com" in content:
            return prize_dispatcher(content)
    else:
        contact_name = getattr(contact, "name", "__contact_name")
        member_name = getattr(member, "name", "__member_name")
        member_nick = getattr(member, "nick", "__member_nick")
        msg = "%s [%s __from__ %s] -> %s" % (member_nick, member_name, contact_name, content)
        chat_logging.info(msg)
    return True
    # if contact.nick == "此人已死":
    #     if random.randint(0, 10) < 5:
    #         return auto_reply(bot, contact, member, content)
    # elif content.startswith("$$"):
    #     return auto_reply(bot, contact, member, content.strip("$$"))
