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
    target3 = (Path(storage_root) / build_root.strip("/") / sub / "404.html").as_posix()
    for i, try_file in enumerate((target, target2, target3)):
        if os.path.exists(try_file) and os.path.isfile(try_file):
            return FileResponse(try_file, status_code=404 if i == 2 else 200)
    raise ValueError("not found")
