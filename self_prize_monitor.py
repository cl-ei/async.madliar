import json
import websocket
import time
import datetime
import os
import logging
import pika
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

LOG_PATH = "/home/wwwroot/log/"

fh = logging.FileHandler(os.path.join(LOG_PATH, "self_monotor.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("self_monotor")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


# pika
connection_param = pika.ConnectionParameters(host='localhost')
pika_connection = pika.BlockingConnection(connection_param)
pika_channel = pika_connection.channel()
pika_channel.queue_declare(queue='prizeinfo')


def push_prize_info(msg):
    pika_channel.basic_publish(exchange='', routing_key='danmaku', body=pickle.dumps(msg))


# when tears down
# pika_connection.close()


def parse_danmaku(msg):
    cmd = msg.get("cmd")
    if cmd == "NOTICE_MSG":
        message_type = msg.get("msg_type")
        if message_type in (2, 3):
            room_id = msg.get("roomid")
            message = msg.get("msg_self", "")
            datetime_str = str(datetime.datetime.now())
            msg = "[{}] [{}] [{}][{}]".format(datetime_str, message_type, room_id, message)
            print(msg)
            logging.info(msg)

            msg = {"gtype": "unkown-%s" % message, "roomid": room_id}
            pika_channel.basic_publish(exchange='', routing_key='prizeinfo', body=pickle.dumps(msg))


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
