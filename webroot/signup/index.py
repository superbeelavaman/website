page = ""
args = ""
responseType = "200 OK"
contentType = "text/html"

if "username" in argumentsDict and "password" in argumentsDict and "password2" in argumentsDict:
    username = urllib.parse.unquote(argumentsDict["username"])
    password = urllib.parse.unquote(argumentsDict["password"])
    password2 = urllib.parse.unquote(argumentsDict["password2"])

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

    error = ""
    if password != password2:
        error = "Passwords do not match."
    elif username == password:
        error = "Username cannot match password."

    if error == "":
        status, reason = userManagement.register(username, password)
        if status == "fail":
            error = reason

    if error == "":
        # Auto-login after successful registration
        status, token = userManagement.login(username, password)
        if status == "success":
            responseHeaders += ("Set-Cookie: session=" + token + "; Path=/; HttpOnly; SameSite=Strict\n").encode()
        url = "/?p=" + urllib.parse.quote(returnpath)
    else:
        url = "/?p=/signup/" + returnto + "&errortext=" + urllib.parse.quote(error)

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
password2 = ""

responsecontent = page.encode()
