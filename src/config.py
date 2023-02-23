import os

LOG_PATH = "logs/"
BLOG_REPO_ROOT = "temp/blog"
BLOG_DIST_PATH = "src/static/new_blog"
LAST_COMMIT_FILE = "src/static/new_blog/last_commit_id"
BLOG_STATIC_PREFIX = "/static/new_blog"

os.makedirs(BLOG_REPO_ROOT, exist_ok=True)
os.makedirs(BLOG_DIST_PATH, exist_ok=True)
