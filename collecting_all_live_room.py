import redis
import requests
import json


REDIS_CONFIG = {
    "host": "47.104.176.84",
    "port": 19941,
    "password": "redispassword",
    "db": 10
}
redis_conn = redis.Redis(**REDIS_CONFIG)
req_url = "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid="
headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)",
}


def main():
    for roomid in range(10000, 99999999):
        query_url = req_url + str(roomid)
        try:
            r = requests.get(url=query_url, headers=headers)
            content = r.content.decode("utf-8")
            r_dict = json.loads(content)

            uinfo = r_dict.get("data", {}).get("info", {})
            uid = uinfo.get("uid", "")
            uname = uinfo.get("uname", "")
            master_level = r_dict.get("data", {}).get("level", {}).get("master_level", {}).get("level", 0)

            key = "SUCC:%s:%s:%s:%s" % (roomid, uid, uname, master_level)
            print(key)
            # redis_conn.set("SUCC_", 1)
        except Exception:
            key = "FAILED:%s" % roomid
            print(key)
            # redis_conn.set("FAILED", 0)


if __name__ == "__main__":
    main()
