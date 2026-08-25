import os
from pathlib import Path


IS_PROD = os.environ.get("RUN_ENV", "") == "prod"

DEBUG = not IS_PROD
if DEBUG:
    print("The app is running in DEBUG mode.")
    LOG_FILE = str(Path.home() / "async.log")
else:
    os.makedirs("/var/log", exist_ok=True)
    LOG_FILE = "/var/log/async.log"

print(f"APP log will be written to this file: {LOG_FILE}")


STORAGE_ROOT = os.environ.get("STORAGE_ROOT")
if not STORAGE_ROOT:
    STORAGE_ROOT = str(Path.home() / "notebook_storage_root")
    print(f"No STORAGE_ROOT configured, storage root dir will be set as: {STORAGE_ROOT}")

# 用于 API 操作
APP_KEY = os.getenv("APP_KEY") or "1"
