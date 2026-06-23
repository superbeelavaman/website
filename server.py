from socket import *
import os, sys, random
import math, datetime
import re, magic
import html
import urllib
import urllib.parse
import userManagement
import time
import threading
import calendar
import subprocess

running = True

ALLOWED_METHODS = {"GET", "POST", "HEAD"}

script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
webroot_real = os.path.realpath(script_directory + "/webroot")

trying = True
while trying:
    try:
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', 8123))
        serverSocket.listen(128)
        trying = False
    except Exception as e:
        print("Waiting for socket to be free...")
        print(e)
        time.sleep(1)

recentConnections = []
recentConnectionsExtended = []
recentConnections_lock = threading.Lock()


def get_last_modified(path: str) -> str:
    mtime = os.path.getmtime(path)
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))

def is_newer_than(path: str, date_str: str) -> bool:
    mtime = os.path.getmtime(path)
    parsed = time.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
    return mtime > calendar.timegm(parsed)

def recv_full(sock, timeout=5):
    """Receive a full HTTP request, not just the first 1024 bytes.
    Reads until the end of headers, then reads Content-Length more bytes
    for the body if present."""
    sock.settimeout(timeout)
    data = b""
    try:
        while b"\r\n\r\n" not in data and b"\n\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        # Split off headers to check Content-Length
        if b"\r\n\r\n" in data:
            header_part, body_so_far = data.split(b"\r\n\r\n", 1)
        elif b"\n\n" in data:
            header_part, body_so_far = data.split(b"\n\n", 1)
        else:
            return data.decode(errors="replace")

        # Check for Content-Length and read remaining body bytes
        content_length = 0
        for line in header_part.decode(errors="replace").splitlines():
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                break

        while len(body_so_far) < content_length:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body_so_far += chunk

        return (header_part + b"\r\n\r\n" + body_so_far).decode(errors="replace")
    except TimeoutError:
        return data.decode(errors="replace")

blocklist_lock = threading.Lock()

def addtoblocklist(IP):
    with blocklist_lock:
        with open("/etc/nginx/blocklist.txt", "a") as blocklistfile:
            blocklistfile.write(IP + " 1;\n")
        subprocess.run(["sudo","systemctl","reload","nginx"])

blocked_agents_lock = threading.Lock()

def load_blocked_agents(path: str) -> set:
    try:
        with open(path) as f:
            return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
    except FileNotFoundError:
        return set()

blocked_agents_file = script_directory + "/blocked_agents.txt"
blocked_agents = load_blocked_agents(blocked_agents_file)

