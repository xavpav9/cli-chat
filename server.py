import socket, sys, re, select
from threading import Thread
    
#Usage - python(3) server.py ip port

interactive = input("Would you like the server to be interactive (y/n)?: ").lower()
interactive = interactive == "y"

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
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((ip, port))

connections = {sock: {}}
sock.listen(5)

def removeConn(conn):
    conn.shutdown(2)
    conn.close()
    connections.pop(conn)
    log(f"Terminated connection: {conn}")

def createPacket(text):
    return f"{len(text):<{HEADERSIZE}}{text}"

def createMessage(username, data):
    return f"{createPacket(username)}{createPacket(data)}".encode(encoding="UTF-8")

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


def main():
    while True:
        try:
            connsToRead, connsToWrite, connsInError = select.select(connections.keys(), [], connections.keys())
        except Exception as error:
            connError = False
            for conn in connections.keys():
                if conn.fileno() == -1:
                    removeConn(conn)
                    connError = True

            if connError:
                continue
            else:
                sys.exit()

        for conn in connsInError:
            removeConn(conn)

        for conn in connsToRead:
            if conn == sock:
                conn, addr = sock.accept()
                log(f"New connection: {addr}")
                connections[conn] = {"address": addr}
            else:
                data = decodeMessage(conn)
                if data == None:
                    removeConn(conn)
                elif "username" in connections[conn].keys():
                    log(f"{data} from {connections[conn]["address"]}")

                    packet = createMessage(connections[conn]["username"], data)

                    for otherConn in connections.keys():
                        if otherConn != sock and otherConn != conn:
                            otherConn.send(createMessage(connections[conn]["username"], data))
                else:
                    username = data
                    log(f"Username: {username} for {connections[conn]["address"]}")
                    if len(username) < 2 or len(username) > 15:
                        conn.send(b"Invalid username.")
                    else:
                        connections[conn]["username"] = username

def log(msg):
    if not interactive:
        print(msg)

if interactive:
    mainThread = Thread(target=main)
    mainThread.start()
    print("Enter h for help")
    while True:
        command = input("> ")
        match command:
            case "h":
                print("lc = list connections\nla = list connections by username and address")
            case "lc":
                print(f"socket: {list(connections.keys())[0]}")
                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        print(conn)
            case "la":
                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        print(f"Username: \"{connections[conn]["username"]}\", Address: {connections[conn]["address"]}")
                else:
                    print(None)
            case _:
                print("Command not found") 
        

    mainThread.join()
else:
    main()
