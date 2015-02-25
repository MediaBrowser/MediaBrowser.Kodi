import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import httplib
import hashlib
import StringIO
import gzip
import sys
import inspect
import json as json
from random import randrange
from uuid import uuid4 as uuid4
from ClientInformation import ClientInformation
import encodings
import time

class DownloadUtils():

    logLevel = 0
    addonSettings = None
    getString = None
    LogCalls = False
    TrackLog = ""
    TotalUrlCalls = 0

    def __init__(self, *args):
        
        # Internal variables
        self.window = xbmcgui.Window( 10000 )
        self.addonId = ClientInformation().getAddonId()
        self.addon = xbmcaddon.Addon(id=self.addonId)
        self.addonName = self.addon.getAddonInfo('name').upper()
        self.getString = self.addon.getLocalizedString

        # Verify and set log level
        level = self.addon.getSetting('logLevel')        
        self.logLevel = 0
        
        if level != None:
            self.logLevel = int(level)
        
        if self.logLevel == 2:
            self.LogCalls = True


    def logMsg(self, msg, level = 1):
        
        className = self.__class__.__name__
        addonName = self.addonName
        
        if self.logLevel >= level:
            try:
                xbmc.log("%s %s -> %s" % (addonName, className, str(msg)))
            except UnicodeEncodeError:
                try:
                    xbmc.log("%s %s -> %s" % (addonName, className, str(msg.encode('utf-8'))))
                except: pass


    def getServer(self):

        addon = self.addon
        host = addon.getSetting('ipaddress')
        port = addon.getSetting('port')

        return host + ":" + port
    
    
    def getUserId(self, suppress=True):

        WINDOW = self.window
        addon = self.addon
        getString = self.getString
        username = addon.getSetting('username')
        userId = WINDOW.getProperty('userid' + username)

        if (userId != None and userId != ""):
            self.logMsg("Returning saved UserID: %s Username: %s" % (userId, username))
            return userId
    
        self.logMsg("Looking for username: " + username)

        authOk = self.authenticate()

        if authOk == "":
            if suppress == False:
                xbmcgui.Dialog().ok(getString(30044), getString(30044))
            return ""

        if (userId == "" and suppress == False):
            xbmcgui.Dialog().ok(getString(30045), getString(30045))

        self.logMsg("userid: " + userId)         
        self.postcapabilities()
        
        return userId
        
        
    def postcapabilities(self):
        
        # Set Capabilities
        server = self.getServer()
        deviceId = ClientInformation().getMachineId()

        self.logMsg("postcapabilities called")
        
        # get session id
        url = "http://" + server + "/mediabrowser/Sessions?DeviceId=" + deviceId + "&format=json"
        self.logMsg("Session URL : " + url);
        jsonData = self.downloadUrl(url)
        self.logMsg("Session JsonData : " + jsonData)
        result = json.loads(jsonData)
        self.logMsg("Session JsonData : " + str(result))
        sessionId = result[0].get("Id")
        self.logMsg("Session Id : " + str(sessionId))
        
        # post capability data
        playableMediaTypes = "Audio,Video,Photo"
        supportedCommands = "Play,Playstate,DisplayContent,GoHome,SendString,GoToSettings,DisplayMessage,PlayNext"
        
        url = "http://" + server + "/mediabrowser/Sessions/Capabilities?Id=" + sessionId + "&PlayableMediaTypes=" + playableMediaTypes + "&SupportedCommands=" + supportedCommands + "&SupportsMediaControl=True"
        
        postData = {}
        #postData["Id"] = sessionId;
        #postData["PlayableMediaTypes"] = "Video";
        #postData["SupportedCommands"] = "MoveUp";
        stringdata = json.dumps(postData)
        self.logMsg("Capabilities URL : " + url);
        self.logMsg("Capabilities Data : " + stringdata)
        
        self.downloadUrl(url, postBody=stringdata, type="POST")
        

    def authenticate(self): 
        
        WINDOW = self.window
        addon = self.addon
        server = self.getServer()
        token = WINDOW.getProperty('AccessToken' + addon.getSetting('username'))

        # Verify if there's an access token saved for the user
        if (token != None and token != ""):
            self.logMsg("Returning saved AccessToken for user: %s Token: %s" % (addon.getSetting('username'), token))
            return token
        
        # Verify if there's server information saved
        if len(server) < 2:
            return ""
        
        # If there's no token saved, authenticate user  
        url = "http://" + server + "/mediabrowser/Users/AuthenticateByName?format=json"
    
        clientInfo = ClientInformation()
        headers = clientInfo.getHeader()
        
        sha1 = hashlib.sha1(addon.getSetting('password'))
        sha1 = sha1.hexdigest()
        
        accessToken = addon.getSetting('token')
        
        if accessToken == "":
            messageData = "username=" + addon.getSetting('username') + "&password=" + sha1
            resp = self.downloadUrl(url, postBody=messageData, type="POST", authenticate=False, suppress=True)
    
            try:
                result = json.loads(resp)
                accessToken = result.get('AccessToken')
            except:
                pass
    
            if accessToken != None:
                self.logMsg("User Authenticated : " + accessToken)
                addon.setSetting('token', accessToken)
                WINDOW.setProperty('AccessToken' + addon.getSetting('username'), accessToken)
                WINDOW.setProperty('userid' + addon.getSetting('username'), result.get('User').get('Id'))
                addon.setSetting('userid', result.get('User').get('Id'))
                
                return accessToken
    
            else:
                self.logMsg("User NOT Authenticated")
                WINDOW.setProperty('AccessToken' + addon.getSetting('username'), "")
                
                return ""
        else:
            self.logMsg("User already authenticated: " + accessToken)
            WINDOW.setProperty('AccessToken' + addon.getSetting('username'), accessToken)
            WINDOW.setProperty('userid' + addon.getSetting('username'), addon.getSetting('userid'))
            return accessToken


    def getArtwork(self, data, type, index = "0", userParentInfo = False):

        addon = self.addon
        id = data.get("Id")
        getSeriesData = False
        userData = data.get("UserData") 

        if type == "tvshow.poster": # Change the Id to the series to get the overall series poster
            if data.get("Type") == "Season" or data.get("Type")== "Episode":
                id = data.get("SeriesId")
                getSeriesData = True
        elif type == "poster" and data.get("Type") == "Episode" and addon.getSetting('useSeasonPoster')=='true': # Change the Id to the Season to get the season poster
            id = data.get("SeasonId")
        if type == "poster" or type == "tvshow.poster": # Now that the Ids are right, change type to MB3 name
            type="Primary"
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Primary2" and type != "Primary3" and type != "Primary4" and type != "Thumb" and type != "Banner" and type!="Thumb3":
                id = data.get("SeriesId")
                getSeriesData = True
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary" and type != "Primary2" and type != "Primary3" and type != "Primary4":
                id = data.get("SeriesId")
                getSeriesData = True
            if type =="Primary2" or type=="Primary3" or type=="Primary4":
                id = data.get("SeasonId")
                getSeriesData = True
                if  data.get("SeasonUserData") != None:
                    userData = data.get("SeasonUserData")
        if id == None:
            id=data.get("Id")
                
        imageTag = "e3ab56fe27d389446754d0fb04910a34" # a place holder tag, needs to be in this format
        originalType = type
        if type == "Primary2" or type == "Primary3" or type == "Primary4" or type=="SeriesPrimary":
            type = "Primary"
        if type == "Backdrop2" or type=="Backdrop3" or type=="BackdropNoIndicators":
            type = "Backdrop"
        if type == "Thumb2" or type=="Thumb3":
            type = "Thumb"
        if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
            imageTag = data.get("ImageTags").get(type)   

        if (data.get("Type") == "Episode" or data.get("Type") == "Season") and type=="Logo":
            imageTag = data.get("ParentLogoImageTag")
        if (data.get("Type") == "Episode" or data.get("Type") == "Season") and type=="Art":
            imageTag = data.get("ParentArtImageTag")
        if (data.get("Type") == "Episode") and originalType=="Thumb3":
            imageTag = data.get("SeriesThumbImageTag")
        if (data.get("Type") == "Season") and originalType=="Thumb3" and imageTag=="e3ab56fe27d389446754d0fb04910a34" :
            imageTag = data.get("ParentThumbImageTag")
            id = data.get("SeriesId")
     
        query = ""
        height = "10000"
        width = "10000"
        played = "0"
        totalbackdrops = 0

        if addon.getSetting('showArtIndicators')=='true': # add watched, unplayedcount and percentage played indicators to posters
            if (originalType =="Primary" or  originalType =="Backdrop" or  originalType =="Banner") and data.get("Type") != "Episode":
                if originalType =="Backdrop" and index == "0" and data.get("BackdropImageTags") != None:
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)

            elif originalType =="Primary2":
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                    height = "338"
                    width = "226"
                    
            elif originalType =="Primary3" or originalType == "SeriesPrimary":
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                   
            
            elif originalType =="Primary4":
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                    height = "270"
                    width = "180"    
                    
            elif type =="Primary" and data.get("Type") == "Episode":
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                    height = "410"
                    width = "770"
                                   
                    
            elif originalType =="Backdrop2" or originalType =="Thumb2" and data.get("Type") != "Episode":
                if originalType =="Backdrop2" and data.get("BackdropImageTags") != None: 
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                    height = "370"
                    width = "660"      
                    
            elif originalType =="Backdrop3" or originalType =="Thumb3" and data.get("Type") != "Episode":
                if originalType =="Backdrop3" and data.get("BackdropImageTags") != None:
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and addon.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)

                    if(userData != None and userData.get("Played") == True and addon.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and addon.getSetting('showPlayedPrecentageIndicators')=='true':
                        played = str(PlayedPercentage)
                        
                    height = "910"
                    width = "1620"                        
        
        if originalType =="BackdropNoIndicators" and index == "0" and data.get("BackdropImageTags") != None:
            totalbackdrops = len(data.get("BackdropImageTags"))
            if totalbackdrops != 0:
                index = str(randrange(0,totalbackdrops))
        # use the local image proxy server that is made available by this addons service
        
        server = self.getServer()
        
        if addon.getSetting('compressArt')=='true':
            query = query + "&Quality=90"
        
        if imageTag == None:
            imageTag = "e3ab56fe27d389446754d0fb04910a34"
        artwork = "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + index + "/" + imageTag + "/original/" + width + "/" + height + "/" + played + "?" + query
        if addon.getSetting('disableCoverArt')=='true':
            artwork = artwork + "&EnableImageEnhancers=false"
        
        self.logMsg("getArtwork : " + artwork, level=2)
        
        # do not return non-existing images
        if (    (type!="Backdrop" and imageTag=="e3ab56fe27d389446754d0fb04910a34") |  #Remember, this is the placeholder tag, meaning we didn't find a valid tag
                (type=="Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) | 
                (type=="Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)                
                ):
            if type != "Backdrop" or (type=="Backdrop" and getSeriesData==True and data.get("ParentBackdropImageTags") == None) or (type=="Backdrop" and getSeriesData!=True):
                artwork=''        
        
        return artwork
        
    
    def getUserArtwork(self, data, type, index = "0"):

        id = data.get('Id')
        server = self.getServer()

        artwork = "http://" + server + "/mediabrowser/Users/" + str(id) + "/Images/" + type  + "?Format=original"
       
        return artwork
        

    def imageUrl(self, id, type, index, width, height):
    
        server = self.getServer()
        
        return "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + str(index) + "/e3ab56fe27d389446754d0fb04910a34/original/" + str(width) + "/" + str(height) + "/0"
    
    
    def getAuthHeader(self, authenticate=True):
        
        clientInfo = ClientInformation()
        headers = clientInfo.getHeader()
        
        if authenticate == False:  
            return headers
        
        else:
            userid = self.getUserId()
            headers = clientInfo.getHeader()
            authToken = self.authenticate()

            return headers
        
        
    def downloadUrl(self, url, suppress=False, postBody=None, type="GET", popup=0, authenticate=True ):
        
        WINDOW = self.window
        addon = self.addon
        getString = self.getString

        self.logMsg("== ENTER: getURL ==")
        
        self.TotalUrlCalls = self.TotalUrlCalls + 1
        if(self.LogCalls):
            stackString = ""
            for f in inspect.stack():
                stackString = stackString + "\r - " + str(f)
            self.TrackLog = self.TrackLog + "HTTP_API_CALL : " + url + stackString + "\r"
            
        link = ""
        try:
            if url[0:4] == "http":
                serversplit = 2
                urlsplit = 3
            else:
                serversplit = 0
                urlsplit = 1

            server = url.split('/')[serversplit]
            urlPath = "/"+"/".join(url.split('/')[urlsplit:])

            self.logMsg("DOWNLOAD_URL = " + url)
            self.logMsg("server = "+str(server), level=2)
            self.logMsg("urlPath = "+str(urlPath), level=2)
            
            conn = httplib.HTTPConnection(server, timeout=20)
            
            head = self.getAuthHeader(authenticate)
            self.logMsg("HEADERS : " + str(head), level=1)

            if(postBody != None):
                head["Content-Type"] = "application/x-www-form-urlencoded"
                head["Content-Length"] = str(len(postBody))
                self.logMsg("POST DATA : " + postBody)
                conn.request(method=type, url=urlPath, body=postBody, headers=head)
            else:
                conn.request(method=type, url=urlPath, headers=head)

            tries=0
            while tries<=10:
                try:
                    data = conn.getresponse()
                    break
                except:
                    xbmc.sleep(1000)
                    tries+=1
            if tries==11:
                data = conn.getresponse()
            
            self.logMsg("GET URL HEADERS : " + str(data.getheaders()), level=2)

            contentType = "none"
            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                self.logMsg("Data Len Before : " + str(len(retData)), level=2)
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    link = gzipper.read()
                else:
                    link = retData
                self.logMsg("Data Len After : " + str(len(link)), level=2)
                self.logMsg("====== 200 returned =======", level=2)
                self.logMsg("Content-Type : " + str(contentType), level=2)
                self.logMsg(link, level=2)
                self.logMsg("====== 200 finished ======", level=2)

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) == 401:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                xbmc.log(error)
                addon.setSetting('token', "")
                addon.setSetting('userid', "")
                
                timeStamp = WINDOW.getProperty("XBMB3C_LAST_USER_ERROR")
                if(timeStamp == None or timeStamp == ""):
                    timeStamp = "0"
                    
                if((int(timeStamp) + 10) < int(time.time())):
                    xbmcgui.Dialog().ok(getString(30135), getString(30044))
                    WINDOW.setProperty("XBMB3C_LAST_USER_ERROR", str(int(time.time())))
                
                try: conn.close()
                except: pass
                return ""
                
            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                xbmc.log(error)
                if suppress is False:
                    if popup == 0:
                        xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                    else:
                        xbmcgui.Dialog().ok(getString(30135),server)
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            xbmc.log(error)
            if suppress is False:
                xbmc.log("Suppress is False, displaying user message: popup=" + str(popup))
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(: URL error: Unable to connect to server,)")
                else:
                    xbmcgui.Dialog().ok("",getString(30204))
                raise
        else:
            try: conn.close()
            except: pass

        return link
        
        
    def __del__(self):
        return
        # xbmc.log("\rURL_REQUEST_REPORT : Total Calls : " + str(self.TotalUrlCalls) + "\r" + self.TrackLog)
