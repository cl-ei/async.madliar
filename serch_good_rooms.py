import sys
import pickle
import json
import time
import datetime
import os
import logging
import redis
import requests
from traceback import format_exc


DEBUG = sys.argv[-1] != "server"

LOG_PATH = "./log/" if DEBUG else "/home/wwwroot/log/"
fh = logging.FileHandler(os.path.join(LOG_PATH, "search_good_rooms.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
logger = logging.getLogger("search_good_rooms")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger

scan_url = "https://api.live.bilibili.com/room/v1/Area/getListByAreaID?areaId=0&sort=online&pageSize=500&page="
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
headers = {'User-Agent': UA}


class Cache(object):
    REDIS_CONFIG = {"host": "47.104.176.84", "port": 19941, "password": "redispassword", "db": 0 if DEBUG else 4}
    __r = redis.Redis(**REDIS_CONFIG)

    __ROOM_KEY = "AN_%s"  # room_id

    @classmethod
    def get_room_info(cls, room_id):
        k = cls.__ROOM_KEY % room_id
        try:
            s = pickle.loads(cls.__r.get(k) or "")
        except Exception:
            s = {}
        return s

    @classmethod
    def save_room_info(cls, room_id, info):
        if not isinstance(info, dict):
            return False
        k = cls.__ROOM_KEY % room_id
        try:
            r = cls.__r.set(k, pickle.dumps(info))
        except Exception:
            r = False
        return r


def get_online_rooms(page_limit=20):
    req_url = "https://api.live.bilibili.com/room/v1/Area/getListByAreaID?areaId=0&sort=online&pageSize=500&page="

    for page in range(0, page_limit):
        url = req_url + str(page)
        try:
            r = requests.get(url=url, headers=headers, timeout=10)
            info = json.loads(r.content.decode("utf-8"))
            data = info.get("data", []) or []
            if not data:
                continue
        except Exception:
            continue

        for d in data:
            try:
                room_id = int(d["roomid"])
                online = int(d["online"])
                info = Cache.get_room_info(room_id)
                info.setdefault("o", []).append(online)
                if len(info["o"]) > 4:
                    info["o"] = sorted(info["o"], reverse=True)[:4]
                Cache.save_room_info(room_id, info)
                print("room id: %s, info: %s" % (room_id, json.dumps(info)))
            except Exception:
                pass
        time.sleep(1)

    #
    # content = getattr(r, "content", b"")
    # try:
    #     code = json.loads(content.decode("utf-8")).get("code", -1)
    #     message = "\taccept_prize, room id: %s -> %s, code: %s" % (room_id, gift_id, code)
    #     print(message)
    #     tv_logging.info(message)
    # except Exception as e:
    #     message = "\taccept_prize ERROR: %s, room id: %s" % (e, room_id)
    #     print(message)
    #     tv_logging.error(message)


if __name__ == "__main__":
    # print(Cache.get_room_info(123))
    # print(Cache.save_room_info(123, {"a": 123}))
    # print(Cache.get_room_info(123))
    get_online_rooms(page_limit=1)
