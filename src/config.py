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
