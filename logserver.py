import json
import pickle
import pika
import logging
from threading import Thread
from websocket_server import WebsocketServer


global_ws_server = None
cached_message = []


def new_client(client, server):
    for msg in cached_message:
        server.send_message(client, msg)


def client_left(client, server):
    pass


def message_received(client, server, message):
    pass


def on_pika_message(ch, method, properties, body):
    try:
        msg = pickle.loads(body)
        json_message = json.dumps({"action": "console", "data": msg})
        global_ws_server.send_message_to_all(json_message)

        cached_message.append(json_message)
        if len(cached_message) > 80:
            cached_message.pop(0)
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
