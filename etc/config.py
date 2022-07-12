import sys
import os
import configparser

print("-"*80)


# DEBUG = bool(sys.platform in ("win32", "darwin"))
DEBUG = True


config = configparser.ConfigParser()
config.read('/etc/madliar.settings.ini')

try:
    CDN_URL = config["default"]["CDN_URL"]
except KeyError:
    CDN_URL = "https://statics.madliar.com"

try:
    CLSERVER_TOKEN = config["default"]["CLSERVER_TOKEN"]
except KeyError:
    CLSERVER_TOKEN = ""

REDIS_CONFIG = {}
try:
    REDIS_CONFIG["host"] = config["redis"]["host"]
    REDIS_CONFIG["port"] = int(config["redis"]["port"])
    REDIS_CONFIG["password"] = config["redis"]["password"]
    REDIS_CONFIG["db"] = int(config["redis"]["stormgift_db"])
except KeyError:
    REDIS_CONFIG["host"] = "49.234.17.23"
    REDIS_CONFIG["port"] = 19941
    REDIS_CONFIG["password"] = "redispassword"
    REDIS_CONFIG["db"] = 2

print(REDIS_CONFIG)

LOG_PATH = "./log" if DEBUG else "/home/wwwroot/log/async.madliar"
PROJECT_ROOT = "./" if DEBUG else "/home/wwwroot/async.madliar"
MUSIC_FOLDER = "./music" if DEBUG else "/home/wwwroot/statics/music"
RAW_ARTICLE_PATH = "templates/_post/article"
DIST_ARTICLE_PATH = "./dist_article" if DEBUG else "/home/wwwroot/statics/static/article"

os.makedirs(LOG_PATH, exist_ok=True)
os.makedirs(DIST_ARTICLE_PATH, exist_ok=True)
