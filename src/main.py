from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from src.midddleware import ErrorCatchMiddleware
from src.router import router as main_router


PROJECT_NAME = "async.madliar"
DEBUG = False
VERSION = "1.0"


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

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(ErrorCatchMiddleware)
    application.mount("/static", StaticFiles(directory="src/static"), name="static")
    application.include_router(main_router, prefix="")

    return application


app = get_application()
