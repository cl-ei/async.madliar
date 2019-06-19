import os
import json
import asyncio
from app.http import HttpResponse, render_to_response
from etc import DIST_ARTICLE_PATH, CDN_URL, MUSIC_FOLDER, DEBUG
from app.lt import LtOperations


async def robots_response(request):
    response = HttpResponse(
        content=(
            "User-agent:  *\n"
            "Disallow:  /static/\n"
        ),
        content_type="text/plain",
        charset="utf-8"
    )
    return response


async def record_response(request):
    return HttpResponse("")


async def delay_response(request):
    delay = int(request.query.get("delay", 0))
    await asyncio.sleep(delay)
    if request.query.get("json"):
        return HttpResponse('{"code": 0, "msg": "OK"}')
    else:
        return HttpResponse('response "ok!"')


async def game_response(request):
    return render_to_response("templates/game.html")


async def index(request):
    article_js_file_name = ""
    for f in os.listdir(DIST_ARTICLE_PATH):
        if f.lower().endswith(".js"):
            article_js_file_name = f
            break

    if DEBUG:
        article_js_link = os.path.join(DIST_ARTICLE_PATH, article_js_file_name)
    else:
        article_js_link = CDN_URL + "/dist_article/" + article_js_file_name

    context = {
        "article_js_link": article_js_link,
        "page": {
            "author": "CL",
            "description": u"CL，编程爱好者，这是CL的官方博客，记录生活感悟和学习点滴。",
            "keywords": u"MADLIAR, CL, CL's 疯言疯语, 疯言疯语, 风言风语, CL博客",
        },
        "CDN_URL": CDN_URL,
    }
    return render_to_response(
        "templates/index.html",
        context=context
    )


async def thank(request):
    return await LtOperations.thank(request)


async def music_response(request):
    if request.query.get("ref"):
        if not os.path.exists(MUSIC_FOLDER):
            os.mkdir(MUSIC_FOLDER)

        view_data = {
            "ref": True,
            "music_list": json.dumps(os.listdir(MUSIC_FOLDER), ensure_ascii=False)
        }
    else:
        view_data = {"ref": False}

    view_data["CDN_URL"] = CDN_URL
    return render_to_response(
        "templates/music/index.html",
        context=view_data
    )
