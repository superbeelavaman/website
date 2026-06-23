responseType = "200 OK"
contentType = "text/html"

session_token = Cookies.get("session", "")
if session_token:
    userManagement.logout(session_token)

responseHeaders += b"Set-Cookie: session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict\n"

returnpath = "/"
if "returnto" in argumentsDict:
    candidate = urllib.parse.unquote(argumentsDict["returnto"])
    resolved = os.path.realpath(script_directory + "/webroot" + candidate)
    webroot_real = os.path.realpath(script_directory + "/webroot")
    if resolved.startswith(webroot_real + os.sep) or resolved == webroot_real:
        returnpath = candidate

url = "/?p=" + urllib.parse.quote(returnpath)
responseType = "302 Found"
responseHeaders += ("Location: " + url + "\n").encode()
responsecontent = (
    "<html><head><title>Redirecting...</title>"
    "<meta http-equiv=\"refresh\" content=\"0; url='" + html.escape(url) + "'\" />"
    "</head><body><p><a href=\"" + html.escape(url) + "\">Redirect</a></p></body></html>"
).encode()
