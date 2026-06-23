page = ""
responseType = "200 OK"
contentType = "text/html"

if "p" in argumentsDict:
    path = urllib.parse.unquote(argumentsDict["p"])

    webroot_real = os.path.realpath(script_directory + "/webroot")
    filePath = os.path.realpath(script_directory + "/webroot/" + path)
    if not filePath.startswith(webroot_real + os.sep) and filePath != webroot_real:
        responseType = "403 Forbidden"
        contentType = "text/html"
        responsecontent = b"<h1>403 Forbidden</h1>"
    elif os.path.exists(filePath):
        if os.path.isdir(filePath):
            filesList = list(os.scandir(filePath))
            page = open(script_directory + "/webroot/Templates/fileList.html").read()
            page = page.replace("<!--dir-->", html.escape(path))
            listText = "<li>Folder: <a href=\"/raw/?p=" + html.escape(os.path.dirname(path)) + "\">..</a></li>"
            for i in filesList:
                temp = "File: "
                if os.path.isdir(filePath + i.name):
                    temp = "Folder: "
                link = path.rstrip("/") + "/" + i.name
                listText += ("<li>" + temp + "<a href=\"/raw/?p=" + html.escape(link) + "\">" + html.escape(i.name) + "</a></li>")
            page = page.replace("<!--fileList-->", listText)
            responsecontent = page.encode()
        else:
            contentType = magic.Magic(mime=True).from_file(filePath)
            if contentType in (contentTypes + ["application/x-python-code", "text/x-python"]):
                if contentType.startswith("text"):
                    contentType = "text/plain"
                responsecontent = open(filePath, "rb").read()
            else:
                responseType = "415 Unsupported Media Type"
                contentType = ""
                responsecontent = b""
    else:
        responseType = "404 Not Found"
        fullRequestPath = script_directory + "/webroot/404.html"
        responsecontent = open(fullRequestPath, "rb").read()
else:
    responseType = "400 Bad Request"
    fullRequestPath = script_directory + "/webroot/400.html"
    responsecontent = open(fullRequestPath, "rb").read()
