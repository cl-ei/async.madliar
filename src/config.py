import os
import sys
from pathlib import Path

DEBUG = bool(sys.platform == "win32")
if DEBUG:
    print("The app is running in DEBUG mode.")

if DEBUG:
    LOG_FILE = str(Path.home() / "async.log")
else:
    LOG_FILE = os.environ.get("LOG_FILE")
    if not LOG_FILE:
        LOG_FILE = "/var/logs/async.log"
print(f"APP log will be written to this file: {LOG_FILE}")

LOG_PATH = "logs/"
BLOG_REPO_ROOT = "temp/blog"
BLOG_DIST_PATH = "src/static/new_blog"
LAST_COMMIT_FILE = "src/static/new_blog/last_commit_id"
BLOG_STATIC_PREFIX = "/static/new_blog"

os.makedirs(BLOG_REPO_ROOT, exist_ok=True)
os.makedirs(BLOG_DIST_PATH, exist_ok=True)
