import os
import socket
import logging
import pickle
import datetime

fh = logging.FileHandler(os.path.join("/home/wwwroot/notebook.madliar/notebook_user/i@caoliang.net", "papaya_log.txt"))
log_format = '%(asctime)s: %(message)s'
fh.setFormatter(logging.Formatter(log_format))
logger = logging.getLogger("papapa_loger")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger

import pika
# pika
connection_param = pika.ConnectionParameters(host='localhost')
pika_connection = pika.BlockingConnection(connection_param)
pika_channel = pika_connection.channel()
pika_channel.queue_declare(queue='danmaku')


def send_message_to_songlist_server(msg):
    pika_channel.basic_publish(exchange='', routing_key='danmaku', body=pickle.dumps(msg))


# when tears down
# pika_connection.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', 55555))
    s.listen(5)
    while True:
        sock, addr = s.accept()
        content = None
        while True:
            data = sock.recv(1024)
            if data:
                content = content + data if content else data
            else:
                break

        msg = content.decode("utf-8")
        logging.info(msg)
        send_message_to_songlist_server(str(datetime.datetime.now())[:-3] + " > " + msg)
        sock.close()


if __name__ == "__main__":
    print("Running...")
    main()


def send_message(msg):
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('47.104.176.84', 55555))
        s.send(str(msg).encode("utf-8"))
        s.close()
    except Exception:
        pass
