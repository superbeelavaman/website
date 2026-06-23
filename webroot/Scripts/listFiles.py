webroot_real = os.path.realpath(script_directory + "/webroot")
folderPath = os.path.realpath(script_directory + "/webroot" + requestPath)

if not folderPath.startswith(webroot_real + os.sep) and folderPath != webroot_real:
    responseType = "403 Forbidden"
    contentType = "text/html"
    responsecontent = b"<h1>403 Forbidden</h1>"
else:
    filesList = list(os.scandir(folderPath))
    responseType = "200 OK"
    contentType = "text/html"

    template = open(script_directory + "/webroot/Templates/fileList.html").read()
    template = template.replace("<!--dir-->", html.escape(requestPath))
    listText = "<li>Folder: <a href=\"..\">..</a></li>"
    for i in filesList:
        temp = "File: "
        funnynameorsomethingidk = i.name
        if os.path.isdir(folderPath + "/" + funnynameorsomethingidk):
            temp = "Folder: "
            funnynameorsomethingidk += "/"
        link = requestPath + "/" + funnynameorsomethingidk
        link = link.replace("//", "/")
        if link.endswith(".py"):
            link = "/raw/?p=" + html.escape(link)
        else:
            link = html.escape(link)
        listText += ("<li>" + temp + "<a href='" + link + "'>" + html.escape(i.name) + "</a></li>")
    template = template.replace("<!--fileList-->", listText)
    responsecontent = template.encode()
