import socket, sys, re, select

#Usage - python(3) server.py ip port

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

connections = [sock]
sock.listen(5)

def removeConn(conn):
    conn.shutdown(2)
    conn.close()
    connections.remove(conn)
    print(f"Terminated connection: {conn}")


while True:
    try:
        connsToRead, connsToWrite, connsInError = select.select(connections, [], connections)
    except Exception as error:
        connError = False
        for conn in connections:
            if conn.fileno() == -1:
                removeConn(conn)
                connError = True

        if connError:
            continue
        else:
            print(error)
            sys.exit()

    for conn in connsInError:
        removeConn(conn)

    for conn in connsToRead:
        if conn == sock:
            conn, addr = sock.accept()
            print(f"New connection: {addr}")
            connections.append(conn)
        else:
            msg = conn.recv(1024)
            if msg == b"":
                removeConn(conn)
            else:
                print(f"{msg.decode(encoding("UTF-8"))} from {conn}")
                for otherConn in connections:
                    if otherConn != sock and otherConn != conn:
                        otherConn.send(msg)
