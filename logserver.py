import os
import socket


import logging

fh = logging.FileHandler(os.path.join("./log", "papaya.log"))
log_format = '%(asctime)s: %(message)s'
fh.setFormatter(logging.Formatter(log_format))
logger = logging.getLogger("papapa_loger")
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logging = logger


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
        logging.info(content.decode("utf-8"))
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
