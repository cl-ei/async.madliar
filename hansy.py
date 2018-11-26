import json
import requests
import time


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


if __name__ == "__main__":
    msg_list = [
        "各位小可爱记得点上关注哟，点个关注不迷路 ヽ(✿ﾟ▽ﾟ)ノ",
        "喜欢泡泡的小伙伴，加粉丝QQ群436496941来撩骚呀~",
        "更多好听的原创歌和翻唱作品，网易云音乐搜索「管珩心」~",
    ]
    for msg in msg_list:
        print(send_danmaku(msg, roomid=4424139, color=16738408))
