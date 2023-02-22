import os
import sys
import logging

LOG_PATH = "logs/"
os.makedirs(LOG_PATH, exist_ok=True)


log_format = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")

console = logging.StreamHandler(sys.stdout)
console.setFormatter(log_format)

file_handler = logging.FileHandler(os.path.join(LOG_PATH, "async.madliar.log"))
file_handler.setFormatter(log_format)

http_log_handler = logging.FileHandler(os.path.join(LOG_PATH, "http_logger.log"))
http_log_handler.setFormatter(logging.Formatter("%(message)s"))

website_logger = logging.getLogger("async.madliar")
website_logger.setLevel(logging.DEBUG)
website_logger.addHandler(console)
website_logger.addHandler(file_handler)
