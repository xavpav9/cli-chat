import socket, sys, re, readline, os, datetime
from threading import Thread

#Usage - python(3) server.py ip port

HEADERSIZE = 5
TZ = datetime.datetime.now().astimezone().tzinfo
messages = []

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
while len(username) < 2 or len(username) > 15 or " " in username:
    print("Your username must be between 2 and 15 characters long with no spaces.")
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

def outputMessages():
    global connected, messages
    while connected:
        time = decodeMessage(sock)
        if time == None:
            print("Connection has been terminated. Enter <C-c> or <CR> to exit.")
            connected = False
        else:
            time = datetime.datetime(*[int(i) for i in time.split(":")], datetime.timezone.utc).astimezone(TZ).strftime("%H:%M")
            username = decodeMessage(sock)
            if username != None:
                message = decodeMessage(sock)
                if username == "i":
                    if message == "clear":
                        messages.clear()
                    else:
                        messages.append(["---->", username, message])
                        refreshDisplay(readline.get_line_buffer())
                else:
                    messages.append([time, username, message])
                    refreshDisplay(readline.get_line_buffer())

def refreshDisplay(currentLine):
    def formatMessage(time, username, message):
        if time == "0":
            return f"{username}>: {message}"
        else:
            return f"{time} {username}>: {message}" 

    os.system("clear") 
    if len(messages) != 0:
        print(formatMessage(messages[0][0], messages[0][1], messages[0][2]))
        for messageIndex in range(1, len(messages)):
            time = messages[messageIndex][0]
            if messages[messageIndex][0] == messages[messageIndex - 1][0] and messages[messageIndex][1] != "i":
                time = f"{'=':^5}"
            print(formatMessage(time, messages[messageIndex][1], messages[messageIndex][2]))

    print("\nyou> " + currentLine, end="", flush=True)


sock.connect((ip, port))
connected = True

sock.send(createPacket(username).encode(encoding="UTF-8"))

os.system("clear")
print("\nyou> ", end="", flush=True)

outputThread = Thread(target=outputMessages)
outputThread.start()

while connected:
    try:
        message = input()
    except KeyboardInterrupt:
        message = "/quit"

    if not connected:
        break
    elif len(message) > 1 and message[0] == "/":
        sock.send(createPacket(message).encode(encoding="UTF-8"))
    elif len(message) > 1023:
        messages.append(["---->", "i", "Message above char limit of 1023."])
        refreshDisplay("")
    elif message != "":
        messages.append([datetime.datetime.now().astimezone(TZ).strftime("%H:%M"), username, message])
        refreshDisplay("")
        sock.send(createPacket(message).encode(encoding="UTF-8"))
    else:
        refreshDisplay("")

print("")
sock.close()
outputThread.join()
