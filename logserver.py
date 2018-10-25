import json
import pickle
import pika
import logging
from threading import Thread
from websocket_server import WebsocketServer


global_ws_server = None


def new_client(client, server):
    pass


def client_left(client, server):
    pass


def message_received(client, server, message):
    pass


def on_pika_message(ch, method, properties, body):
    try:
        msg = pickle.loads(body)
        global_ws_server.send_message_to_all(json.dumps({"action": "console", "data": msg}))
    except Exception as e:
        logging.error("Error happend on_pika_message: %s" % e)


def main():
    global global_ws_server
    server = WebsocketServer(8080, "haha5")
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    global_ws_server = server
    t = Thread(target=server.run_forever)
    t.start()

    # pika
    connection_param = pika.ConnectionParameters(host='localhost')
    connection = pika.BlockingConnection(connection_param)
    channel = connection.channel()
    channel.queue_declare(queue='danmaku')
    channel.basic_consume(on_pika_message, queue='danmaku', no_ack=True)
    channel.start_consuming()
    print("Server is running.")


if __name__ == "__main__":
    main()
