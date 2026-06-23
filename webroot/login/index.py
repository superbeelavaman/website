page = ""
args = ""
responseType = "200 OK"
contentType = "text/html"

if "username" in argumentsDict and "password" in argumentsDict:
    username = urllib.parse.unquote(argumentsDict["username"])
    password = urllib.parse.unquote(argumentsDict["password"])

    # Validate and sanitize returnpath
    returnpath = "/"
    returnto = ""
    if "returnto" in argumentsDict:
        candidate = urllib.parse.unquote(argumentsDict["returnto"])
        resolved = os.path.realpath(script_directory + "/webroot" + candidate)
        webroot_real = os.path.realpath(script_directory + "/webroot")
        if resolved.startswith(webroot_real + os.sep) or resolved == webroot_real:
            returnpath = candidate
        returnto = "&returnto=" + urllib.parse.quote(returnpath)

    status, result = userManagement.login(username, password)

    if status == "success":
        token = result
        responseHeaders += ("Set-Cookie: session=" + token + "; Path=/; HttpOnly; SameSite=Strict\n").encode()
        url = "/?p=" + urllib.parse.quote(returnpath)
    else:
        url = "/?p=/login/" + returnto + "&errortext=" + urllib.parse.quote("Invalid username or password.")

    page = ("<html><head><title>Redirecting...</title>"
            "<meta http-equiv=\"refresh\" content=\"0; url='" + html.escape(url) + "'\" />"
            "</head><body><p><a href=\"" + html.escape(url) + "\">Redirect</a></p></body></html>")
else:
    responseType = "400 Bad Request"
    fullRequestPath = script_directory + "/webroot/400.html"
    page = open(fullRequestPath).read()

# Clear sensitive locals
username = ""
password = ""

responsecontent = page.encode()
