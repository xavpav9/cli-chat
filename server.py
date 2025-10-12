import socket, sys, re, select, datetime
from time import sleep
from threading import Thread
    
#Usage - python(3) server.py ip port numOfRooms interactive(y/n)

HEADERSIZE = 5

if len(sys.argv) != 5:
    print("Usage - python(3) server.py ip port numOfRooms interactive(y/n)")
    print("Must provide IP address, port number, how many rooms you want and whether you want the server to be interactive (y) or not (n).")
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

    try:
        if sys.argv[4].lower() not in ["n", "no", "y", "yes"]:
            raise Exception("Interactivity must be y or n")
        interactive = sys.argv[4] in ["y", "yes"]
    except Exception as error:
        print("Problem with interactivity:")
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

def removeConn(conn, logInfo="has left"):
    if conn in connections.keys():
        username = ""
        if "username" in connections[conn].keys():
            username = connections[conn]["username"]
            message = f"{username} {logInfo}."
            chatServer = connections[conn]["room"]
            time = datetime.datetime.now()
            logMessage(time, "s", message, chatServer)
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
                    otherConn.send(createMessage("s", message, time))

def createPacket(text):
    return f"{len(text):<{HEADERSIZE}}{text}"

def createMessage(username, message, time=datetime.datetime.now()):
    return f"{createPacket(time.strftime("%H:%M"))}{createPacket(username)}{createPacket(message)}".encode(encoding="UTF-8")

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

def log(message):
    if not interactive:
        print(message)

def logMessage(time, username, message, room):
    if room != "a":
        data = [time, username, message]
        messageLog[room - 1].append(data)
        with open(f"log{room}.txt", "r") as file:
            lines = file.readlines()
            file.close()

            for i in range(len(lines)):
                lines[i] = lines[i].strip("\n")

            lines.append(f"Time: {data[0]} |=> Username: {data[1]} |=> Message: {data[2]}")

        with open(f"log{room}.txt", "w") as file:
            file.write("\n".join(lines) + "\n")
            file.close()
    else:
        for room in range(numOfRooms):
            logMessage(time, username, message, room + 1)

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

def clearScreen(conn):
    conn.send(createMessage("i", "clear"))
    conn.send(createMessage("i", "Enter /help for help.\n"))

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
                message = decodeMessage(conn)
                if message == None:
                    removeConn(conn)
                elif "username" in connections[conn].keys():
                    log(f"{message} from {connections[conn]['address']}")

                    if message[0] == "/" and len(message) > 1:
                        if message.rstrip(" ") == "/users":
                            conn.send(createMessage("i", "The current users online are: \n      -    " + "\n      -    ".join(getUsernames(True))))
                        elif message.rstrip(" ") == "/quit":
                            removeConn(conn)
                        elif message.rstrip(" ") == "/help":
                            message = "Commands begin with a /. Commands available:\n      -    /quit to leave.\n      -    /users to see a list of users currently online.\n      -    /room to see the room you are in.\n      -    /history to view all the messages stored in the current log\n      -    /clear to clear the current screen"
                            if numOfRooms != 1:
                                message += "\n      -    /[1-"+str(numOfRooms)+"] to go to that numbered room."
                            conn.send(createMessage("i", message))
                        elif message.rstrip(" ") == "/room":
                            conn.send(createMessage("i", f"You are in room {connections[conn]['room']} out of {numOfRooms}."))
                        elif message.rstrip(" ") == "/history":
                            clearScreen(conn)
                            for data in messageLog[connections[conn]['room'] - 1]:
                                conn.send(createMessage(data[1], data[2], data[0]))
                        elif message.rstrip(" ") == "/clear":
                            clearScreen(conn)
                        elif message[1:] in [str(room + 1) for room in range(numOfRooms)]:
                            newRoom = int(message[1:])
                            if message[1:] != str(connections[conn]['room']):
                                clearScreen(conn)

                                oldChatRoom = connections[conn]['room']

                                message = f"{connections[conn]['username']} has joined from room {oldChatRoom}."
                                time = datetime.datetime.now()
                                logMessage(time, "s", message, newRoom)
                                for otherConn in connections:
                                    if otherConn != sock and connections[otherConn]['room'] == newRoom:
                                        otherConn.send(createMessage("s", message, time))

                                connections[conn]['room'] = newRoom
                                conn.send(createMessage("i", f"You are now in room {connections[conn]['room']}."))

                                message = f"{connections[conn]['username']} has moved to room {newRoom}."
                                logMessage(time, "s", message, oldChatRoom)
                                for otherConn in connections:
                                    if otherConn != sock and connections[otherConn]['room'] == oldChatRoom:
                                        otherConn.send(createMessage("s", message, time))
                            else:
                                conn.send(createMessage("i", f"You are already in room {newRoom}."))
                                
                        else:
                            conn.send(createMessage("i", "Unknown command"))
                            
                    else:
                        if len(message) > 1023:
                            conn.send(createMessage("i", "Message above char limit of 1023."))
                        else:
                            time = datetime.datetime.now()
                            logMessage(time, connections[conn]['username'], message, connections[conn]['room'])
                            for otherConn in connections.keys():
                                if otherConn != sock and otherConn != conn and connections[otherConn]['room'] == connections[conn]['room']:
                                    otherConn.send(createMessage(connections[conn]["username"], message, time))
                else:
                    username = message
                    log(f"Username: {username} for {connections[conn]['address']}")

                    usernames = getUsernames(False)

                    if len(username) < 2 or len(username) > 15 or " " in username:
                        conn.send(createMessage("i", "Invalid username."))
                        removeConn(conn)
                    elif username in usernames:
                        conn.send(createMessage("i", "Invalid username."))
                        conn.send(createMessage("i", f"Usernames in use: {', '.join(usernames)}."))
                        removeConn(conn)
                    else:
                        connections[conn]["username"] = username
                        message = f"{username} has joined."
                        time = datetime.datetime.now()
                        logMessage(time, "s", message, 1)
                        conn.send(createMessage("i", "Enter /help for help.\n"))
                        for otherConn in connections.keys():
                            if otherConn != sock and connections[otherConn]['room'] == 1:
                                otherConn.send(createMessage("s", message, time))

