import sys
DEBUG = bool(sys.platform in ("win32", "darwin"))

PROJECT_ROOT = "./" if DEBUG else "/home/wwwroot/async.madliar.com"
LOG_PATH = "./log" if DEBUG else "/home/wwwroot/log/async.madliar"
MUSIC_FOLDER = "./music" if DEBUG else "/home/wwwroot/statics/music"
RAW_ARTICLE_PATH = "templates/_post/article"
DIST_ARTICLE_PATH = "./dist_article" if DEBUG else "/home/wwwroot/statics/dist_article"
CDN_URL = "https://statics.madliar.com"

