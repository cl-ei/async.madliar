import sys
import configparser

print("-"*80)


DEBUG = bool(sys.platform in ("win32", "darwin"))

config = configparser.ConfigParser()
config.read('/etc/madliar.settings.ini')

try:
    CDN_URL = config["default"]["CDN_URL"]
except KeyError:
    CDN_URL = "https://statics.madliar.com"


PROJECT_ROOT = "./" if DEBUG else "/home/wwwroot/async.madliar"
LOG_PATH = "./log" if DEBUG else "/home/wwwroot/log/async.madliar"
MUSIC_FOLDER = "./music" if DEBUG else "/home/wwwroot/statics/music"
RAW_ARTICLE_PATH = "templates/_post/article"
DIST_ARTICLE_PATH = "./dist_article" if DEBUG else "/home/wwwroot/statics/dist_article"
