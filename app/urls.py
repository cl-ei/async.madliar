from app.handler import (
    index,
    old_blog,
    music,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/old", old_blog),
    ("get", r"/music", music),
)

static_url_map = (
    ("/static", "static"),
    ("/music", "music"),
)
