import os
import sys
import logging
from etc.config import LOG_PATH


log_format = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
console = logging.StreamHandler(sys.stdout)
console.setFormatter(log_format)
file_handler = logging.FileHandler(os.path.join(LOG_PATH, "madliar.log"))
file_handler.setFormatter(log_format)
madliar_logger = logging.getLogger("madliar")
madliar_logger.setLevel(logging.DEBUG)
madliar_logger.addHandler(console)
madliar_logger.addHandler(file_handler)
