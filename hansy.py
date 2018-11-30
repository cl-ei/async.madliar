import os
import sys
import json
import requests
import time
import redis
import logging

if sys.platform == "darwin":
    log_file = "log/hansy_b.log"
else:
    log_file = "/home/wwwroot/log/hansy_b.log"

fh = logging.FileHandler(log_file)
log_format = '%(asctime)s: %(message)s'
fh.setFormatter(logging.Formatter(log_format))
logger = logging.getLogger("b_loger")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


REDIS_CONFIG = {
    "host": "47.104.176.84",
    "port": 19941,
    "password": "redispassword",
    "db": 8
}


def send_danmaku(msg, roomid=4424139, color=0xffffff):
    with open("/home/wwwroot/notebook.madliar/notebook_user/i@caoliang.net/cookie.txt") as f:
        cookie = f.read().strip()
    csrf_token = ""
    for kv in cookie.split(";"):
        if "bili_jct" in kv:
            csrf_token = kv.split("=")[-1].strip()
            break
    if not csrf_token:
        return False

    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie,
    }
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
    time.sleep(1)
    return not (r.status_code != 200 or json.loads(r.content.decode("utf-8")).get("code") != 0)


msg_list = [
    "📢 各位小可爱记得点上关注哟，点个关注不迷路 ヽ(✿ﾟ▽ﾟ)ノ",
    "📢 喜欢泡泡的小伙伴，加粉丝QQ群436496941来撩骚呀~",
    "📢 更多好听的原创歌和翻唱作品，网易云音乐搜索「管珩心」~",
    "📢 泡泡的海盗船舰队正在招聘船长~加入舰队即可领取感恩福利(✿≖ ◡ ≖)✧",
    "📢 获取「电磁泡」勋章：赠送1个B坷垃，或充电50电池，或给up的投稿投币20~",
    "📢 一定要记得网易云关注「管珩心」哦，超百首高质量单曲，小珩心捧着奶茶等你来听~",
]


def main():
    r = redis.Redis(**REDIS_CONFIG)
    try:
        time_sec = int(r.get("HANSY_TIME"))
        index = int(r.get("HANSY_INDEX"))
    except Exception as e:
        logging.error("Exception: %s" % e)
        print("Exception: %s" % e)
        return

    if int(time.time()) - time_sec > 121*len(msg_list):
        logging.error("Timeout, %s sec." % (int(time.time() - time_sec)))
        print("Timeout.")
        return

    index += 1
    index = index % len(msg_list)
    r.set("HANSY_INDEX", index)

    r = send_danmaku(msg_list[index], roomid=2516117)
    print("Result: %s" % r)
    if not r:
        logging.error("Execute error!")


if __name__ == "__main__":
    main()
