import socket


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 55555))
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

        print("------- received -------")
        print(content.decode("utf-8"))
        print("--------- end ----------")
        sock.close()


if __name__ == "__main__":
    print("Running...")
    main()


def send_message(msg):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 55555))
    s.send(str(msg).encode("utf-8"))
    s.close()
