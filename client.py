import socket

ip = "127.0.0.1" # localhost
port = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.connect((ip, port))

print(sock.recv(1024).decode(encoding="UTF-8"))
sock.close()
