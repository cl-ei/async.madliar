import os
import sys
import logging
import pika
import pickle
import datetime
import random
import requests
import json


if sys.platform == "darwin":
    DEBUG = True
    LOG_PATH = "./log/"
else:
    DEBUG = False
    LOG_PATH = "/home/wwwroot/log/"

fh = logging.FileHandler(os.path.join(LOG_PATH, "qqbot.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("qqbot")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


def prize_dispatcher(content):
    detail, url = content.split("\n")
    time_roomid, gtype = detail.split("→")
    room_id = time_roomid.split(" ")[-1]
    msg = {"gtype": gtype, "roomid": room_id}

    connection_param = pika.ConnectionParameters(host='localhost')
    pika_connection = pika.BlockingConnection(connection_param)
    pika_channel = pika_connection.channel()
    pika_channel.queue_declare(queue='prizeinfo')
    pika_channel.basic_publish(exchange='', routing_key='prizeinfo', body=pickle.dumps(msg))

    print("QQBOT: %s -> %s" % (gtype, room_id))
    logging.info("%s: %s -> %s" % (str(datetime.datetime.now()), gtype, room_id))


def robot_dispatcher(bot, contact, member, content):
    bot.SendTo(contact, 'xxx')


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


def onQQMessage(bot, contact, member, content):
    if str(getattr(member, "uin", None)) == "3139399240" and "live.bilibili.com" not in content:
        return prize_dispatcher(content)

    elif contact.nick == "此人已死" or content[0] == "#":
        if contact.nick == "此人已死":
            if random.randint(0, 10) > 3:
                return
        req_m = content[:127]
        response = get_reply(req_m)
        if response:
            bot.SendTo("🤖 " + contact, response)
