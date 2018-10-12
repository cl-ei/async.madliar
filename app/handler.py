import os
import json
from app.http import HttpResponse, render_to_response
from etc import (
    PROJECT_ROOT,
    PARSED_ARTICLE_JSON,
    PARSED_ARTICLE_JSON_PATH,
    CDN_URL,
    MUSIC_FOLDER,
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
    article_file_path = os.path.join(PROJECT_ROOT, PARSED_ARTICLE_JSON)
    article_js_file_name = os.listdir(article_file_path)[0]
    article_js = os.path.join(PARSED_ARTICLE_JSON_PATH, article_js_file_name)
    context = {
        "article_js": article_js,
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
        encoding = "utf-8"
        view_data = {
            "ref": True,
            "music_list": json.dumps(
                [_.decode(encoding) for _ in os.listdir(MUSIC_FOLDER)],
                ensure_ascii=False
            )
        }
    else:
        view_data = {"ref": False}

    view_data["CDN_URL"] = CDN_URL
    return render_to_response(
        "templates/music/index.html",
        context=view_data
    )
