import os
import sys
import json
import requests
import time
import socket
import redis
import pickle
import logging

if sys.platform in ("darwin", "win32"):
    log_file = "log/captain.log"
else:
    log_file = "/home/wwwroot/log/captain.log"

fh = logging.FileHandler(log_file)
log_format = '%(asctime)s: %(message)s'
fh.setFormatter(logging.Formatter(log_format))
logger = logging.getLogger("captain")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


REDIS_CONFIG = {
    "host": "47.104.176.84",
    "port": 19941,
    "password": "redispassword",
    "db": 10
}


def parse_roomid(s):
    room_list = []
    while True:
        if "href=\"https://live.bilibili.com/" not in s:
            return room_list
        info = s.split("href=\"https://live.bilibili.com/", 1)[-1]
        room_id, s = info.split("\"", 1)
        room_list.append(room_id)


def get_captain_list():
    url = "https://bili.exinterfaces.com:2234/Governors/View"
    r = requests.get(url)
    string_content = r.content.decode("utf-8").split("<h2>总督列表:</h2>", 1)[-1]
    zongdu, other = string_content.split("<h2>提督列表:</h2>", 1)
    tidu, jianzhang = other.split("<h2>舰长列表:</h2>", 1)
    return list(map(parse_roomid, [zongdu, tidu, jianzhang]))


def compare(old_list, new_list):
    old_list = [str(o) for o in old_list]
    new_list = [str(o) for o in new_list]
    new_list_string = "_".join(new_list)

    for i in range(0, len(old_list)):
        old_str = "_".join(old_list[i:])
        if new_list_string.startswith(old_str):
            new_list = new_list_string[len(old_str):].split("_")
            return [x for x in new_list if x]
    return new_list


def push_prize_info(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(pickle.dumps(msg), ('127.0.0.1', 11111))
        s.close()
    except Exception:
        pass



def main():
    room_list = get_captain_list()

    redis_conn = redis.Redis(**REDIS_CONFIG)
    try:
        captain_info = pickle.loads(redis_conn.get("CAPTAIN_INFO"))
    except Exception:
        captain_info = {}

    old_cap_1 = captain_info.get("c1", [])
    old_cap_2 = captain_info.get("c2", [])
    old_cap_3 = captain_info.get("c3", [])

    zongdu_list = compare(old_cap_1, room_list[0])
    tidu_list = compare(old_cap_2, room_list[1])
    jianzhang_list = compare(old_cap_3, room_list[2])

    new_info = {
        "c1": zongdu_list,
        "c2": tidu_list,
        "c3": jianzhang_list,
    }
    redis_conn.set("CAPTAIN_INFO", pickle.dumps(new_info))

    logging.info("Found captain list, zongdu: %s, tidu: %s, jianzhang: %s" % (zongdu_list, tidu_list, jianzhang_list))

    for z in zongdu_list:
        push_prize_info({"gtype": "总督", "roomid": int(z)})
    for z in tidu_list:
        push_prize_info({"gtype": "提督", "roomid": int(z)})
    for z in jianzhang_list:
        push_prize_info({"gtype": "舰长", "roomid": int(z)})


if __name__ == "__main__":
    main()
