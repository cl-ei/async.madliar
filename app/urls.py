from etc.config import DEBUG
from app.handler import (
    index,
    thank,
    robots_response,
    record_response,
    music_response,
    delay_response,
    game_response,
)


async def lt_response(rq):
    from app.http import HttpResponse
    return HttpResponse("", status=302, headers={"Location": "http://49.234.17.23:1024"})


user_url_map = (
    ("get", r"/", index),
    ("get", r"/thank", thank),
    ("get", r"/game", game_response),
    ("get", r"/robots.txt", robots_response),
    ("get", r"/record", record_response),
    ("get", r"/music", music_response),
    ("get", r"/delay", delay_response),
    ("post", r"/delay", delay_response),
    ("get", r"/lt", lt_response),
)

static_url_map = (
    ("/dist_article", "./dist_article"),
    ("/music", "./music"),
) if DEBUG else ()
