import asyncio
import os
import shutil
import logging
from src.ssg.generator import StaticSiteGenerator
from src.ssg.oss_syncer import OSSSyncer
from src.config import STORAGE_ROOT, IS_PROD


EMAIL = "i@caoliang.net"


def load_access_key(env_file: str) -> tuple[str, str]:
    access_key_id = ""
    access_key_secret = ""
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")  # 去掉两端空白和引号
                if key == "ACCESS_KEY_ID":
                    access_key_id = value
                elif key == "ACCESS_KEY_SECRET":
                    access_key_secret = value
    if not access_key_id or not access_key_secret:
        raise ValueError("ACCESS_KEY_ID or ACCESS_KEY_SECRET not found in env file")
    return access_key_id, access_key_secret


async def generate():
    logging.info(f"start gen static site, STORAGE_ROOT: {STORAGE_ROOT}")

    ssg = StaticSiteGenerator(EMAIL)
    flag, msg = await ssg.gen()
    logging.info(f"gen result: {flag}, msg: {msg}")
    if not flag:
        return

    # 这里要做3步，拷贝静态文件，拷贝original-intention，拷贝其他文件
    config = await ssg.load_config()
    statics_root = "%s/%s/%s" % (ssg.adapter.storage_root, config.build.source_root.strip('/'), "_statics")
    await ssg.adapter.copy_tree(statics_root, f"{ssg.write_root}/statics")

    # original-intention
    cwd = os.getcwd()
    shutil.copy2(f"{cwd}/src/tpl/original-intention.html", f"{ssg.write_root}/original-intention.html")
    shutil.copytree(f"{cwd}/src/statics", f"{ssg.write_root}/original-intention/statics", dirs_exist_ok=True)

    # copy robots.txt etc.
    shutil.copytree(f"{cwd}/src/global_site_files", ssg.write_root, dirs_exist_ok=True)
    logging.info("gen complete!")


async def upload_to_oss():
    if IS_PROD:
        env_file = "root/.env"
    else:
        env_file = r"C:\Users\Administrator\.env"

    key_id, key_secret = load_access_key(env_file)
    syncer = OSSSyncer(
        access_key_id=key_id,
        access_key_secret=key_secret,
        endpoint='https://oss-cn-beijing.aliyuncs.com',
        bucket_name='madliar',
    )
    ssg = StaticSiteGenerator(EMAIL)
    await ssg.load_config()
    final = syncer.sync_to_remote(ssg.write_root, '')
    logging.info(f"upload result: {final}")
