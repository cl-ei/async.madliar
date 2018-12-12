import os
import sys
import logging


if sys.platform == "darwin":
    DEBUG = True
    LOG_PATH = "./log/"
else:
    DEBUG = False
    LOG_PATH = "/home/wwwroot/log/"

fh = logging.FileHandler(os.path.join(LOG_PATH, "qqbot.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(message)s'))
logger = logging.getLogger("qqbot")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


def onQQMessage(bot, contact, member, content):
    msg = "\n\n%s, %s, %s, %s\n\n" % (bot, contact, member, content)
    print(msg)
    logging.info(msg)

