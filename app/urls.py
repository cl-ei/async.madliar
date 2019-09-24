from etc.config import DEBUG
from app.handler import (
    index,
    old_blog,
    robots,
    record,
    music,
    game,
    lt,
    thank,
    console,
    grafana,
    log,
    register_clserver,
    cls_server,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/old_blog", old_blog),
    ("get", r"/thank", thank),
    ("get", r"/game", game),
    ("get", r"/robots.txt", robots),
    ("get", r"/record", record),
    ("get", r"/music", music),
    ("get", r"/lt", lt),
    ("get", r"/console", console),
    ("get", r"/grafana", grafana),
    ("post", r"/log", log),
    ("post", r"/register_clserver", register_clserver),
    ("get", r"/cls_server", cls_server),
)

static_url_map = (
    ("/dist_article", "./dist_article"),
    ("/music", "./music"),
) if DEBUG else ()
