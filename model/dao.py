import time
import json
import pickle
import aioredis
import datetime
from etc.config import REDIS_CONFIG


class GiftRedisCache(object):
    def __init__(self, host, port, db, password):
        self.uri = f'redis://{host}:{port}'
        self.db = db
        self.password = password
        self.__redis_conn = None

    async def non_repeated_save(self, key, info, ex=3600*24*7):
        """

        :param key:
        :param info:
        :param ex:
        :return: True
        """
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        return await self.__redis_conn.execute("set", key, json.dumps(info), "ex", ex, "nx")

    async def set(self, key, value, timeout=0):
        v = pickle.dumps(value)
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        if timeout > 0:
            return await self.__redis_conn.execute("setex", key, timeout, v)
        else:
            return await self.__redis_conn.execute("set", key, v)

    async def ttl(self, key):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        return await self.__redis_conn.execute("ttl", key)

    async def get(self, key):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        r = await self.__redis_conn.execute("get", key)
        try:
            return pickle.loads(r)
        except TypeError:
            return None

    async def hash_map_set(self, name, key_values):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        args = []
        for key, value in key_values.items():
            args.append(pickle.dumps(key))
            args.append(pickle.dumps(value))
        return await self.__redis_conn.execute("hmset", name, *args)

    async def hash_map_get(self, name, *keys):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )

        if keys:
            r = await self.__redis_conn.execute("hmget", name, *[pickle.dumps(k) for k in keys])
            if not isinstance(r, list) or len(r) != len(keys):
                raise Exception(f"Redis hash map read error! r: {r}")

            result = [pickle.loads(_) for _ in r]
            return result[0] if len(result) == 1 else result

        else:
            """HDEL key field1 [field2] """
            r = await self.__redis_conn.execute("hgetall", name)
            if not isinstance(r, list):
                raise Exception(f"Redis hash map read error! r: {r}")

            result = {}
            key_temp = None
            for index in range(len(r)):
                if index & 1:
                    result[pickle.loads(key_temp)] = pickle.loads(r[index])
                else:
                    key_temp = r[index]
            return result

    async def list_push(self, name, *items):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )

        r = await self.__redis_conn.execute("LPUSH", name, *[pickle.dumps(e) for e in items])
        return r

    async def list_get_all(self, name):
        if self.__redis_conn is None:
            self.__redis_conn = await aioredis.create_connection(
                address=self.uri, db=self.db, password=self.password
            )
        # count = await self.__redis_conn.execute("LLEN", name)

        r = await self.__redis_conn.execute("LRANGE", name, 0, 100000)
        if isinstance(r, list):
            return [pickle.loads(e) for e in r]
        return []


redis_cache = GiftRedisCache(**REDIS_CONFIG)


class HansyGiftRecords(object):
    gift_key = "HANSY_GIFT_{year}_{month}"

    @classmethod
    async def add_log(cls, uid, uname, gift_name, coin_type, price, count, created_timestamp, rnd=0):
        today = datetime.datetime.today()
        key = cls.gift_key.replace("{year}", str(today.year)).replace("{month}", str(today.month))
        r = await redis_cache.list_push(key, [uid, uname, gift_name, coin_type, price, count, created_timestamp, rnd])
        return r

    @classmethod
    async def get_log(cls):
        today = datetime.datetime.today()
        key = cls.gift_key.replace("{year}", str(today.year)).replace("{month}", str(today.month))
        r = await redis_cache.list_get_all(key)
        return r


async def test():
    key = "test"
    value = None

    r = await redis_cache.set(key, value)
    print(r)

    r = await redis_cache.ttl(key)
    print(r)

    r = await redis_cache.get(key)
    print(r)

    r = await redis_cache.get("abc")
    print(r)

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
