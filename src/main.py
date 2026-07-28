import sys
import logging
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles as StarletteStaticFiles
from starlette.middleware.cors import CORSMiddleware
from src.config import LOG_FILE
from src.midddleware import ErrorCatchMiddleware
from src.router import router as main_router


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

logging.getLogger("asyncio").setLevel(logging.INFO)


PROJECT_NAME = "async.madliar"
DEBUG = False
VERSION = "1.0"


class CORSStaticFiles(StarletteStaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # 字体/静态资源：不需要凭证，直接通配，最稳
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Vary"] = "Origin"
        return response


def get_application() -> FastAPI:
    application = FastAPI(
        title=PROJECT_NAME,
        debug=DEBUG,
        version=VERSION,
        openapi_url="",
        docs_url="",
        redoc_url="",
        swagger_ui_oauth2_redirect_url="",
    )

    application.add_middleware(ErrorCatchMiddleware)
    application.mount("/static", CORSStaticFiles(directory="src/static", html=True), name="static")
    application.include_router(main_router, prefix="")

    return application


app = get_application()
