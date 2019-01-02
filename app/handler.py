import os
import json
from app.http import HttpResponse, render_to_response
from etc import (
    PROJECT_ROOT,
    DIST_ARTICLE_PATH,
    CDN_URL,
    MUSIC_FOLDER,
    DEBUG,
)


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


async def record_response(req):
    return HttpResponse("")


async def index(req):
    article_js_file_name = ""
    for f in os.listdir(DIST_ARTICLE_PATH):
        if f.lower().endswith(".js"):
            article_js_file_name = f
            break
    if DEBUG:
        article_js_link = os.path.join(DIST_ARTICLE_PATH, article_js_file_name)
    else:
        article_js_link = CDN_URL + os.path.join("dist_article", article_js_file_name)
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


async def console_response(request):
    view_data = {"CDN_URL": CDN_URL}
    return render_to_response(
        "templates/console.html",
        context=view_data
    )
