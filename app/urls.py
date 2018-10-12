from app.handler import (
    robots_response,
    index,
)


user_url_map = (
    ("get", r"/", index),
    ("get", r"/robots.txt", robots_response),
    # r"^/record": record,
    # r"^/blog": blog_url_map,
    # r"^/music": music_url_map,
    # r"^/notebook": notebook_url_map,
    # r"^/timeout": timeout_response,),
)

static_url_map = (
    ("/static", "static"),
)
