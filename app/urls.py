from etc.config import DEBUG
from app.handler import (
    index,
    robots_response,
    record_response,
    music_response,
    console_response,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/robots.txt", robots_response),
    ("get", r"/record", record_response),
    ("get", r"/music", music_response),
    ("get", r"/console", console_response),
)

static_url_map = (
    ("/dist_article", "./dist_article"),
    ("/music", "./music"),
) if DEBUG else ()
