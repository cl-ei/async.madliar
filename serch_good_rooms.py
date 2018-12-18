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
    __QUERIED_LIST = "QUERIED_LIST"

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

    @classmethod
    def get_if_its_queried_room(cls, room_id):
        try:
            room_list = pickle.loads(cls.__r.get(cls.__QUERIED_LIST))
        except Exception:
            room_list = []
        return int(room_id) in room_list

    @classmethod
    def _set_queried_room(cls, room_id):
        try:
            room_list = pickle.loads(cls.__r.get(cls.__QUERIED_LIST))
        except Exception:
            room_list = []
        room_list.append(int(room_id))
        return cls.__r.set(cls.__QUERIED_LIST, pickle.dumps(room_list))

    @classmethod
    def get_queried_room_list(cls):
        try:
            room_list = pickle.loads(cls.__r.get(cls.__QUERIED_LIST))
        except Exception:
            room_list = []
        return room_list


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


def search_detail_info():
    pass


if __name__ == "__main__":
    # while True:
    #     time.sleep(60*10)
    #     get_online_rooms(page_limit=1)
    print(Cache.get_if_its_queried_room(123))
    print(Cache._set_quired_room(123))
    print(Cache.get_if_its_queried_room(123))
