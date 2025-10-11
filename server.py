import socket, sys, re, select, datetime
from threading import Thread
    
#Usage - python(3) server.py ip port numOfRooms

interactive = input("Would you like the server to be interactive (y/n)?: ").lower()
interactive = interactive == "y"

HEADERSIZE = 5

if len(sys.argv) != 4:
    print("Must provide IP address, port number and how many rooms you want.")
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

    try:
        if int(sys.argv[3]) > 9 or int(sys.argv[3]) < 1:
            raise Exception("Number of rooms must be between 1 and 9.")
        numOfRooms = int(sys.argv[3])
    except Exception as error:
        print("Problem with number of rooms:")
        print(error)
        sys.exit()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((ip, port))
connected = True
print(f"...accepting connections on {ip}:{port}")

connections = {sock: {}}
sock.listen(5)

messageLog = []

for i in range(numOfRooms):
    try:
        open(f"log{i + 1}.txt", "x")
    except:
        continue

def removeConn(conn, logInfo="left", globalMsg="has left"):
    if conn in connections.keys():
        username = ""
        if "username" in connections[conn].keys():
            username = connections[conn]["username"]
            chatServer = connections[conn]["room"]
            logMsg(f"Time: {datetime.datetime.now()} |=> Username: {username} |=> {logInfo}", chatServer)
            log(f"Terminated connection: {conn}")

        try:
            conn.shutdown(2)
            conn.close()
        except:
            pass
        connections.pop(conn)

        if username != "":
            for otherConn in connections.keys():
                if otherConn != sock and connections[otherConn]['room'] == chatServer:
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
                connections[conn] = {"address": addr, "room": 1}
            else:
                data = decodeMessage(conn)
                if data == None:
                    removeConn(conn)
                elif "username" in connections[conn].keys():
                    log(f"{data} from {connections[conn]['address']}")
                    logMsg(f"Time: {datetime.datetime.now()} |=> Username: {connections[conn]['username']} |=> Message: {data}", connections[conn]['room'])

                    if data[0] == "!" and len(data) > 1:
                        if data.rstrip(" ") == "!users":
                            conn.send(createMessage("i", "The current users online are: \n-    " + "\n-    ".join(getUsernames(True))))
                        elif data.rstrip(" ") == "!quit":
                            removeConn(conn)
                        elif data.rstrip(" ") == "!help":
                            msg = "Commands begin with a !. Commands available:\n-    !quit to leave.\n-    !users to see a list of users currently online.\n-    !room to see the room you are in.\n"
                            if numOfRooms != 1:
                                msg += "-    ![1-"+str(numOfRooms)+"] to go to that numbered room.\n"
                            conn.send(createMessage("i", msg))
                        elif data.rstrip(" ") == "!room":
                            conn.send(createMessage("i", f"You are in room {connections[conn]['room']} out of {numOfRooms}."))
                        elif data[1] in [str(room + 1) for room in range(numOfRooms)]:
                            newRoom = int(data[1])
                            if data[1] != str(connections[conn]['room']):
                                conn.send(createMessage("s", "clear"))
                                conn.send(createMessage("i", "Enter !help for help.\n"))

                                oldChatServer = connections[conn]['room']

                                msg = f"{connections[conn]['username']} has joined from room {oldChatServer}."
                                logMsg(f"Time: {datetime.datetime.now()} |=> Username: s |=> {msg}", newRoom)
                                for otherConn in connections:
                                    if otherConn != sock and connections[otherConn]['room'] == newRoom:
                                        otherConn.send(createMessage("s", msg))

                                connections[conn]['room'] = newRoom
                                conn.send(createMessage("i", f"You are now in room {connections[conn]['room']}."))

                                msg = f"{connections[conn]['username']} has moved to room {newRoom}."
                                logMsg(f"Time: {datetime.datetime.now()} |=> Username: s |=> {msg}", oldChatServer)
                                for otherConn in connections:
                                    if otherConn != sock and connections[otherConn]['room'] == oldChatServer:
                                        otherConn.send(createMessage("s", msg))
                            else:
                                conn.send(createMessage("i", f"You are already in room {newRoom}."))
                                
                        else:
                            conn.send(createMessage("i", "Unknown command"))
                            
                    else:
                        for otherConn in connections.keys():
                            if otherConn != sock and otherConn != conn and connections[otherConn]['room'] == connections[conn]['room']:
                                otherConn.send(createMessage(connections[conn]["username"], data))
                else:
                    username = data
                    log(f"Username: {username} for {connections[conn]['address']}")

                    usernames = getUsernames(False)

                    if len(username) < 2 or len(username) > 15 or " " in username:
                        conn.send(createMessage("i", "Invalid username."))
                        removeConn(conn)
                    elif username in usernames:
                        conn.send(createMessage("i", f"Usernames in use: {', '.join(usernames)}."))
                        removeConn(conn)
                    else:
                        connections[conn]["username"] = username
                        logMsg(f"Time: {datetime.datetime.now()} |=> Username: {username} |=> joined", 1)
                        conn.send(createMessage("i", "Enter !help for help.\n"))
                        for otherConn in connections.keys():
                            if otherConn != sock and connections[otherConn]['room'] == 1:
                                otherConn.send(createMessage("s", f"{username} has joined."))

def log(msg):
    if not interactive:
        print(msg)

def logMsg(msg, room):
    if room != "a":
        messageLog.append(f"{msg} |=> Room: {room}")
        with open(f"log{room}.txt", "r") as file:
            lines = file.readlines()
            file.close()

            for i in range(len(lines)):
                lines[i] = lines[i].strip("\n")

            lines.append(msg)

        with open(f"log{room}.txt", "w") as file:
            file.write("\n".join(lines) + "\n")
            file.close()
    else:
        for room in range(numOfRooms):
            logMsg(msg, room + 1)

def getUsernames(byChatServer=False):
    usernames = []
    if len(connections) > 1:
        for conn in connections:
            if "username" in list(connections[conn].keys())[1:]:
                if byChatServer:
                    usernames.append(f"{connections[conn]['room']}. {connections[conn]['username']}")
                else:
                    usernames.append(connections[conn]["username"])
        return sorted(usernames)
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
                print("h/help = this menu\nquit/exit = close server\n\nlc = list connections\nla = list connections by username and address\nip = print ip\nport = print port\n\nstalk = send out a message as the server\nlog = list current log\nkick = kick a player")
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
                newRoom = input("Enter a room (a=all): ")
                if newRoom not in [str(room + 1) for room in range(numOfRooms)] and newRoom != "a":
                    print("Not a valid room.")
                else:
                    msg = input("Enter message: ")
                    if newRoom == "a":
                        logMsg(f"Time: {datetime.datetime.now()} |=> Username: s |=> {msg}", "a")

                        for otherConn in connections.keys():
                            if otherConn != sock:
                                otherConn.send(createMessage("s", msg))
                    else:
                        newRoom = int(newRoom)
                        logMsg(f"Time: {datetime.datetime.now()} |=> Username: s |=> {msg}", newRoom)

                        for otherConn in connections.keys():
                            if otherConn != sock and connections[otherConn]['room'] == newRoom:
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
            case "ip":
                print(ip)
            case "port":
                print(port)
            case _:
                print("Command not found") 
        print()
        
    try:
        mainThread.join()
    except KeyboardInterrupt:
        pass
else:
    main()

print()