for room in range(numOfRooms):
    messageLog.append([])
    try:
        open(f"log{room + 1}.txt", "x")
    except:
        pass
    logMessage(datetime.datetime.now(), "s", "room created", room + 1)

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
                print("h/help = this menu\nquit/exit = close server\n\nlc = list connections\nla = list connections by username, address and room\nip = print ip\nport = print port\n\nrooms = print number of rooms\nmkroom = makes a new room\nrmroom = removes the last room\n\nstalk = send out a message as the server\nlog = list current log\nkick = kick a player")
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
                        print(f"Username: \"{username}\", Address: {connections[conn]['address']}, Room: {connections[conn]['room']}")
                else:
                    print(None)
            case "stalk":
                newRoom = input("Enter a room (a=all): ")
                if newRoom not in [str(room + 1) for room in range(numOfRooms)] and newRoom != "a":
                    print("Not a valid room.")
                else:
                    message = input("Enter message: ")
                    if newRoom == "a":
                        time = datetime.datetime.now()
                        logMessage(time, "s", message, "a")

                        for otherConn in connections.keys():
                            if otherConn != sock:
                                otherConn.send(createMessage("s", message, time))
                    else:
                        newRoom = int(newRoom)
                        time = datetime.datetime.now()
                        logMessage(time, "s", message, newRoom)

                        for otherConn in connections.keys():
                            if otherConn != sock and connections[otherConn]['room'] == newRoom:
                                otherConn.send(createMessage("s", message, time))
            case "log":
                for room in range(len(messageLog)):
                    if len(messageLog[room]) != 0:
                        print(f"Room: {room + 1}")
                        for data in messageLog[room]:
                            print(f"-    Time: {data[0]} |=> Username: {data[1]} |=> Message: {data[2]}")
            case "kick":
                user = input("Enter a user to kick: ")
                removed = False
                for conn in list(connections.keys())[1:]:
                    if "username" in connections[conn].keys():
                        if connections[conn]["username"] == user:
                            conn.send(createMessage("i", "You have been kicked by the server."))
                            print(f"\"{connections[conn]['username']}\" has been removed.")
                            removeConn(conn, "has been kicked")
                            removed = True
                            break
                if not removed:
                    print("User not found.")
            case "quit" | "exit":
                for room in range(len(messageLog)):
                    logMessage(datetime.datetime.now(), "s", "room removed", room + 1)

                if len(connections) > 1:
                    for conn in list(connections.keys())[1:]:
                        removeConn(conn)
                connected = False
                print("Connections have been terminated. You might need to press <C-c> to exit.")
            case "ip":
                print(ip)
            case "port":
                print(port)
            case "rooms":
                print(numOfRooms)
            case "mkroom":
                if numOfRooms == 9:
                    print("You already have the max number of rooms.")
                else:
                    numOfRooms += 1
                    try:
                        open(f"log{numOfRooms}.txt", "x")
                    except:
                        pass
                    messageLog.append([])
                    logMessage(datetime.datetime.now(), "s", "room created", numOfRooms)
                    print(f"Room {numOfRooms} has been made.")
            case "rmroom":
                if numOfRooms == 1:
                    print("You already have the minimum number of rooms.")
                else:
                    print("Wait 3 seconds.")
                    message = "This room is being removed by the server in 3 seconds. You will be sent to room 1."
                    time = datetime.datetime.now()
                    logMessage(time, "s", message, numOfRooms)

                    for conn in list(connections.keys())[1:]:
                        if connections[conn]['room'] == numOfRooms:
                            conn.send(createMessage("s", message, time))

                    sleep(3)

                    for conn in list(connections.keys())[1:]:
                        if connections[conn]['room'] == numOfRooms:
                            clearScreen(conn)

                            oldChatRoom = connections[conn]['room']

                            message = f"{connections[conn]['username']} has joined from the removed room {oldChatRoom}."
                            time = datetime.datetime.now()
                            logMessage(time, "s", message, 1)
                            for otherConn in connections:
                                if otherConn != sock and connections[otherConn]['room'] == 1:
                                    otherConn.send(createMessage("s", message, time))

                            connections[conn]['room'] = 1
                            conn.send(createMessage("i", f"You are now in room {connections[conn]['room']}."))

                            message = f"{connections[conn]['username']} has moved to room 1."
                            logMessage(datetime.datetime.now(), "s", message, oldChatRoom)

                    logMessage(datetime.datetime.now(), "s", "room removed", numOfRooms)

                    messageLog.pop()
                    numOfRooms -= 1
                    print(f"Room {numOfRooms + 1} has been removed.")

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
