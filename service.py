import xbmc
import xbmcgui
import xbmcaddon
import urllib
import httplib
import os
import time
import requests

import threading
import json
from datetime import datetime
import xml.etree.ElementTree as xml

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import mimetypes
from threading import Thread
from SocketServer import ThreadingMixIn
from urlparse import parse_qs
from urllib import urlretrieve

from random import randint
import random
import urllib2

__cwd__ = xbmcaddon.Addon(id='plugin.video.xbmb3c').getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__language__     = __addon__.getLocalizedString
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)
base_window = xbmcgui.Window( 10000 )

import websocket
from uuid import getnode as get_mac

_MODE_BASICPLAY=12

def getMachineId():
    return "%012X"%get_mac()
    
def getVersion():
    return "0.8.5"

def getAuthHeader():
    addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    deviceName = addonSettings.getSetting('deviceName')
    deviceName = deviceName.replace("\"", "_") # might need to url encode this as it is getting added to the header and is user entered data
    txt_mac = getMachineId()
    version = getVersion()  
    userid = xbmcgui.Window( 10000 ).getProperty("userid")
    authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
    headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}
    xbmc.log("XBMB3C Authentication Header : " + str(headers))
    return headers 

#################################################################################################
# WebSocket Client thread
#################################################################################################

class WebSocketThread(threading.Thread):

    logLevel = 0
    client = None
    
    def playbackStarted(self, itemId):
        if(self.client != None):
            xbmc.log( "XBMB3C Service WebSocket -> Sending Playback Started" )
            messageData = {}
            messageData["MessageType"] = "PlaybackStart"
            messageData["Data"] = itemId + "|true|audio,video"
            messageString = json.dumps(messageData)
            xbmc.log(messageString)
            self.client.send(messageString)
        else:
            xbmc.log( "XBMB3C Service WebSocket -> Sending Playback Started NO Object ERROR" )
            
    def playbackStopped(self, itemId, ticks):
        if(self.client != None):
            xbmc.log( "XBMB3C Service WebSocket -> Sending Playback Stopped" )
            messageData = {}
            messageData["MessageType"] = "PlaybackStopped"
            messageData["Data"] = itemId + "|" + str(ticks)
            messageString = json.dumps(messageData)
            xbmc.log(messageString)
            self.client.send(messageString)
        else:
            xbmc.log( "XBMB3C Service WebSocket -> Sending Playback Stopped NO Object ERROR" )
            
    def sendProgressUpdate(self, itemId, ticks):
        if(self.client != None):
            #xbmc.log( "XBMB3C Service WebSocket -> Sending Progress Update" )
            messageData = {}
            messageData["MessageType"] = "PlaybackProgress"
            messageData["Data"] = itemId + "|" + str(ticks) + "|false|false"
            messageString = json.dumps(messageData)
            xbmc.log(messageString)
            self.client.send(messageString)
        else:
            xbmc.log( "XBMB3C Service WebSocket -> Sending Progress Update NO Object ERROR" )
            
    def stopClient(self):
        # stopping the client is tricky, first set keep_running to false and then trigger one 
        # more message by requesting one SessionsStart message, this causes the 
        # client to receive the message and then exit
        if(self.client != None):
            xbmc.log( "XBMB3C Service WebSocket -> Stopping Client" )
            self.client.keep_running = False
            messageData = {}
            messageData["MessageType"] = "SessionsStart"
            messageData["Data"] = "300,0"
            messageString = json.dumps(messageData)
            xbmc.log(messageString)
            self.client.send(messageString)
        else:
            xbmc.log( "XBMB3C Service WebSocket -> Stopping Client NO Object ERROR" )
            
    def on_message(self, ws, message):
        xbmc.log( "XBMB3C Service WebSocket -> message : " + str(message) )
        result = json.loads(message)
        
        messageType = result.get("MessageType")
        playCommand = result.get("PlayCommand")
        data = result.get("Data")
        
        if(messageType != None and messageType == "Play" and data != None):
            itemIds = data.get("ItemIds")
            playCommand = data.get("PlayCommand")
            if(playCommand != None and playCommand == "PlayNow"):
            
                startPositionTicks = data.get("StartPositionTicks")
                xbmc.log("XBMB3C Service WebSocket -> Playing Media With ID : " + itemIds[0])
                
                addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
                mb3Host = addonSettings.getSetting('ipaddress')
                mb3Port = addonSettings.getSetting('port')                   
                
                url =  mb3Host + ":" + mb3Port + ',;' + itemIds[0]
                if(startPositionTicks == None):
                    url  += ",;" + "-1"
                else:
                    url  += ",;" + str(startPositionTicks)
                    
                playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
                playUrl = playUrl.replace("\\\\","smb://")
                playUrl = playUrl.replace("\\","/")                
                
                xbmc.Player().play(playUrl)
                
        elif(messageType != None and messageType == "Playstate"):
            command = data.get("Command")
            if(command != None and command == "Stop"):
                xbmc.log("XBMB3C Service WebSocket -> Playback Stopped")
                xbmc.executebuiltin('xbmc.activatewindow(10000)')
                xbmc.Player().stop()
                
            if(command != None and command == "Seek"):
                seekPositionTicks = data.get("SeekPositionTicks")
                xbmc.log("XBMB3C Service WebSocket -> Playback Seek : " + str(seekPositionTicks))
                seekTime = (seekPositionTicks / 1000) / 10000
                xbmc.Player().seekTime(seekTime)

    def on_error(self, ws, error):
        xbmc.log( "XBMB3C Service WebSocket -> error : " + str(error) )

    def on_close(self, ws):
        xbmc.log( "XBMB3C Service WebSocket -> closed" )

    def on_open(self, ws):
        machineId = getMachineId()
        version = getVersion()
        messageData = {}
        messageData["MessageType"] = "Identity"
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        deviceName = addonSettings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")
    
        messageData["Data"] = "XBMC|" + machineId + "|" + version + "|" + deviceName
        messageString = json.dumps(messageData)
        xbmc.log( "XBMB3C Service WebSocket -> opened : " + str(messageString))
        ws.send(messageString)
        
    def getWebSocketPort(self, host, port):
        
        userUrl = "http://" + host + ":" + port + "/mediabrowser/System/Info?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()              
        except Exception, e:
            xbmc.log("WebSocketThread getWebSocketPort urlopen : " + str(e) + " (" + userUrl + ")")
            return -1

        result = json.loads(jsonData)     

        wsPort = result.get("WebSocketPortNumber")
        if(wsPort != None):
            return wsPort
        else:
            return -1

    def run(self):
    
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        xbmc.log("XBMB3C Log Level : " + str(self.logLevel))
        
        if(self.logLevel >= 1):
            websocket.enableTrace(True)        

        wsPort = self.getWebSocketPort(mb3Host, mb3Port);
        xbmc.log( "XBMB3C Service WebSocket -> WebSocketPortNumber = " + str(wsPort))
        if(wsPort == -1):
            xbmc.log( "XBMB3C Service WebSocket -> Could not retrieve WebSocket port, can not run WebScoket Client")
            return
        
        #Make a call to /System/Info. WebSocketPortNumber is the port hosting the web socket.
        webSocketUrl = "ws://" +  mb3Host + ":" + str(wsPort) + "/mediabrowser"
        xbmc.log( "XBMB3C Service WebSocket -> WebSocket URL : " + webSocketUrl)
        self.client = websocket.WebSocketApp(webSocketUrl,
                                    on_message = self.on_message,
                                    on_error = self.on_error,
                                    on_close = self.on_close)
        self.client.on_open = self.on_open
        self.client.run_forever()
        xbmc.log( "XBMB3C Service WebSocket -> Exited")

