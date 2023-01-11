import os

print("-"*80)

CDN_URL = ""

PROJECT_ROOT = "./"
LOG_PATH = "./logs"
MUSIC_FOLDER = "./music"
RAW_ARTICLE_PATH = "templates/_post/article"
DIST_ARTICLE_PATH = "static/blog/dist_article"

os.makedirs(LOG_PATH, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(RAW_ARTICLE_PATH, exist_ok=True)
os.makedirs(DIST_ARTICLE_PATH, exist_ok=True)
