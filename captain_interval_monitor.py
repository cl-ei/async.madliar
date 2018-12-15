import os
import sys
import json
import requests
import time
import redis
import pickle
import logging


if sys.platform in ("darwin", "win32"):
    log_file = "log/captain.log"
    cookie_file = "./cookie.txt"
else:
    log_file = "/home/wwwroot/log/captain.log"
    cookie_file = "/home/wwwroot/notebook.madliar/notebook_user/i@caoliang.net/cookie.txt"

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
    req_url = "https://api.live.bilibili.com/lottery/v1/Lottery/check_guard?roomid=%s" % room_id
    req_data = {"roomid": room_id}
    for _ in range(0, 3):
        try:
            time.sleep(0.2)
            r = requests.get(url=req_url, data=req_data, headers=headers, timeout=5)
            if r.status_code == 200:
                data = json.loads(r.content.decode("utf-8"))
                if data.get("code", 0) == 0:
                    return [int(d["id"]) for d in data.get("data", []) if "id" in d and d["id"]]
        except Exception as e:
            logging.error("Get gift id ERROR: %s, room id: %s" % (e, room_id))
            pass
    return []


def send_request_for_accept_prize(room_id, gift_id):
    req_url = "https://api.live.bilibili.com/lottery/v2/Lottery/join"
    data = {
        "roomid": int(room_id),
        "id": gift_id,
        "type": "guard",
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
        content = json.loads(content.decode("utf-8")).get("data", {}).get("message", "")
        message = "accept_prize, room id: %s -> %s, %s" % (room_id, gift_id, content)
        print(message)
        logging.info(message)
    except Exception as e:
        message = "accept_prize ERROR: %s, room id: %s" % (e, room_id)
        print(message)
        logging.error(message)


def accept_prize(room_id):
    g_id_list = get_gift_id(room_id)
    for gift_id in g_id_list:
        send_request_for_accept_prize(room_id, gift_id)


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
        "c1": room_list[0],
        "c2": room_list[1],
        "c3": room_list[2],
    }
    redis_conn.set("CAPTAIN_INFO", pickle.dumps(new_info))

    logging.info("Found captain list, zongdu: %s, tidu: %s, jianzhang: %s" % (zongdu_list, tidu_list, jianzhang_list))

    total_list = set(zongdu_list + tidu_list + jianzhang_list)
    for room_id in total_list:
        accept_prize(room_id)


if __name__ == "__main__":
    main()