newWebSocketThread = WebSocketThread()
newWebSocketThread.start()

#################################################################################################
# end WebSocket Client thread
#################################################################################################

#################################################################################################
# menu item loader thread
# this loads the favourites.xml and sets the windows props for the menus to auto display in skins
#################################################################################################

class LoadMenuOptionsThread(threading.Thread):

    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Load Menu -> " + msg) 
    
    def run(self):
        xbmc.log("LoadMenuOptionsThread Started")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)    
        
        lastFavPath = ""
        favourites_file = os.path.join(xbmc.translatePath('special://profile'), "favourites.xml")
        self.loadMenuOptions(favourites_file)
        lastFavPath = favourites_file
        
        try:
            lastModLast = os.stat(favourites_file).st_mtime
        except:
            lastModLast = 0;
        
        
        while (xbmc.abortRequested == False):
            
            favourites_file = os.path.join(xbmc.translatePath('special://profile'), "favourites.xml")
            try:
                lastMod = os.stat(favourites_file).st_mtime
            except:
                lastMod = 0;
            
            if(lastFavPath != favourites_file or lastModLast != lastMod):
                self.loadMenuOptions(favourites_file)
                
            lastFavPath = favourites_file
            lastModLast = lastMod
            
            xbmc.sleep(3000)
                        
        xbmc.log("LoadMenuOptionsThread Exited")

    def loadMenuOptions(self, pathTofavourites):
               
        self.logMsg("LoadMenuOptionsThread -> Loading menu items from : " + pathTofavourites)
        WINDOW = xbmcgui.Window( 10000 )
        menuItem = 0
        
        try:
            tree = xml.parse(pathTofavourites)
            rootElement = tree.getroot()
        except Exception, e:
            xbmc.log("LoadMenuOptionsThread -> Error Parsing favourites.xml : " + str(e))
            for x in range(0, 10):
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(x), "")
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(x), "")
            return
        
        for child in rootElement.findall('favourite'):
            name = child.get('name')
            action = child.text
        
            index = action.find("plugin://plugin.video.xbmb3c") # this addon
            if (index == -1):
                index = action.find("plugin://plugin.video.sbview") # sick beard addon
                
            if(index > -1 and len(action) > 10):
                action_url = action[index:len(action) - 2]
                
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(menuItem), name)
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(menuItem), action_url)
                self.logMsg("xbmb3c_menuitem_name_" + str(menuItem) + " : " + name, level=2)
                self.logMsg("xbmb3c_menuitem_action_" + str(menuItem) + " : " + action_url, level=2)
                
                menuItem = menuItem + 1

        for x in range(menuItem, menuItem+10):
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(x), "")
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(x), "")
                self.logMsg("xbmb3c_menuitem_name_" + str(x) + " : ", level=2)
                self.logMsg("xbmb3c_menuitem_action_" + str(x) + " : ", level=2)
            
newMenuThread = LoadMenuOptionsThread()
newMenuThread.start()

#################################################################################################
# end menu item loader
#################################################################################################

#################################################################################################
# http image proxy server 
# This acts as a HTTP Image proxy server for all thumbs and artwork requests
# this is needed due to the fact XBMC can not use the MB3 API as it has issues with the HTTP response format
# this proxy handles all the requests and allows XBMC to call the MB3 server
#################################################################################################

class MyHandler(BaseHTTPRequestHandler):
    
    logLevel = 0
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        BaseHTTPRequestHandler.__init__(self, *args)
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Image Proxy -> " + msg)
    
    #overload the default log func to stop stderr message from showing up in the xbmc log
    def log_message(self, format, *args):
        if(self.logLevel >= 1):
            the_string = [str(i) for i in range(len(args))]
            the_string = '"{' + '}" "{'.join(the_string) + '}"'
            the_string = the_string.format(*args)
            xbmc.log("XBMB3C Image Proxy -> BaseHTTPRequestHandler : " + the_string)
        return    
    
    def do_GET(self):
    
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')
        
        params = parse_qs(self.path[2:])
        self.logMsg("Params : " + str(params))
        
        if(params.get("id") == None):
            return
        
        itemId = params["id"][0]
        requestType = params["type"][0]
        
        if (len(params) > 2):
          self.logMsg("Params with Index: " + str(params))  
          index = params['index'][0]
        else:
          index = None

        imageType = "Primary"
        if(requestType == "b"):
            imageType = "Backdrop"
        elif(requestType == "logo"):
            imageType = "Logo"
        elif(requestType == "banner"):
            imageType = "Banner"
        elif(requestType == "disc"):
            imageType = "Disc"
        elif(requestType == "clearart"):
            imageType = "Art"
        elif(requestType == "landscape"):
            imageType = "Thumb"
        
        if (index == None):  
          remoteUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Items/" + itemId + "/Images/" + imageType  + "?Format=png"
        else:
          remoteUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Items/" + itemId + "/Images/" + imageType +  "/" + index  + "?Format=png"
                  
        self.logMsg("MB3 Host : " + mb3Host)
        self.logMsg("MB3 Port : " + mb3Port)
        self.logMsg("Item ID : " + itemId)
        self.logMsg("Request Type : " + requestType)
        self.logMsg("Remote URL : " + remoteUrl)
        
        # get the remote image
        self.logMsg("Downloading Image")
        
        try:
            requesthandle = urllib.urlopen(remoteUrl, proxies={})
            pngData = requesthandle.read()
            requesthandle.close()            
        except Exception, e:
            xbmc.log("Image Proxy MyHandler urlopen : " + str(e) + " (" + remoteUrl + ")")
            return

        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        length = len(pngData)
        
        self.logMsg("ReSending Image")
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Content-Length', length)
        self.send_header('Last-Modified', datestring)        
        self.end_headers()
        self.wfile.write(pngData)
        self.logMsg("Image Sent")
        
    def do_HEAD(self):
        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Last-Modified', datestring)
        self.end_headers()        
        
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

