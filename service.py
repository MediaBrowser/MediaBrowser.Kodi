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

import mimetypes
from threading import Thread
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

from BackgroundLoader import BackgroundRotationThread
from RecentItems import RecentInfoUpdaterThread
from InProgressItems import InProgressUpdaterThread
from WebSocketClient import WebSocketThread
from ClientInformation import ClientInformation
from MenuLoad import LoadMenuOptionsThread
from ImageProxy import MyHandler
from ImageProxy import ThreadingHTTPServer

_MODE_BASICPLAY=12

def getAuthHeader():
    addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    deviceName = addonSettings.getSetting('deviceName')
    deviceName = deviceName.replace("\"", "_") # might need to url encode this as it is getting added to the header and is user entered data
    clientInfo = ClientInformation()
    txt_mac = clientInfo.getMachineId()
    version = clientInfo.getVersion()  
    userid = xbmcgui.Window( 10000 ).getProperty("userid")
    authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
    headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}
    xbmc.log("XBMB3C Authentication Header : " + str(headers))
    return headers 

# start some worker threads
newInProgressThread = InProgressUpdaterThread()
newInProgressThread.start()

newWebSocketThread = WebSocketThread()
newWebSocketThread.start()

newMenuThread = LoadMenuOptionsThread()
newMenuThread.start()

newThread = RecentInfoUpdaterThread()
newThread.start()

backgroundUpdaterThread = BackgroundRotationThread()
backgroundUpdaterThread.start()

###############################################
# start the image proxy server
###############################################
keepServing = True
def startImageProxyServer():

    xbmc.log("XBMB3S -> HTTP Image Proxy Server Starting")
    server = ThreadingHTTPServer(("",15001), MyHandler)
    
    while (keepServing):
        server.handle_request()
    
    xbmc.log("XBMB3S -> HTTP Image Proxy Server EXITING")
    
Thread(target=startImageProxyServer).start()

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
def deleteItem (url):
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
        return 1
    else:
        return 0
        
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
                
                    gotDeleted = 0
                    if(deleteurl != None and deleteurl != ""):
                        xbmc.log ("XBMB3C Service -> Offering Delete:" + str(deleteurl))
                        gotDeleted = deleteItem(deleteurl)
                        
                    if(gotDeleted == 0):
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

