import socket

ip = "127.0.0.1" # localhost
port = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((ip, port))

sock.listen(5)

while True:
    conn, addr = sock.accept()
    print(addr)
    conn.send(b"Hello")
    conn.shutdown(2)
    conn.close()