keepServing = True
def startServer():

    server = ThreadingHTTPServer(("",15001), MyHandler)
    
    while (keepServing):
        server.handle_request()
    #server.serve_forever()
    
    xbmc.log("XBMB3s -> HTTP Image Proxy Server EXITING")
    
xbmc.log("XBMB3s -> HTTP Image Proxy Server Starting")
Thread(target=startServer).start()
xbmc.log("XBMB3s -> HTTP Image Proxy Server NOW SERVING IMAGES")

#################################################################################################
# end http image proxy server 
#################################################################################################

#################################################################################################
# Recent Info Updater
# 
#################################################################################################

class RecentInfoUpdaterThread(threading.Thread):

    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Recent Info Thread -> " + msg)
    
    def run(self):
        xbmc.log("RecentInfoUpdaterThread Started")
        
        self.updateRecent()
        lastRun = datetime.today()
        lastProfilePath = xbmc.translatePath('special://profile')
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)        
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            profilePath = xbmc.translatePath('special://profile')
            
            updateInterval = 60
            if (xbmc.Player().isPlaying()):
                updateInterval = 300
                
            if(secTotal > updateInterval or lastProfilePath != profilePath):
                self.updateRecent()
                lastRun = datetime.today()

            lastProfilePath = profilePath
            
            xbmc.sleep(3000)
                        
        xbmc.log("RecentInfoUpdaterThread Exited")
        
    def updateRecent(self):
        self.logMsg("updateRecent Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()              
        except Exception, e:
            xbmc.log("RecentInfoUpdaterThread updateRecent urlopen : " + str(e) + " (" + userUrl + ")")
            return

        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        self.logMsg("updateRecentMovies UserName : " + userName + " UserID : " + userid)
        
        self.logMsg("Updating Recent Movie List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview,CriticRatingSummary&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json"
        
        try:
            requesthandle = urllib.urlopen(recentUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()              
        except Exception, e:
            xbmc.log("RecentInfoUpdaterThread updateRecent urlopen : " + str(e) + " (" + recentUrl + ")")
            return    

        result = json.loads(jsonData)
        
        result = result.get("Items")
        if(result == None):
            result = []
            
        WINDOW = xbmcgui.Window( 10000 )

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
            
            rating = item.get("CommunityRating")
            criticrating = item.get("CriticRating")
            criticratingsummary = ""
            if(item.get("CriticRatingSummary") != None):
                criticratingsummary = item.get("CriticRatingSummary").encode('utf-8')
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')
            year = item.get("ProductionYear")
            if(item.get("RunTimeTicks") != None):
                runtime = str(int(item.get("RunTimeTicks"))/(10000000*60))
            else:
                runtime = "0"

            item_id = item.get("Id")
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(item_id) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(item_id) + "&type=b"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestMovieMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
            self.logMsg("LatestMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
            
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Path", playUrl)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Rating", str(rating))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("LatestMovieMB3." + str(item_count) + ".Runtime", str(runtime))
            
            item_count = item_count + 1
        
        #Updating Recent TV Show List
        self.logMsg("Updating Recent TV Show List")
        
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json"
        
        try:
            requesthandle = urllib.urlopen(recentUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()               
        except Exception, e:
            xbmc.log("RecentInfoUpdaterThread updateRecent urlopen : " + str(e) + " (" + recentUrl + ")")
            return

        result = json.loads(jsonData)
        self.logMsg("Recent TV Show Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = "00"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "Episode" or item.get("Type") == "Season":
               series_id = item.get("SeriesId")
            
            poster = "http://localhost:15001/?id=" + str(series_id) + "&type=t"
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(series_id) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(series_id) + "&type=b"
            banner = "http://localhost:15001/?id=" + str(series_id) + "&type=banner"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("LatestEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("LatestEpisodeMB3." + str(item_count) + ".Plot", plot)
            
            item_count = item_count + 1
            
        #Updating Recent MusicList
        self.logMsg("Updating Recent MusicList")
    
        recentUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=DateCreated&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=MusicAlbum&format=json"
    
        try:
            requesthandle = urllib.urlopen(recentUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()                 
        except Exception, e:
            xbmc.log("RecentInfoUpdaterThread updateRecent urlopen : " + str(e) + " (" + recentUrl + ")")
            return
    
        result = json.loads(jsonData)
        self.logMsg("Recent MusicList Json Data : " + str(result))
    
        result = result.get("Items")
        if(result == None):
          result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            artist = "Missing Artist"
            if(item.get("AlbumArtist") != None):
                artist = item.get("AlbumArtist").encode('utf-8')   

            year = "0000"
            if(item.get("ProductionYear") != None):
              year = str(item.get("ProductionYear"))
            plot = "Missing Plot"
            if(item.get("Overview") != None):
              plot = item.get("Overview").encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "MusicAlbum":
               parentId = item.get("ParentLogoItemId")
            
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(parentId) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(parentId) + "&type=b"
            banner = "http://localhost:15001/?id=" + str(parentId) + "&type=banner"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Artist = " + artist, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Year = " + year, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(banner)  = " + banner, level=2)  
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("LatestAlbumMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Artist", artist)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Year", year)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(banner)", banner)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("LatestAlbumMB3." + str(item_count) + ".Plot", plot)
            
            item_count = item_count + 1
        
        
newThread = RecentInfoUpdaterThread()
newThread.start()

#################################################################################################
# end Recent Info Updater
#################################################################################################

#################################################################################################
# Start of BackgroundRotationThread
# Sets a backgound property to a fan art link
#################################################################################################

class BackgroundRotationThread(threading.Thread):

    movie_art_links = []
    tv_art_links = []
    music_art_links = []
    global_art_links = []
    current_movie_art = 0
    current_tv_art = 0
    current_music_art = 0
    current_global_art = 0
    linksLoaded = False
    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Background Image Thread -> " + msg)
    
    def run(self):
        xbmc.log("BackgroundRotationThread Started")
        
        try:
            self.loadLastBackground()
        except Exception, e:
            xbmc.log("BackgroundRotationThread loadLastBackground Exception : " + str(e))
        
        self.updateArtLinks()
        self.setBackgroundLink()
        lastRun = datetime.today()
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        
        backgroundRefresh = int(addonSettings.getSetting('backgroundRefresh'))
        if(backgroundRefresh < 10):
            backgroundRefresh = 10
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > backgroundRefresh):
                if(self.linksLoaded == False):
                    self.updateArtLinks()
                self.setBackgroundLink()
                lastRun = datetime.today()
                
                backgroundRefresh = int(addonSettings.getSetting('backgroundRefresh'))
                if(backgroundRefresh < 10):
                    backgroundRefresh = 10                

            xbmc.sleep(1000)
        
        try:
            self.saveLastBackground()
        except Exception, e:
            xbmc.log(str(e))  
            
        xbmc.log("BackgroundRotationThread Exited")

        
    def loadLastBackground(self):
        
        __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )         
        
        lastDataPath = __addondir__ + "LastBgLinks.json"
        dataFile = open(lastDataPath, 'r')
        jsonData = dataFile.read()
        dataFile.close()
        
        self.logMsg(jsonData)
        result = json.loads(jsonData)
        
        WINDOW = xbmcgui.Window( 10000 )
        if(result.get("global") != None):
            self.logMsg("Setting Global Last : " + result.get("global"), level=2)
            WINDOW.setProperty("MB3.Background.Global.FanArt", result.get("global"))       

        if(result.get("movie") != None):
            self.logMsg("Setting Movie Last : " + result.get("movie"), level=2)
            WINDOW.setProperty("MB3.Background.Movie.FanArt", result.get("movie"))      
            
        if(result.get("tv") != None):
            self.logMsg("Setting TV Last : " + result.get("tv"), level=2)
            WINDOW.setProperty("MB3.Background.TV.FanArt", result.get("tv"))    

        if(result.get("music") != None):
            self.logMsg("Setting Music Last : " + result.get("music"), level=2)
            WINDOW.setProperty("MB3.Background.Music.FanArt", result.get("music"))   
        
    def saveLastBackground(self):
    
        data = {}
        if(len(self.global_art_links) > 0):
            data["global"] = self.global_art_links[self.current_global_art]
        if(len(self.movie_art_links) > 0):
            data["movie"] = self.movie_art_links[self.current_movie_art]
        if(len(self.tv_art_links) > 0):
            data["tv"] = self.tv_art_links[self.current_tv_art]
        if(len(self.music_art_links) > 0):
            data["music"] = self.music_art_links[self.current_music_art]

        __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )            
            
        lastDataPath = __addondir__ + "LastBgLinks.json"
        dataFile = open(lastDataPath, 'w')
        stringdata = json.dumps(data)
        self.logMsg("Last Background Links : " + stringdata)
        dataFile.write(stringdata)
        dataFile.close()        
    
    def setBackgroundLink(self):
    
        WINDOW = xbmcgui.Window( 10000 )
        
        if(len(self.movie_art_links) > 0):
            self.logMsg("setBackgroundLink index movie_art_links " + str(self.current_movie_art + 1) + " of " + str(len(self.movie_art_links)), level=2)
            artUrl =  self.movie_art_links[self.current_movie_art]
            WINDOW.setProperty("MB3.Background.Movie.FanArt", artUrl)
            self.logMsg("MB3.Background.Movie.FanArt=" + artUrl, level=2)
            self.current_movie_art = self.current_movie_art + 1
            if(self.current_movie_art == len(self.movie_art_links)):
                self.current_movie_art = 0
        
        if(len(self.tv_art_links) > 0):
            self.logMsg("setBackgroundLink index tv_art_links " + str(self.current_tv_art + 1) + " of " + str(len(self.tv_art_links)), level=2)
            artUrl =  self.tv_art_links[self.current_tv_art]
            WINDOW.setProperty("MB3.Background.TV.FanArt", artUrl)
            self.logMsg("MB3.Background.TV.FanArt=" + artUrl, level=2)
            self.current_tv_art = self.current_tv_art + 1
            if(self.current_tv_art == len(self.tv_art_links)):
                self.current_tv_art = 0
                
        if(len(self.music_art_links) > 0):
            self.logMsg("setBackgroundLink index music_art_links " + str(self.current_music_art + 1) + " of " + str(len(self.music_art_links)), level=2)
            artUrl =  self.music_art_links[self.current_music_art]
            WINDOW.setProperty("MB3.Background.Music.FanArt", artUrl)
            self.logMsg("MB3.Background.Music.FanArt=" + artUrl, level=2)
            self.current_music_art = self.current_music_art + 1
            if(self.current_music_art == len(self.music_art_links)):
                self.current_music_art = 0
            
        if(len(self.global_art_links) > 0):
            self.logMsg("setBackgroundLink index global_art_links " + str(self.current_global_art + 1) + " of " + str(len(self.global_art_links)), level=2)
            artUrl =  self.global_art_links[self.current_global_art]
            WINDOW.setProperty("MB3.Background.Global.FanArt", artUrl)
            self.logMsg("MB3.Background.Global.FanArt=" + artUrl, level=2)
            self.current_global_art = self.current_global_art + 1         
            if(self.current_global_art == len(self.global_art_links)):
                self.current_global_art = 0
                
    def updateArtLinks(self):
        self.logMsg("updateArtLinks Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("BackgroundRotationThread updateArtLinks urlopen : " + str(e) + " (" + userUrl + ")")
            return        
        
        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        self.logMsg("updateArtLinks UserID : " + userid)
        
        moviesUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&IncludeItemTypes=Movie&format=json"

        try:
            requesthandle = urllib2.urlopen(moviesUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("BackgroundRotationThread updateArtLinks urlopen : " + str(e) + " (" + moviesUrl + ")")
            return          
        
        result = json.loads(jsonData)
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              fanartLink = "http://localhost:15001/?id=" + str(id) + "&type=b" + "&index=" + str(index)
              if (fanartLink not in self.movie_art_links):
                  self.movie_art_links.append(fanartLink)
              index = index + 1
        
        random.shuffle(self.movie_art_links)
        self.logMsg("Background Movie Art Links : " + str(len(self.movie_art_links)))
        
        tvUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&IncludeItemTypes=Series&format=json"

        try:
            requesthandle = urllib2.urlopen(tvUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("BackgroundRotationThread updateArtLinks urlopen : " + str(e) + " (" + tvUrl + ")")
            return          
        
        result = json.loads(jsonData)        
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              fanartLink = "http://localhost:15001/?id=" + str(id) + "&type=b" + "&index=" + str(index)
              if (fanartLink not in self.tv_art_links):
                  self.tv_art_links.append(fanartLink)    
              index = index + 1
              
        random.shuffle(self.tv_art_links)
        self.logMsg("Background Tv Art Links : " + str(len(self.tv_art_links)))

        musicUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&IncludeItemTypes=MusicArtist&format=json"
        
        try:
            requesthandle = urllib2.urlopen(musicUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("BackgroundRotationThread updateArtLinks urlopen : " + str(e) + " (" + musicUrl + ")")
            return           
        
        result = json.loads(jsonData)        
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              fanartLink = "http://localhost:15001/?id=" + str(id) + "&type=b" + "&index=" + str(index)
              if (fanartLink not in self.music_art_links):
                  self.music_art_links.append(fanartLink)
              index = index + 1

        random.shuffle(self.music_art_links)
        self.logMsg("Background Music Art Links : " + str(len(self.music_art_links)))

        self.global_art_links.extend(self.movie_art_links)
        self.global_art_links.extend(self.tv_art_links)
        self.global_art_links.extend(self.music_art_links)
        random.shuffle(self.global_art_links)
        self.logMsg("Background Global Art Links : " + str(len(self.global_art_links)))
        self.linksLoaded = True
        
backgroundUpdaterThread = BackgroundRotationThread()
backgroundUpdaterThread.start()

#################################################################################################
# End of BackgroundRotationThread
#################################################################################################

#################################################################################################
# Random Info Updater
# 
#################################################################################################

class RandomInfoUpdaterThread(threading.Thread):

    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Random Info Thread -> " + msg)
    
    def run(self):
        xbmc.log("RandomInfoUpdaterThread Started")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        
        self.updateRandom()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateRandom()
                lastRun = datetime.today()

            xbmc.sleep(1000)
                        
        xbmc.log("RandomInfoUpdaterThread Exited")
        
    def updateRandom(self):
        self.logMsg("updateRandomMovies Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()      
        except Exception, e:
            xbmc.log("RandomInfoUpdaterThread updateRandom urlopen : " + str(e) + " (" + userUrl + ")")
            return           
        
        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        self.logMsg("updateRandomMovies UserID : " + userid)
        
        self.logMsg("Updating Random Movie List")
        
        randomUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=Random&Fields=Path,Genres,MediaStreams,Overview,CriticRatingSummary&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json"
        
        try:
            requesthandle = urllib.urlopen(randomUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()     
        except Exception, e:
            xbmc.log("RandomInfoUpdaterThread updateRandom urlopen : " + str(e) + " (" + randomUrl + ")")
            return           

        result = json.loads(jsonData)
        self.logMsg("Random Movie Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []
            
        WINDOW = xbmcgui.Window( 10000 )

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
            
            rating = item.get("CommunityRating")
            criticrating = item.get("CriticRating")
            criticratingsummary = ""
            if(item.get("CriticRatingSummary") != None):
                criticratingsummary = item.get("CriticRatingSummary").encode('utf-8')
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')
            year = item.get("ProductionYear")
            if(item.get("RunTimeTicks") != None):
                runtime = str(int(item.get("RunTimeTicks"))/(10000000*60))
            else:
                runtime = "0"

            item_id = item.get("Id")
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(item_id) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(item_id) + "&type=b"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("RandomMovieMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
            self.logMsg("RandomMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
            
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Path", playUrl)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Rating", str(rating))
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("RandomMovieMB3." + str(item_count) + ".Runtime", str(runtime))
            
            item_count = item_count + 1
        
        self.logMsg("Updating Random TV Show List")
        
        randomUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=Random&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json"
        
        try:
            requesthandle = urllib.urlopen(randomUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()         
        except Exception, e:
            xbmc.log("RandomInfoUpdaterThread updateRandom urlopen : " + str(e) + " (" + randomUrl + ")")
            return          
        
        result = json.loads(jsonData)
        self.logMsg("Random TV Show Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = ""
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "Episode" or item.get("Type") == "Season":
               series_id = item.get("SeriesId")
            
            poster = "http://localhost:15001/?id=" + str(series_id) + "&type=t"
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(series_id) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(series_id) + "&type=b"
            banner = "http://localhost:15001/?id=" + str(series_id) + "&type=banner"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("RandomEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("RandomEpisodeMB3." + str(item_count) + ".Plot", plot)
            
            
            item_count = item_count + 1
            
        # update random music
        self.logMsg("Updating Random MusicList")
    
        randomUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=10&Recursive=true&SortBy=Random&Fields=Path,Genres,MediaStreams,Overview&SortOrder=Descending&Filters=IsUnplayed,IsFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=MusicAlbum&format=json"
    
        try:
            requesthandle = urllib.urlopen(randomUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()     
        except Exception, e:
            xbmc.log("RandomInfoUpdaterThread updateRandom urlopen : " + str(e) + " (" + randomUrl + ")")
            return  
    
        result = json.loads(jsonData)
        self.logMsg("Random MusicList Json Data : " + str(result), level=2)
    
        result = result.get("Items")
        if(result == None):
          result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            artist = "Missing Artist"
            if(item.get("AlbumArtist") != None):
                artist = item.get("AlbumArtist").encode('utf-8')   

            year = "0000"
            if(item.get("ProductionYear") != None):
              year = str(item.get("ProductionYear"))
            plot = "Missing Plot"
            if(item.get("Overview") != None):
              plot = item.get("Overview").encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "MusicAlbum":
               parentId = item.get("ParentLogoItemId")
            
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(parentId) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(parentId) + "&type=b"
            banner = "http://localhost:15001/?id=" + str(parentId) + "&type=banner"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Title = " + title, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Artist = " + artist, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Year = " + year, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Art(banner)  = " + banner, level=2)  
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
            self.logMsg("RandomAlbumMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            
            
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Title", title)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Artist", artist)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Year", year)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Art(fanart)", fanart)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Art(clearlogo)", logo)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Art(banner)", banner)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Art(poster)", thumbnail)
            WINDOW.setProperty("RandomAlbumMB3." + str(item_count) + ".Plot", plot)
            
            item_count = item_count + 1
        
        
newThread = RandomInfoUpdaterThread()
newThread.start()

#################################################################################################
# end Random Info Updater
#################################################################################################

#################################################################################################
# NextUp TV Updater
# 
#################################################################################################

class NextUpUpdaterThread(threading.Thread):

    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C NextUp Thread -> " + msg)
    
    def run(self):
        xbmc.log("NextUpUpdaterThread Started")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
        
        self.updateNextUp()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateNextUp()
                lastRun = datetime.today()

            xbmc.sleep(3000)
                        
        xbmc.log("NextUpUpdaterThread Exited")
        
    def updateNextUp(self):
        xbmc.log("updateNextUp Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()     
        except Exception, e:
            xbmc.log("NextUpUpdaterThread updateNextUp urlopen : " + str(e) + " (" + userUrl + ")")
            return  
        
        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        self.logMsg("updateNextUp UserID : " + userid)
        
        self.logMsg("Updating NextUp List")
        
        nextUpUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Shows/NextUp?UserId=" + userid + "&Fields=Path,Genres,MediaStreams,Overview&format=json"
        
        try:
            requesthandle = urllib.urlopen(nextUpUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("NextUpUpdaterThread updateNextUp urlopen : " + str(e) + " (" + nextUpUrl + ")")
            return  
        
        result = json.loads(jsonData)
        self.logMsg("NextUP TV Show Json Data : " + str(result))
        
        result = result.get("Items")
        WINDOW = xbmcgui.Window( 10000 )
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')

            item_id = item.get("Id")
           
            if item.get("Type") == "Episode" or item.get("Type") == "Season":
               series_id = item.get("SeriesId")
            
            poster = "http://localhost:15001/?id=" + str(series_id) + "&type=t"
            thumbnail = "http://localhost:15001/?id=" + str(item_id) + "&type=t"
            logo = "http://localhost:15001/?id=" + str(series_id) + "&type=logo"
            fanart = "http://localhost:15001/?id=" + str(series_id) + "&type=b"
            banner = "http://localhost:15001/?id=" + str(series_id) + "&type=banner"
            
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            # Process UserData
            userData = item.get("UserData")
            if(userData != None):
                resume = str(userData.get("PlaybackPositionTicks"))
                if (resume == "0"):
                    resume = "False"
                else:
                    resume = "True"

            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Resume  = " + resume, level=2)
            
            
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Resume", resume)
            
            item_count = item_count + 1

newThread = NextUpUpdaterThread()
newThread.start()

#################################################################################################
# end NextUp TV Updater
##################################################################################################

#################################################################################################
# Info Updater
# 
#################################################################################################


class InfoUpdaterThread(threading.Thread):

    logLevel = 0
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C Info Thread -> " + msg)
    
    def run(self):
        xbmc.log("InfoUpdaterThread Started")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)       
        
        self.updateInfo()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateInfo()
                lastRun = datetime.today()

            xbmc.sleep(3000)
                        
        xbmc.log("InfoUpdaterThread Exited")
        
    def updateInfo(self):
        self.logMsg("updateInfo Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')        
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()        
        except Exception, e:
            xbmc.log("InfoUpdaterThread updateInfo urlopen : " + str(e) + " (" + userUrl + ")")
            return          
        
        userid = ""
        result = json.loads(jsonData)
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")    
                break
        
        self.logMsg("updateInfo UserID : " + userid)
        
        self.logMsg("Updating info List")
        
        infoUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Fields=CollectionType&format=json"
        
        try:
            requesthandle = urllib.urlopen(infoUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()      
        except Exception, e:
            xbmc.log("InfoUpdaterThread updateInfo urlopen : " + str(e) + " (" + infoUrl + ")")
            return  
        
        result = json.loads(jsonData)
        
        result = result.get("Items")
        WINDOW = xbmcgui.Window( 10000 )
        if(result == None):
            result = []   

        item_count = 1
        movie_count = 0
        movie_unwatched_count = 0
        tv_count = 0
        episode_count = 0
        episode_unwatched_count = 0
        tv_unwatched_count = 0
        music_count = 0
        music_songs_count = 0
        music_songs_unplayed_count = 0
        musicvideos_count = 0
        musicvideos_unwatched_count = 0
        trailers_count = 0
        trailers_unwatched_count = 0
        for item in result:
            collectionType = item.get("CollectionType")
            if collectionType==None:
                collectionType="unknown"
            self.logMsg("collectionType "  + collectionType)    
            if(collectionType == "movies"):
                movie_count = movie_count + item.get("RecursiveItemCount")
                movie_unwatched_count = movie_unwatched_count + item.get("RecursiveUnplayedItemCount")
                
            if(collectionType == "musicvideos"):
                musicvideos_count = musicvideos_count + item.get("RecursiveItemCount")
                musicvideos_unwatched_count = musicvideos_unwatched_count + item.get("RecursiveUnplayedItemCount")
            
            if(collectionType == "tvshows"):
                tv_count = tv_count + item.get("ChildCount")
                episode_count = episode_count + item.get("RecursiveItemCount")
                episode_unwatched_count = episode_unwatched_count + item.get("RecursiveUnplayedItemCount")
            
            if(collectionType == "music"):
                music_count = music_count + item.get("ChildCount")
                music_songs_count = music_songs_count + item.get("RecursiveItemCount")
                music_songs_unplayed_count = music_songs_unplayed_count + item.get("RecursiveUnplayedItemCount")
                  
            if(item.get("Name") == "Trailers"):
                trailers_count = trailers_count + item.get("RecursiveItemCount")
                trailers_unwatched_count = trailers_unwatched_count + item.get("RecursiveUnplayedItemCount")
               
        self.logMsg("MoviesCount "  + str(movie_count), level=2)
        self.logMsg("MoviesUnWatchedCount "  + str(movie_unwatched_count), level=2)
        self.logMsg("MusicVideosCount "  + str(musicvideos_count), level=2)
        self.logMsg("MusicVideosUnWatchedCount "  + str(musicvideos_unwatched_count), level=2)
        self.logMsg("TVCount "  + str(tv_count), level=2)
        self.logMsg("EpisodeCount "  + str(episode_count), level=2)
        self.logMsg("EpisodeUnWatchedCount "  + str(episode_unwatched_count), level=2)
        self.logMsg("MusicCount "  + str(music_count), level=2)
        self.logMsg("SongsCount "  + str(music_songs_count), level=2)
        self.logMsg("SongsUnPlayedCount "  + str(music_songs_unplayed_count), level=2)
        self.logMsg("TrailersCount" + str(trailers_count), level=2)
        self.logMsg("TrailersUnWatchedCount" + str(trailers_unwatched_count), level=2)
    
            #item_count = item_count + 1
        
        movie_watched_count = movie_count - movie_unwatched_count
        musicvideos_watched_count = musicvideos_count - musicvideos_unwatched_count
        episode_watched_count = episode_count - episode_unwatched_count
        music_songs_played_count = music_songs_count - music_songs_unplayed_count
        trailers_watched_count = trailers_count - trailers_unwatched_count    
        WINDOW.setProperty("MB3TotalMovies", str(movie_count))
        WINDOW.setProperty("MB3TotalUnWatchedMovies", str(movie_unwatched_count))
        WINDOW.setProperty("MB3TotalWatchedMovies", str(movie_watched_count))
        WINDOW.setProperty("MB3TotalMusicVideos", str(musicvideos_count))
        WINDOW.setProperty("MB3TotalUnWatchedMusicVideos", str(musicvideos_unwatched_count))
        WINDOW.setProperty("MB3TotalWatchedMusicVideos", str(musicvideos_watched_count))
        WINDOW.setProperty("MB3TotalTvShows", str(tv_count))
        WINDOW.setProperty("MB3TotalEpisodes", str(episode_count))
        WINDOW.setProperty("MB3TotalUnWatchedEpisodes", str(episode_unwatched_count))
        WINDOW.setProperty("MB3TotalWatchedEpisodes", str(episode_watched_count))
        WINDOW.setProperty("MB3TotalMusicAlbums", str(music_count))
        WINDOW.setProperty("MB3TotalMusicSongs", str(music_songs_count))
        WINDOW.setProperty("MB3TotalUnPlayedMusicSongs", str(music_songs_unplayed_count))
        WINDOW.setProperty("MB3TotalPlayedMusicSongs", str(music_songs_played_count))
        WINDOW.setProperty("MB3TotalTrailers", str(trailers_count))
        WINDOW.setProperty("MB3TotalUnWatchedTrailers", str(trailers_unwatched_count))
        WINDOW.setProperty("MB3TotalWatchedTrailers", str(trailers_watched_count))

        self.logMsg("InfoTV start")
        infoTVUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?&IncludeItemTypes=Series&Recursive=true&SeriesStatus=Continuing&format=json"
        
        try:
            requesthandle = urllib.urlopen(infoTVUrl, proxies={})
            self.logMsg("InfoTV start open")
            jsonData = requesthandle.read()
            requesthandle.close()  
        except Exception, e:
            xbmc.log("InfoUpdaterThread updateInfo urlopen : " + str(e) + " (" + infoTVUrl + ")")
            return  
        
        result = json.loads(jsonData)
        self.logMsg("InfoTV Json Data : " + str(result))
        
        totalRunning = result.get("TotalRecordCount")
        self.logMsg("TotalRunningCount "  + str(totalRunning))
        WINDOW.setProperty("MB3TotalRunningTvShows", str(totalRunning))
        
        self.logMsg("InfoNextAired start")
        InfoNextAiredUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?IsUnaired=true&SortBy=PremiereDate%2CAirTime%2CSortName&SortOrder=Ascending&IncludeItemTypes=Episode&Limit=1&Recursive=true&Fields=SeriesInfo%2CUserData&format=json"
        
        try:
            requesthandle = urllib.urlopen(InfoNextAiredUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("InfoUpdaterThread updateInfo urlopen : " + str(e) + " (" + InfoNextAiredUrl + ")")
            return  
        
        result = json.loads(jsonData)
        self.logMsg("InfoNextAired Json Data : " + str(result))
        
        result = result.get("Items")
        if(result == None):
            result = []
        
        episode = ""
        for item in result:
            title = ""
            seriesName = ""
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')
            
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            eppNumber = ""
            tempEpisodeNumber = ""
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
               
            episode = seriesName + " - " + title + " - S" + tempSeasonNumber + "E" + tempEpisodeNumber
        
        self.logMsg("MB3NextAiredEpisode"  + episode)
        WINDOW.setProperty("MB3NextAiredEpisode", episode)
        self.logMsg("InfoNextAired end")
        
        today = datetime.today()    
        dateformat = today.strftime("%Y-%m-%d") 
        nextAiredUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?IsUnaired=true&SortBy=PremiereDate%2CAirTime%2CSortName&SortOrder=Ascending&IncludeItemTypes=Episode&Recursive=true&Fields=SeriesInfo%2CUserData&MinPremiereDate="  + str(dateformat) + "&MaxPremiereDate=" + str(dateformat) + "&format=json"
        
        try:
            requesthandle = urllib.urlopen(nextAiredUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            xbmc.log("InfoUpdaterThread updateInfo total urlopen : " + str(e) + " (" + nextAiredUrl + ")")
            return  
        
        result = json.loads(jsonData)
        self.logMsg("InfoNextAired total url: " + nextAiredUrl)
        self.logMsg("InfoNextAired total Json Data : " + str(result))
        
        totalToday = result.get("TotalRecordCount")
        self.logMsg("MB3NextAiredTotalToday "  + str(totalToday))
        WINDOW.setProperty("MB3NextAiredTotalToday", str(totalToday))  
        
newThread = InfoUpdaterThread()
newThread.start()

#################################################################################################
# end Info Updater
#################################################################################################
def delete (url):
    return_value = xbmcgui.Dialog().yesno(__language__(30091),__language__(30092))
    if return_value:
        xbmc.log('Deleting via URL: ' + url)
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30052), __language__(30053))
        resp = requests.delete(url, data='', headers=getAuthHeader())
        deleteSleep=0
        while deleteSleep<10:
            xbmc.sleep(1000)
            deleteSleep=deleteSleep+1
            progress.update(deleteSleep*10,__language__(30053))
        progress.close()
        xbmc.executebuiltin("Container.Refresh")
        
def markWatched(url):
    xbmc.log('XBMB3C Service -> Marking watched via: ' + url)
    resp = requests.post(url, data='', headers=getAuthHeader())
    
def markUnWatched(url):
    xbmc.log('XBMB3C Service -> Marking watched via: ' + url)
    resp = requests.delete(url, data='', headers=getAuthHeader())    

def setPosition (url, method):
    xbmc.log('XBMB3C Service -> Setting position via: ' + url)
    if method == 'POST':
        resp = requests.post(url, data='', headers=getAuthHeader())
    elif method == 'DELETE':
        resp = requests.delete(url, data='', headers=getAuthHeader())
        
def hasData(data):
    if(data == None or len(data) == 0 or data == "None"):
        return False
    else:
        return True
        
def stopAll(played_information):

    if(len(played_information) == 0):
        return 
        
    addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    xbmc.log ("XBMB3C Service -> played_information : " + str(played_information))
    
    for item_url in played_information:
        data = played_information.get(item_url)
        if(data != None):
            xbmc.log ("XBMB3C Service -> item_url  : " + item_url)
            xbmc.log ("XBMB3C Service -> item_data : " + str(data))
            
            watchedurl = data.get("watchedurl")
            positionurl = data.get("positionurl")
            deleteurl = data.get("deleteurl")
            runtime = data.get("runtime")
            currentPossition = data.get("currentPossition")
            item_id = data.get("item_id")
            
            if(currentPossition != None and hasData(runtime) and hasData(positionurl) and hasData(watchedurl)):
                runtimeTicks = int(runtime)
                xbmc.log ("XBMB3C Service -> runtimeticks:" + str(runtimeTicks))
                percentComplete = (currentPossition * 10000000) / runtimeTicks
                markPlayedAt = float(addonSettings.getSetting("markPlayedAt")) / 100    

                xbmc.log ("XBMB3C Service -> Percent Complete:" + str(percentComplete) + " Mark Played At:" + str(markPlayedAt))
                if (percentComplete > markPlayedAt):
                    if(deleteurl != None and deleteurl != ""):
                        xbmc.log ("XBMB3C Service -> Offering Delete:" + str(deleteurl))
                        delete(deleteurl)
                    else:
                        setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')
                        newWebSocketThread.playbackStopped(item_id, str(0))
                        markWatched(watchedurl)
                else:
                    markUnWatched(watchedurl)
                    newWebSocketThread.playbackStopped(item_id, str(int(currentPossition * 10000000)))
                    setPosition(positionurl + '?PositionTicks=' + str(int(currentPossition * 10000000)), 'DELETE')
                    
    played_information.clear()

class Service( xbmc.Player ):

    played_information = {}
    
    def __init__( self, *args ):
        xbmc.log("XBMB3C Service -> starting monitor service")
        self.played_information = {}
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        
        stopAll(self.played_information)
        
        currentFile = xbmc.Player().getPlayingFile()
        
        WINDOW = xbmcgui.Window( 10000 )
        watchedurl = WINDOW.getProperty("watchedurl")
        deleteurl = WINDOW.getProperty("deleteurl")
        positionurl = WINDOW.getProperty("positionurl")
        runtime = WINDOW.getProperty("runtimeticks")
        item_id = WINDOW.getProperty("item_id")
        
        newWebSocketThread.playbackStarted(item_id)
        
        if (watchedurl != "" and positionurl != ""):
        
            data = {}
            data["watchedurl"] = watchedurl
            data["deleteurl"] = deleteurl
            data["positionurl"] = positionurl
            data["runtime"] = runtime
            data["item_id"] = item_id
            self.played_information[currentFile] = data
            
            xbmc.log("XBMB3C Service -> ADDING_FILE : " + currentFile)
            xbmc.log("XBMB3C Service -> ADDING_FILE : " + str(self.played_information))

            # reset in progress possition
            setPosition(positionurl + '/Progress?PositionTicks=0', 'POST')

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        xbmc.log("XBMB3C Service -> onPlayBackEnded")
        stopAll(self.played_information)

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        xbmc.log("XBMB3C Service -> onPlayBackStopped")
        stopAll(self.played_information)

monitor = Service()
lastProgressUpdate = datetime.today()
            
while not xbmc.abortRequested:

    if xbmc.Player().isPlaying():
        try:
        
            playTime = xbmc.Player().getTime()
            currentFile = xbmc.Player().getPlayingFile()
            
            if(monitor.played_information.get(currentFile) != None):
                monitor.played_information[currentFile]["currentPossition"] = playTime
            
            # send update
            td = datetime.today() - lastProgressUpdate
            secDiff = td.seconds
            if(secDiff > 10):
                if(monitor.played_information.get(currentFile) != None and monitor.played_information.get(currentFile).get("item_id") != None):
                    item_id =  monitor.played_information.get(currentFile).get("item_id")
                    newWebSocketThread.sendProgressUpdate(item_id, str(int(playTime * 10000000)))
                lastProgressUpdate = datetime.today()
            
        except Exception, e:
            xbmc.log("XBMB3C Service -> Exception in Playback Monitor : " + str(e))
            pass

    xbmc.sleep(1000)
    
# stop the WebSocket client
newWebSocketThread.stopClient()

# stop the image proxy
keepServing = False
try:
    requesthandle = urllib.urlopen("http://localhost:15001/?id=dummy&type=t", proxies={})
except:
    xbmc.log("XBMB3C Service -> Tried to stop image proxy server but it was already stopped")

xbmc.log("XBMB3C Service -> Service shutting down")

