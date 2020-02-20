import os
import rsa
import json
import base64
import aiohttp
import datetime
import traceback
from etc.config import CLSERVER_TOKEN
from etc.log4 import http_logger as http_logging
from aiohttp.web import HTTPNotFound
from app.http import HttpResponse, render_to_response
from etc import DIST_ARTICLE_PATH, CDN_URL, MUSIC_FOLDER, DEBUG
from app.lt import LtOperations


async def index(request):
    return render_to_response("templates/home.html", context={"CDN_URL": CDN_URL})


async def old_blog(request):
    article_js_file_name = ""
    for f in os.listdir(DIST_ARTICLE_PATH):
        if f.lower().endswith(".js"):
            article_js_file_name = f
            break

    if DEBUG:
        article_js_link = os.path.join(DIST_ARTICLE_PATH, article_js_file_name)
    else:
        article_js_link = CDN_URL + "/static/article/" + article_js_file_name

    context = {
        "article_js_link": article_js_link,
        "page": {
            "author": "CL",
            "description": u"CL，编程爱好者，这是CL的官方博客，记录生活感悟和学习点滴。",
            "keywords": u"MADLIAR, CL, CL's 疯言疯语, 疯言疯语, 风言风语, CL博客",
        },
        "CDN_URL": CDN_URL,
    }
    return render_to_response("templates/index.html", context=context)


async def robots(request):
    response = HttpResponse(
        content="User-agent:  *\nDisallow:  /static/\n",
        content_type="text/plain",
        charset="utf-8"
    )
    return response


async def record(request):
    return HttpResponse("")


async def music(request):
    if request.query.get("ref"):
        context = {
            "ref": True,
            "music_list": json.dumps(os.listdir(MUSIC_FOLDER), ensure_ascii=False)
        }
    else:
        context = {"ref": False}

    context["CDN_URL"] = CDN_URL
    return render_to_response("templates/music/index.html", context=context)


async def game(request):
    return render_to_response("templates/game.html")


async def lt(request):
    from app.http import HttpResponse
    return HttpResponse("", status=302, headers={"Location": "http://49.234.17.23:1024"})


async def thank(request):
    return await LtOperations.thank(request)


async def console(request):
    context = {
        "title": "log",
        "CDN_URL": CDN_URL,
    }
    return render_to_response("templates/console.html", context=context)


async def grafana(request):
    image_files = os.listdir("/home/wwwroot/statics/static/grafana/img/")
    music_files = os.listdir("/home/wwwroot/statics/static/grafana/music/")
    context = {
        "title": "grafana",
        "CDN_URL": CDN_URL,
        "background_images": ["/static/grafana/img/" + img for img in image_files],
        "background_musics": ["/static/grafana/music/" + mp3 for mp3 in music_files],
    }
    return render_to_response("templates/grafana.html", context=context)


async def bili_live(request):
    image_files = os.listdir("/home/wwwroot/statics/static/grafana/img/")
    music_files = os.listdir("/home/wwwroot/statics/static/grafana/music/")
    context = {
        "title": "grafana",
        "CDN_URL": CDN_URL,
        "background_images": ["/static/grafana/img/" + img for img in image_files],
        "background_musics": ["/static/grafana/music/" + mp3 for mp3 in music_files],
    }
    return render_to_response("templates/bili_live.html", context=context)


async def log(request):
    if request.method == "GET":
        qs = []
        for k, v in request.query.items():
            qs.append(f"{k}:\t{v}")
        qs = '\n'.join(qs)
        http_logging.info(f"➟ {str(datetime.datetime.now())[5:-3]}: Query string:\n{qs}")
        return aiohttp.web.Response(text="OK")

    post_data = await request.post()
    try:
        message = "\n".join([v for k, v in post_data.items() if k != "_raw"])
        if "_raw" not in post_data:
            message = f"{str(datetime.datetime.now())[5:-3]}: {message}"
        http_logging.info(f"➟ {message}")
    except Exception as e:
        import traceback
        http_logging.exception(f"E: {e}, {traceback.format_exc()}")
    return aiohttp.web.Response(status=206)


async def register_clserver(request):
    remote = request.headers.get("X-Real-IP", "")
    if remote:
        data = await request.post()
        if data.get("token") == CLSERVER_TOKEN:
            with open("clserver.remote.txt", "w") as f:
                f.write(remote.strip())
            return aiohttp.web.Response(text="OK")
    return aiohttp.web.Response(status=403)


async def calc_sign(request):
    try:
        post_data = await request.post()
        key = post_data["key"]
        hash_str = post_data["hash_str"]
        password = post_data["password"]

        pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(key.encode())
        hashed_password = base64.b64encode(rsa.encrypt((hash_str + password).encode('utf-8'), pubkey))
        return aiohttp.web.Response(body=hashed_password)
    except Exception as e:
        text = f"e: {e}\n{traceback.format_exc()}"
        return aiohttp.web.Response(text=text, status=500)
