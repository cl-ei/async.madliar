import os
import sys
import json
import pickle
import pika
import logging
from threading import Thread
from websocket_server import WebsocketServer


if sys.platform == "darwin":
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
    logging.info("Message received: %s" % json.dumps(msg))
    print("Message received: %s" % json.dumps(msg))
    global_ws_server.send_message_to_all(json.dumps(msg))


def on_pika_message(ch, method, properties, body):
    try:
        parse_message_from_monitor(pickle.loads(body))
    except Exception as e:
        logging.error("Error happend on_pika_message: %s" % e)


def main():
    global global_ws_server
    server = WebsocketServer(8080, "haha5")
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    global_ws_server = server
    t = Thread(target=server.run_forever)
    t.start()

    # pika
    connection_param = pika.ConnectionParameters(host='localhost')
    connection = pika.BlockingConnection(connection_param)
    channel = connection.channel()
    channel.queue_declare(queue='prizeinfo')
    channel.basic_consume(on_pika_message, queue='prizeinfo', no_ack=True)
    channel.start_consuming()
    print("Server is running.")


if __name__ == "__main__":
    main()
