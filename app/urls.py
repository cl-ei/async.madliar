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
    bili_live,
    log,
    register_clserver,
    calc_sign,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/old", old_blog),
    ("get", r"/thank", thank),
    ("get", r"/game", game),
    ("get", r"/robots.txt", robots),
    ("get", r"/record", record),
    ("get", r"/music", music),
    ("get", r"/lt", lt),
    ("get", r"/console", console),
    ("get", r"/grafana", grafana),
    ("get", r"/bili_live", bili_live),
    ("post", r"/log", log),
    ("get", r"/log", log),
    ("post", r"/register_clserver", register_clserver),
    ("post", r"/calc_sign", calc_sign),
)

static_url_map = (
    ("/dist_article", "./dist_article"),
    ("/music", "./music"),
) if DEBUG else ()