def handle_connection(connectionSocket, addr):
    global recentConnections
    global recentConnectionsExtended

    sourceIP, sourcePort = addr

    responseType = "200 OK"
    responseHeaders = b""
    responsecontent = b""
    fullRequestPath = ""
    contentType = ""

    message = recv_full(connectionSocket)
    connectionSocket.settimeout(None)
    try:
        messages = message.replace('\r\n', '\n').split('\n')

        requestheaders = []
        for i in range(len(messages)):
            if i > 0:
                if len(messages[i]) == 0:
                    break
                requestheaders.append(messages[i])
        ClientTargetHost     = ''
        ClientUserAgent      = ''
        ClientContentLength  = ''
        ClientAcceptTypes    = ''
        ClientAcceptLanguage = ''
        ClientAcceptEncoding = ''
        ClientConnectionType = ''
        ClientUseHTTPS       = ''
        ClientSecFetchDest   = ''
        ClientSecFetchMode   = ''
        ClientSecFetchSite   = ''
        ClientSecFetchUser   = ''
        XForwardedFor        = ''
        IfModifiedSince      = ''
        Cookies              = {}
        
        for i in requestheaders:
            if i.startswith("Host: "):
                ClientTargetHost = i[6:]
            elif i.startswith("User-Agent: "):
                ClientUserAgent = i[12:]
            elif i.startswith("Content-Length: "):
                ClientContentLength = i[16:]
            elif i.startswith("Accept: "):
                ClientAcceptTypes = i[8:]
            elif i.startswith("Accept-Language: "):
                ClientAcceptLanguage = i[17:]
            elif i.startswith("Accept-Encoding: "):
                ClientAcceptEncoding = i[17:]
            elif i.startswith("Connection: "):
                ClientConnectionType = i[12:]
            elif i.startswith("Upgrade-Insecure-Requests: "):
                ClientUseHTTPS = i[27:]
            elif i.startswith("Sec-Fetch-Dest: "):
                ClientSecFetchDest = i[16:]
            elif i.startswith("Sec-Fetch-Mode: "):
                ClientSecFetchMode = i[16:]
            elif i.startswith("Sec-Fetch-Site: "):
                ClientSecFetchSite = i[16:]
            elif i.startswith("Sec-Fetch-User: "):
                ClientSecFetchUser = i[16:]
            elif i.startswith("X-Forwarded-For: "):
                XForwardedFor = i[17:]
            elif i.startswith("If-Modified-Since: "):
                IfModifiedSince = i[19:]
            elif i.startswith("Cookie: "):
                # Parse cookie header correctly into a flat dict
                cookie_str = i[8:]
                for pair in cookie_str.split("; "):
                    k = pair.split("=", 1)
                    if len(k) == 2:
                        Cookies[k[0].strip()] = k[1].strip()

        if XForwardedFor == '':
            sourceIPvisual = sourceIP
        else:
            sourceIPvisual = XForwardedFor.strip()
        
        print(sourceIPvisual + ":" + str(sourcePort) + " [" + ClientUserAgent + "] requested \"" + messages[0] + "\"")
        if any(sub in messages[0] for sub in [".env","php",".git","cgi","SDK/webLanguage"]):
            addtoblocklist(sourceIPvisual)
            return

        now = datetime.datetime.now()
        with recentConnections_lock:
            recentConnections.append([sourceIPvisual, now])
            recentConnectionsExtended.append([sourceIPvisual, now])
            recentConnections = [
                entry for entry in recentConnections
                if now <= entry[1] + datetime.timedelta(seconds=60)
            ]
            recentConnectionsExtended = [
                entry for entry in recentConnectionsExtended
                if now <= entry[1] + datetime.timedelta(seconds=200)
            ]
            rateLimitCount = {}
            rateLimitCountExtended = {}
            for entry in recentConnections:
                rateLimitCount[entry[0]] = rateLimitCount.get(entry[0], 0) + 1
            for entry in recentConnectionsExtended:
                rateLimitCountExtended[entry[0]] = rateLimitCountExtended.get(entry[0], 0) + 1

        print(rateLimitCount)
		
        if rateLimitCountExtended[sourceIPvisual] >= 200:
            addtoblocklist(sourceIPvisual)
            return

        elif rateLimitCount[sourceIPvisual] >= 100:
            responseType = "429 Too Many Requests (please stop)"
            responsecontent = b"429 Too Many Requests.\nPlease stop.\n"
            responseHeaders += b"Retry-After: 9999999999999999999 \n"
		
        elif rateLimitCount[sourceIPvisual] >= 50:
            responseType = "429 Too Many Requests"
            responsecontent = open(script_directory + "/webroot/429.html", "rb").read()
            fullRequestPath = script_directory + "/webroot/429.html"
            contentType = "text/html"
            responseHeaders += b"Retry-After: 60\n"

        elif len(messages[0]) < 10:
            responseType = "400 Bad Request"
            responsecontent = open(script_directory + "/webroot/400.html", "rb").read()
            fullRequestPath = script_directory + "/webroot/400.html"
            contentType = "text/html"

        else:
            requestType = messages[0].split()[0]

            # Validate HTTP method
            if requestType not in ALLOWED_METHODS:
                responseType = "405 Method Not Allowed"
                responsecontent = b"<h1>405 Method Not Allowed</h1>"
                fullRequestPath = ""
                contentType = "text/html"
                responseHeaders += b"Allow: GET, POST, HEAD\n"
            else:
                # URL-decode the path before sanitizing to catch encoded traversal sequences
                raw_path = (messages[0].split()[1] + "?").split("?")[0]
                decoded_path = urllib.parse.unquote(raw_path)

                # Normalize and build the candidate path, then realpath-check it
                candidate_path = os.path.realpath(script_directory + "/webroot" + decoded_path)

                with blocked_agents_lock:
                    agent_blocked = any(agent in ClientUserAgent.lower() for agent in blocked_agents)
                if agent_blocked and decoded_path != "/robots.txt":
                    responseType = "403 Forbidden"
                    responsecontent = b"<h1>403 Forbidden</h1>"
                    contentType = "text/html"

                if not candidate_path.startswith(webroot_real + os.sep) and candidate_path != webroot_real:
                    responseType = "403 Forbidden"
                    responsecontent = b"<h1>403 Forbidden</h1>"
                    fullRequestPath = ""
                    contentType = "text/html"
                else:
                    fullRequestPath = candidate_path
                    requestPath = decoded_path  # exposed to exec'd scripts via script_env

                    argumentsRaw = (messages[0].split()[1] + "?").split("?")[1]
                    arguments = argumentsRaw.split("&")
                    argumentsDict = {}
                    for i in arguments:
                        j = i.split("=")
                        if len(j) == 2:
                            argumentsDict[j[0]] = j[1]

                    if responseType == "200 OK":
                        if os.path.exists(fullRequestPath):
                            if os.path.isdir(fullRequestPath):
                                indexFiles = ["/index.html", "/index.py"]
                                for i in indexFiles:
                                    if os.path.exists(fullRequestPath + i):
                                        fullRequestPath += i
                                        break
                                else:
                                    fullRequestPath = script_directory + "/webroot/Scripts/listFiles.py"
                        if not os.path.exists(fullRequestPath):
                            responseType = "404 Not Found"
                            fullRequestPath = script_directory + "/webroot/404.html"

                        plainresponse = False
                        extensions   = [".html", ".json", ".png", ".gif", ".ico", ".jpg", ".css", ".txt", ".ttf", ".mp4"]
                        contentTypes = ["text/html", "text/json", "image/png", "image/gif", "image/x-icon", "image/jpeg", "text/css", "text/plain", "application/octet-stream", "video/mp4"]
                        for i in range(len(extensions)):
                            if fullRequestPath.endswith(extensions[i]):
                                plainresponse = True
                                contentType = contentTypes[i]
                                break

                        if plainresponse:
                            with open(fullRequestPath, "rb") as file:
                                responsecontent = file.read()
                        elif fullRequestPath.endswith(".py"):
                            with open(fullRequestPath) as script:
                                local_vars = locals()
                                exec(script.read(), globals(), local_vars)
                            responsecontent = local_vars.get("responsecontent", responsecontent)
                            responseType    = local_vars.get("responseType",    responseType)
                            responseHeaders = local_vars.get("responseHeaders", responseHeaders)
                            contentType     = local_vars.get("contentType",     contentType)
                        else:
                            responseType = "415 Unsupported Media Type"
                            contentType = ""
                            responsecontent = b""

    except Exception as e:
        print("error: ", e)
        responseType = "500 Internal Server Error"
        fullRequestPath = script_directory + "/webroot/500.html"
        contentType = "text/html"
        if os.path.exists(fullRequestPath):
            with open(fullRequestPath, "rb") as file:
                responsecontent = file.read()
        else:
            responsecontent = ("<h1 style=\"color: #a00;\">Error 500: Internal Server Error.</h1><br><p>Additionally, While handling that error, we encountered error 404. (page not found!)<br>Error: " + str(e) + "</p>").encode()

    print("Serving " + fullRequestPath + " to " + sourceIPvisual + ":" + str(sourcePort))

    if contentType != "":
        if contentType[:5] == "image":
            responseHeaders += ("Last-Modified: " + get_last_modified(fullRequestPath) + "\n").encode()
            print(IfModifiedSince)
            if IfModifiedSince != '':
                try:
                    if is_newer_than(fullRequestPath, IfModifiedSince):
                        pass
                    else:
                        responsecontent = b''
                        responseType = "304 Not Modified"
                except Exception as e:
                    print("excepted: ")
                    print(e)

        responseHeaders += ("Content-Length: " + str(len(responsecontent)) + '\n').encode()
        responseHeaders += ("Content-Type: " + contentType + "\n").encode()
        responseHeaders += b"Server: Xbox 360\n"

    response =  ("HTTP/1.1 " + responseType + "\n").encode()
    response += responseHeaders
    response += b"\n"
    response += responsecontent

    numchunks = math.ceil(len(response) / 1024) if len(response) > 0 else 1
    responsechunks = []
    for i in range(numchunks):
        responsechunks.append(response[(1024 * i):(1024 * i + 1024)])
    try:
        transferStarted = datetime.datetime.now()
        lastSentTime = datetime.datetime.now()
        for i in range(len(responsechunks)):
            connectionSocket.send(responsechunks[i])
            if datetime.datetime.now() >= transferStarted + datetime.timedelta(seconds=10):
                if datetime.datetime.now() >= lastSentTime + datetime.timedelta(seconds=0.5):
                    lastSentTime = datetime.datetime.now()
                    print("Sending chunk " + str(i + 1) + " of " + str(numchunks) + " to " + sourceIP + ":" + str(sourcePort) + " for file \"" + fullRequestPath + "\"")
    except BrokenPipeError:
        print("Broken Pipe!")
    except ConnectionResetError:
        print("Connection Reset!")
    except TimeoutError:
        print("Send timed out!")
    print("Served " + fullRequestPath + " to " + sourceIPvisual + ":" + str(sourcePort))

    connectionSocket.close()


while running:
    print('Waiting for a connection...')
    connectionSocket, addr = serverSocket.accept()
    t = threading.Thread(target=handle_connection, args=(connectionSocket, addr))
    t.daemon = True
    t.start()

print("Server Stopped.")
serverSocket.close()
