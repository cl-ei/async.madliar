import os.path
from fastapi.responses import FileResponse
from fastapi.responses import Response
from pathlib import Path
from src.ssg.filesystem.user_fs_adapter import get_user_storage_root
from src.ssg.generator import StaticSiteGenerator


async def process_statics(path: str) -> Response:
    if path == "/":
        path = "index.html"

    email = "i@caoliang.net"
    generator = StaticSiteGenerator(email)
    config = await generator.load_config()

    build_root = config.build.source_root
    storage_root = get_user_storage_root(email)

    sub = "_build"
    target = (Path(storage_root) / build_root.strip("/") / sub / path.strip("/")).as_posix()
    target2 = target + ".html"
    for try_file in (target, target2):
        if os.path.exists(try_file) and os.path.isfile(try_file):
            return FileResponse(try_file)

    return Response(status_code=404)
