from etc.config import DEBUG
from app.handler import (
    index,
    robots,
    record,
    music,
    game,
    lt,
    thank,
    console,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/thank", thank),
    ("get", r"/game", game),
    ("get", r"/robots.txt", robots),
    ("get", r"/record", record),
    ("get", r"/music", music),
    ("get", r"/lt", lt),
    ("get", r"/console", console),
)

static_url_map = (
    ("/dist_article", "./dist_article"),
    ("/music", "./music"),
) if DEBUG else ()
