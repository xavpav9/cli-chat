import socket, sys, re, select, datetime
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
connected = True

connections = {sock: {}}
sock.listen(5)

messageLog = []
try:
    open("log.txt", "x")
except:
    pass

def removeConn(conn, logInfo="left", globalMsg="has left"):
    if conn in connections.keys():
        username = ""
        if "username" in connections[conn].keys():
            username = connections[conn]["username"]
            logMessage = f"Time: {datetime.datetime.now()} |=> Username: {username} |=> {logInfo}"
            logMsg(logMessage)
            log(f"Terminated connection: {conn}")

        try:
            conn.shutdown(2)
            conn.close()
        except:
            pass
        connections.pop(conn)

        if username != "":
            for otherConn in connections.keys():
                if otherConn != sock:
                    otherConn.send(createMessage("s", f"{username} {globalMsg}."))

def createPacket(text):
    return f"{len(text):<{HEADERSIZE}}{text}"

def createMessage(username, data):
    return f"{createPacket(username)}{createPacket(data)}".encode(encoding="UTF-8")

def decodeMessage(conn):
    try:
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
    except:
        return None


def main():
    global connected
    while connected:
        try:
            connsToRead, connsToWrite, connsInError = select.select(connections.keys(), [], connections.keys())
        except KeyboardInterrupt:
            connected = False
            continue
        except Exception as error:
            connError = False
            for conn in connections.keys():
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
                log(f"New connection: {addr}")
                connections[conn] = {"address": addr}
            else:
                data = decodeMessage(conn)
                if data == None:
                    removeConn(conn)
                elif "username" in connections[conn].keys():
                    log(f"{data} from {connections[conn]['address']}")
                    logMessage = f"Time: {datetime.datetime.now()} |=> Username: {connections[conn]['username']} |=> Message: {data}"
                    logMsg(logMessage)

                    if data == "!users":
                        conn.send(createMessage("s", f"The current users online are: {"\n-    " + "\n-    ".join(getUsernames())}"))
                    elif data == "!quit":
                        removeConn(conn)
                    else:
                        for otherConn in connections.keys():
                            if otherConn != sock and otherConn != conn:
                                otherConn.send(createMessage(connections[conn]["username"], data))
                else:
                    username = data
                    log(f"Username: {username} for {connections[conn]['address']}")

                    usernames = getUsernames()

                    if len(username) < 2 or len(username) > 15 or " " in username:
                        conn.send(createMessage("s", "Invalid username."))
                        removeConn(conn)
                    elif username in usernames:
                        conn.send(createMessage("s", f"Usernames in use: {', '.join(usernames)}."))
                        removeConn(conn)
                    else:
                        connections[conn]["username"] = username
                        logMessage = f"Time: {datetime.datetime.now()} |=> Username: {username} |=> joined"
                        logMsg(logMessage)
                        conn.send(createMessage("s", "Enter !quit to leave or !users to see a list of users currently online.\n"))
                        for otherConn in connections.keys():
                            if otherConn != sock:
                                otherConn.send(createMessage("s", f"{username} has joined."))

def log(msg):
    if not interactive:
        print(msg)

def logMsg(msg):
    messageLog.append(msg)
    with open("log.txt", "r") as file:
        lines = file.readlines()
        file.close()

        for i in range(len(lines)):
            lines[i] = lines[i].strip("\n")

        lines.append(msg)

    with open("log.txt", "w") as file:
        file.write("\n".join(lines) + "\n")
        file.close()

def getUsernames():
    usernames = []
    if len(connections) > 1:
        for conn in connections:
            if "username" in list(connections[conn].keys())[1:]:
                usernames.append(connections[conn]["username"])
        return usernames
    else:
        return []


if interactive:
    mainThread = Thread(target=main)
    mainThread.start()
    print("Enter h for help")
    while connected:
        try:
            command = input("> ")
        except KeyboardInterrupt:
            command = "quit"

        match command:
            case "h" | "help":
                print("h/help = this menu\nlc = list connections\nla = list connections by username and address\nstalk = send out a message as the server\nlog = list current log\nkick = kick a player\nquit/exit = close server")
            case "lc":
                print(f"server: {list(connections.keys())[0]}")
                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        print(conn)
            case "la":
                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        if "username" in connections[conn].keys():
                            username = connections[conn]["username"]
                        else:
                            username = None
                        print(f"Username: \"{username}\", Address: {connections[conn]['address']}")
                else:
                    print(None)
            case "stalk":
                msg = input("Enter message: ")

                for otherConn in connections.keys():
                    if otherConn != sock:
                        otherConn.send(createMessage("s", msg))
            case "log":
                for message in messageLog:
                    print(message)
            case "kick":
                user = input("Enter a user to kick: ")
                removed = False
                for conn in list(connections.keys())[1:]:
                    if "username" in connections[conn].keys():
                        if connections[conn]["username"] == user:
                            conn.send(createMessage("s", "You have been kicked by the server."))
                            print(f"\"{connections[conn]['username']}\" has been removed.")
                            removeConn(conn, "kicked by server", "has been kicked")
                            removed = True
                            break
                if not removed:
                    print("User not found.")
            case "quit" | "exit":
                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        removeConn(conn)
                connected = False
                print("Connections have been terminated. You might need to press <C-c> to exit.")
            case _:
                print("Command not found") 
        
    try:
        mainThread.join()
    except KeyboardInterrupt:
        pass
else:
    main()

print()
