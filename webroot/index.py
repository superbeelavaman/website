page = ""
args = ""
responseType = "200 OK"
contentType = "text/html"
for i in argumentsDict:
    argumentsDict[i] = urllib.parse.unquote(argumentsDict[i])
if "p" in argumentsDict:
    path = argumentsDict["p"]

    content_real = os.path.realpath(script_directory + "/webroot/content")
    filePath = os.path.realpath(script_directory + "/webroot/content/" + path)
    if not filePath.startswith(content_real + os.sep) and filePath != content_real:
        responseType = "403 Forbidden"
        responsecontent = b"<h1>403 Forbidden</h1>"
        contentType = "text/html"
    else:
        if "v" in argumentsDict and argumentsDict["v"] in ("new", "old"):
            version = argumentsDict["v"]
        else:
            version = "new"

        if os.path.exists(filePath):
            if os.path.isdir(filePath):
                if os.path.exists(filePath + "/" + version + "index.html"):
                    filePath += ("/" + version + "index.html")
                else:
                    filePath += "/index.html"
            if version == "new":
                page = open(script_directory + "/webroot/Templates/index.html").read()
                header = open(script_directory + "/webroot/Templates/header.html").read()
            elif version == "old":
                page = open(script_directory + "/webroot/Templates/oldindex.html").read()
                header = open(script_directory + "/webroot/Templates/oldheader.html").read()
            page = page.replace("<!--header-->", header)

            # Resolve session cookie and build userbar before other replacements,
            # as the logged-out userbar contains <!--args--> and <!--path--> itself
            session_token = Cookies.get("session", "")
            if session_token:
                session_status, session_user = userManagement.validate_session(session_token)
            else:
                session_status = "fail"
                session_user = ""

            if session_status == "success":
                pfp_base    = os.path.realpath(script_directory + "/webroot/Images/profileimages")
                pfp_real_gif = os.path.realpath(script_directory + "/webroot/Images/profileimages/" + session_user + ".gif")
                pfp_real_jpg = os.path.realpath(script_directory + "/webroot/Images/profileimages/" + session_user + ".jpg")
                if pfp_real_gif.startswith(pfp_base + os.sep) and os.path.exists(pfp_real_gif):
                    pfp_src = "/Images/profileimages/" + html.escape(session_user) + ".gif"
                elif pfp_real_jpg.startswith(pfp_base + os.sep) and os.path.exists(pfp_real_jpg):
                    pfp_src = "/Images/profileimages/" + html.escape(session_user) + ".jpg"
                else:
                    pfp_src = "/Images/default_pfp.gif"
                userbar = (
                    '<span class="nav-button" style="float:right; margin-right:0;">'
                    '<a href="/logout/">'
                    '<div class="nav-content">Logout</div>'
                    '</a></span>'
                    '<span class="nav-button" style="float:right; margin-right:0;">'
                    '<div class="nav-content">'
                    '<img src="' + pfp_src + '" alt="Profile Picture" style="height:100%; vertical-align:middle;">'
                    ' Logged in as ' + html.escape(session_user) +
                    '</div></span>'
                )
            else:
                userbar = (
                    '<span class="nav-button" style="float:right; margin-right:0;">'
                    '<a href="/?<!--args-->returnto=<!--path-->&p=/login/">'
                    '<div class="nav-content">Login</div>'
                    '</a></span>'
                )

            page = page.replace("<!--userbar-->", userbar)

            content = open(filePath).read()
            title       = content.split("Title: ")[1].split("<br>\n")[0]
            icon        = content.split("Icon: ")[1].split("<br>\n")[0]
            style       = content.split("Style: ")[1].split("<br>\n")[0]
            description = content.split("Description: ")[1].split("<br>\n")[0]
            author      = content.split("Author: ")[1].split("<br>\n")[0]
            content     = content.split("Content: \n")[1]
            updateddate = get_last_modified(filePath)

            if version == "old":
                style = "/styles/oldmain.css"
            if "theme" in argumentsDict:
                theme = argumentsDict["theme"]
                if os.path.exists(script_directory + "/webroot/styles/" + version + theme + ".css"):
                    style = "/styles/" + version + theme + ".css"
                    args += "theme=" + theme + "&"
                page = page.replace("<!--theme" + theme + "-->", " selected")
            page = re.sub('<!--theme.*?-->', '', page, flags=re.DOTALL)



            head = "<title>" + title + """</title>
            <link rel=\"shortcut icon\" type=\"image/x-icon\" href=\"""" + icon + """\">
            <link rel=\"icon\" type=\"image/x-icon\" href=\"""" + icon + """\">
            <link rel=\"stylesheet\" type=\"text/css\" href=\"/styles/newCommon.css\">
            <link rel=\"stylesheet\" type=\"text/css\" href=\"""" + html.escape(style) + """\">
            <meta charset=\"UTF-8\">
            <meta name=\"description\" content=\"""" + description + """\">
            <meta name=\"author\" content=\"""" + author + """\">
            <meta property=\"og:title\" content=\"""" + title + """\">
            <meta property=\"og:description\" content=\"""" + description + """\">
            <meta property=\"og:type\" content=\"website\">
            <meta property=\"twitter:title\" content=\"""" + title + """\">
            <meta property=\"twitter:description\" content=\"""" + description + """\">
            """

            args += "v=" + version + "&"

            formargs = ""
            for i in argumentsDict:
                formargs += "<input type=\"hidden\" name=\"" + html.escape(i) + "\" value=\"" + html.escape(argumentsDict[i]) + "\">"

            errortext = ""
            if "errortext" in argumentsDict:
                errortext = "<p class=\"error\">" + html.escape(argumentsDict["errortext"]) + "</p>"

            page = page.replace("<!--content-->", content)
            page = page.replace("<!--head-->", head)
            page = page.replace("<!--path-->", urllib.parse.quote(path, safe=''))
            page = page.replace("<!--args-->", args)
            page = page.replace("<!--formargs-->", formargs)
            page = page.replace("<!--errortext-->", errortext)
            page = page.replace("<!--updateddate-->", updateddate)
            page = page.replace("\n", "")
            page = page.replace("    ", "")

        else:
            responseType = "404 Not Found"
            fullRequestPath = script_directory + "/webroot/404.html"
            page = open(fullRequestPath).read()

        responsecontent = page.encode()

else:
    responseType = "301 Moved Permanently"
    responseHeaders += "Location: /?p=/\n".encode()
    page = "<html><head><title>Redirecting...</title><meta http-equiv=\"refresh\" content=\"0; url='/?p=/'\" /></head><body><p><a href=\"/?p=/\">Redirect</a></p></body></html>"
    responsecontent = page.encode()
