import os
import sys
import json
import pickle
import socket
import logging
import traceback
from threading import Thread
from websocket_server import WebsocketServer


if sys.platform in ("darwin", "win32"):
    DEBUG = True
    LOG_PATH = "./log/"
else:
    DEBUG = False
    LOG_PATH = "/home/wwwroot/log/"


fh = logging.FileHandler(os.path.join(LOG_PATH, "prizeserver.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger = logging.getLogger("prizeserver")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger

global_ws_server = None


def new_client(client, server):
    logging.info("New client connected and was given id %d, addr: %s" % (client['id'], client['address']))


def client_left(client, server):
    logging.info("Client(%d) disconnected." % client['id'])


def parse_message_from_monitor(msg):
    jsonstring = json.dumps(msg, ensure_ascii=False)
    msg_string = "Message received: %s" % jsonstring
    logging.info(msg_string)
    print(msg_string)
    global_ws_server.send_message_to_all(jsonstring)


def main():
    global global_ws_server
    server = WebsocketServer(8080, "haha5")
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    global_ws_server = server
    t = Thread(target=server.run_forever)
    t.start()

    # UDP server
    monitor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    monitor.bind(('0.0.0.0', 11111))
    print("Server is running.")

    while True:
        try:
            data, addr = monitor.recvfrom(10240)
            msg = pickle.loads(data)
            parse_message_from_monitor(msg)
        except Exception as e:
            error_msg = traceback.format_exc()
            logging.error(error_msg)
            raise e


if __name__ == "__main__":
    main()
