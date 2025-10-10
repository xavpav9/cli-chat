import socket, sys, re

#Usage - python(3) server.py ip port

HEADERSIZE = 5

if len(sys.argv) != 3:
    print("Must provide IP address and port number.")
    sys.exit()
else:
    try:
        valid = re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", sys.argv[1])
        if valid == None:
            raise Exception("Invalid IP address format.")
        else:
            ip = sys.argv[1] # localhost
    except Exception as error:
        print("Problem with IP:")
        print(error)
        sys.exit()

    try:
        if int(sys.argv[2]) > 65535 or int(sys.argv[2]) < 0:
            raise Exception("Port must be between 0 and 65536.")
        port = int(sys.argv[2])
    except Exception as error:
        print("Problem with port:")
        print(error)
        sys.exit()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

username = input("Enter your username: ")
while len(username) < 2 or len(username) > 15:
    username = input("Enter your username: ")

def createPacket(text):
    return f"{len(text):<{HEADERSIZE}}{text}"

def decodeMessage(conn):
    header = conn.recv(HEADERSIZE)
    if header == b"":
        return None
    length = int(header.strip())
    text = b""
    for i in range(length // 8):
        part = conn.recv(8)
        text += part

    part = conn.recv(length % 8)
    text += part

    return text.decode(encoding="UTF-8")

sock.connect((ip, port))

sock.send(createPacket(username).encode(encoding="UTF-8"))

while True:
    msg = input()
    if msg != "":
        print(f"{username}>: {msg}")
        sock.send(createPacket(msg).encode(encoding="UTF-8"))

    username = decodeMessage(sock)
    if username != None:
        data = decodeMessage(sock)
        print(f"{username}>: {data}")
    else:
        print("Connection has been terminated")
        break
sock.close()
