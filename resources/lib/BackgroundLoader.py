#################################################################################################
# Start of BackgroundRotationThread
# Sets a backgound property to a fan art link
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
import urllib2
import random

from Utils import PlayUtils

class BackgroundRotationThread(threading.Thread):

    movie_art_links = []
    tv_art_links = []
    music_art_links = []
    global_art_links = []
    item_art_links = []
    current_movie_art = 0
    current_tv_art = 0
    current_music_art = 0
    current_global_art = 0
    current_item_art = 0
    linksLoaded = False
    logLevel = 0
    playingTheme = False
    themeId = ''
    volume = ''
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C BackgroundRotationThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C BackgroundRotationThread -> " + msg)
    
    def run(self):
        self.logMsg("Started")
        
        try:
            self.loadLastBackground()
        except Exception, e:
            self.logMsg("loadLastBackground Exception : " + str(e), level=0)
        lastPath=''
        self.updateArtLinks()
        self.updateItemArtLinks()
        self.updateThemeMusic()
        self.setBackgroundLink()
        lastRun = datetime.today()
        itemLastRun = datetime.today()
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        backgroundRefresh = int(addonSettings.getSetting('backgroundRefresh'))
        themeRefresh = 2
        if(backgroundRefresh < 10):
            backgroundRefresh = 10
        itemBackgroundRefresh = 7
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            td2 = datetime.today() - itemLastRun
            secTotal = td.seconds
            secTotal2 = td2.seconds
            
            if (secTotal > themeRefresh):
                self.updateThemeMusic()    
            
            if(secTotal > backgroundRefresh):
                if(self.linksLoaded == False):
                    self.updateArtLinks()
                self.updateItemArtLinks()                
                lastRun = datetime.today()
                backgroundRefresh = int(addonSettings.getSetting('backgroundRefresh'))
                self.setBackgroundLink()
                if(backgroundRefresh < 10):
                    backgroundRefresh = 10                
            self.updateItemArtLinks()
            self.setItemBackgroundLink()               
            if(secTotal2 > itemBackgroundRefresh):
                self.setItemBackgroundLink()
                itemLastRun = datetime.today()
            if xbmc.getInfoLabel('ListItem.FileNameAndPath') != lastPath:
                self.setItemBackgroundLink()
                itemLastRun = datetime.today()
                lastPath=xbmc.getInfoLabel('ListItem.FileNameAndPath')
                
            xbmc.sleep(2000)
        
        try:
            self.saveLastBackground()
        except Exception, e:
            self.logMsg(str(e), level=0)  
            
        self.logMsg("Exited")

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
            self.logMsg("Setting Global Last : " + str(result.get("global")), level=2)
            WINDOW.setProperty("MB3.Background.Global.FanArt", result.get("global")["url"])       

        if(result.get("movie") != None):
            self.logMsg("Setting Movie Last : " + str(result.get("movie")), level=2)
            WINDOW.setProperty("MB3.Background.Movie.FanArt", result.get("movie")["url"])      
            
        if(result.get("tv") != None):
            self.logMsg("Setting TV Last : " + str(result.get("tv")), level=2)
            WINDOW.setProperty("MB3.Background.TV.FanArt", result.get("tv")["url"])    

        if(result.get("music") != None):
            self.logMsg("Setting Music Last : " + str(result.get("music")), level=2)
            WINDOW.setProperty("MB3.Background.Music.FanArt", result.get("music")["url"])   

        if(result.get("item") != None):
            self.logMsg("Setting Item Last : " + str(result.get("item")), level=2)
            WINDOW.setProperty("MB3.Background.Item.FanArt", result.get("item")["url"])   

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
        if(len(self.item_art_links) > 0):
            data["item"] = self.item_art_links[self.current_item_art]            

        __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )            
            
        lastDataPath = __addondir__ + "LastBgLinks.json"
        dataFile = open(lastDataPath, 'w')
        stringdata = json.dumps(data)
        self.logMsg("Last Background Links : " + stringdata)
        dataFile.write(stringdata)
        dataFile.close()        
    
    def setBackgroundLink(self):
    
        # load the background blacklist
        __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )         
        lastDataPath = __addondir__ + "BlackListedBgLinks.json"
        
        black_list = []
        
        # load blacklist data
        try:
            dataFile = open(lastDataPath, 'r')
            jsonData = dataFile.read()
            dataFile.close()        
            black_list = json.loads(jsonData)
            self.logMsg("Loaded Background Black List : " + str(black_list))
        except:
            self.logMsg("No Background Black List found, starting with empty Black List")
            black_list = []    


        WINDOW = xbmcgui.Window( 10000 )
        
        if(len(self.movie_art_links) > 0):
            next, url = self.findNextLink(self.movie_art_links, black_list, self.current_movie_art)
            self.current_movie_art = next
            WINDOW.setProperty("MB3.Background.Movie.FanArt", url)
            self.logMsg("MB3.Background.Movie.FanArt=" + url)
        
        if(len(self.tv_art_links) > 0):
            self.logMsg("setBackgroundLink index tv_art_links " + str(self.current_tv_art + 1) + " of " + str(len(self.tv_art_links)), level=2)
            artUrl =  self.tv_art_links[self.current_tv_art]["url"]
            WINDOW.setProperty("MB3.Background.TV.FanArt", artUrl)
            self.logMsg("MB3.Background.TV.FanArt=" + artUrl)
            self.current_tv_art = self.current_tv_art + 1
            if(self.current_tv_art == len(self.tv_art_links)):
                self.current_tv_art = 0
                
        if(len(self.music_art_links) > 0):
            self.logMsg("setBackgroundLink index music_art_links " + str(self.current_music_art + 1) + " of " + str(len(self.music_art_links)), level=2)
            artUrl =  self.music_art_links[self.current_music_art]["url"] 
            WINDOW.setProperty("MB3.Background.Music.FanArt", artUrl)
            self.logMsg("MB3.Background.Music.FanArt=" + artUrl)
            self.current_music_art = self.current_music_art + 1
            if(self.current_music_art == len(self.music_art_links)):
                self.current_music_art = 0
            
        if(len(self.global_art_links) > 0):
            next, url = self.findNextLink(self.global_art_links, black_list, self.current_global_art)
            self.current_global_art = next
            WINDOW.setProperty("MB3.Background.Global.FanArt", url)
            self.logMsg("MB3.Background.Global.FanArt=" + url)

    def setItemBackgroundLink(self):
    
        # load the background blacklist
        __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )         
        lastDataPath = __addondir__ + "BlackListedBgLinks.json"
        
        black_list = []
        
        # load blacklist data
        try:
            dataFile = open(lastDataPath, 'r')
            jsonData = dataFile.read()
            dataFile.close()        
            black_list = json.loads(jsonData)
            self.logMsg("Loaded Background Black List : " + str(black_list))
        except:
            self.logMsg("No Background Black List found, starting with empty Black List")
            black_list = []    

        WINDOW = xbmcgui.Window( 10000 )
        
        if(len(self.item_art_links) > 0):
            self.logMsg("setBackgroundLink index item_art_links " + str(self.current_item_art + 1) + " of " + str(len(self.item_art_links)), level=2)
            try: 
                artUrl =  self.item_art_links[self.current_item_art]["url"] 
            except IndexError:
                self.current_item_art=0
                artUrl =  self.item_art_links[self.current_item_art]["url"] 
            WINDOW.setProperty("MB3.Background.Item.FanArt", artUrl)
            self.logMsg("MB3.Background.Item.FanArt=" + artUrl)
            self.current_item_art = self.current_item_art + 1
            if(self.current_item_art == len(self.item_art_links)):
                self.current_item_art = 0
                
                
                
    def isBlackListed(self, blackList, bgInfo):
        for blocked in blackList:
            if(bgInfo["parent"] == blocked["parent"]):
                self.logMsg("Block List Parents Match On : " + str(bgInfo) + " : " + str(blocked), level=1)
                if(blocked["index"] == -1 or bgInfo["index"] == blocked["index"]):
                    self.logMsg("Item Blocked", level=1)
                    return True
        return False
           
    def findNextLink(self, linkList, blackList, startIndex):
        currentIndex = startIndex
        
        isBlacklisted = self.isBlackListed(blackList, linkList[currentIndex])
        
        while(isBlacklisted):
        
            currentIndex = currentIndex + 1
            
            if(currentIndex == len(linkList)):
                currentIndex = 0 # loop back to beginning
            if(currentIndex == startIndex):
                return (currentIndex+1, linkList[currentIndex]["url"]) # we checked everything and nothing was ok so return the first one again                

            isBlacklisted = self.isBlackListed(blackList, linkList[currentIndex])
             
        return (currentIndex+1, linkList[currentIndex]["url"])
    
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
            self.logMsg("updateArtLinks urlopen : " + str(e) + " (" + userUrl + ")", level=0)
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
            self.logMsg("updateArtLinks urlopen : " + str(e) + " (" + moviesUrl + ")", level=0)
            return          
        
        result = json.loads(jsonData)
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              
              info = {}
              info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
              info["index"] = index
              info["parent"] = id
              info["name"] = name
              self.logMsg("BG Movie Image Info : " + str(info), level=2)
              
              if (info not in self.movie_art_links):
                  self.movie_art_links.append(info)
              index = index + 1
        
        random.shuffle(self.movie_art_links)
        self.logMsg("Background Movie Art Links : " + str(len(self.movie_art_links)))

        
        tvUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&IncludeItemTypes=Series&format=json"

        try:
            requesthandle = urllib2.urlopen(tvUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateArtLinks urlopen : " + str(e) + " (" + tvUrl + ")", level=2)
            return          
        
        result = json.loads(jsonData)        
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              
              info = {}
              info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
              info["index"] = index
              info["parent"] = id
              info["name"] = name
              self.logMsg("BG TV Image Info : " + str(info), level=2)
              
              if (info not in self.tv_art_links):
                  self.tv_art_links.append(info)    
              index = index + 1
              
        random.shuffle(self.tv_art_links)
        self.logMsg("Background Tv Art Links : " + str(len(self.tv_art_links)))

        
        musicUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&IncludeItemTypes=MusicArtist&format=json"
        
        try:
            requesthandle = urllib2.urlopen(musicUrl, timeout=60)
            jsonData = requesthandle.read()
            requesthandle.close()   
        except Exception, e:
            self.logMsg("updateArtLinks urlopen : " + str(e) + " (" + musicUrl + ")", level=0)
            return           
        
        result = json.loads(jsonData)        
        
        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
              
              info = {}
              info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
              info["index"] = index
              info["parent"] = id
              info["name"] = name
              self.logMsg("BG Music Image Info : " + str(info), level=2)

              if (info not in self.music_art_links):
                  self.music_art_links.append(info)
              index = index + 1
        random.shuffle(self.music_art_links)
        self.logMsg("Background Music Art Links : " + str(len(self.music_art_links)))
       
        self.global_art_links.extend(self.movie_art_links)
        self.global_art_links.extend(self.tv_art_links)
        self.global_art_links.extend(self.music_art_links)
        random.shuffle(self.global_art_links)
        
        self.logMsg("Background Global Art Links : " + str(len(self.global_art_links)))
        self.linksLoaded = True
      
    def updateThemeMusic(self):
        self.logMsg("updateThemeMusic Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
         
        self.item_art_links = []
        id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        self.logMsg("updateThemeMusic itemGUID : " + id)
        if self.isPlayingZone() and self.isChangeTheme():
            self.themeId = id 
            themeUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Items/" + id + "/ThemeSongs?format=json"
            self.logMsg("updateThemeMusic themeUrl : " + themeUrl)
            try:
                    requesthandle = urllib2.urlopen(themeUrl, timeout=60)
                    jsonData = requesthandle.read()
                    requesthandle.close()   
            except Exception, e:
                    self.logMsg("updateThemeMusic urlopen : " + str(e) + " (" + themeUrl + ")", level=0)
                    return
            theme = json.loads(jsonData)
        
               
            if(theme == None):
                theme = []
            
            themeItems = theme.get("Items")
            if themeItems != []:
                themePlayUrl = PlayUtils.getPlayUrl(mb3Host + ":" + mb3Port,themeItems[0].get("Id"),themeItems[0])
                self.logMsg("updateThemeMusic themeMusicPath : " + str(themePlayUrl))
                self.playingTheme = True
                xbmc.Player().play(themePlayUrl)
                
            elif themeItems == [] and self.playingTheme == True:
                self.stop(True)
        
        if not self.isPlayingZone() and self.playingTheme == True:
            # stop
            if  xbmc.Player().isPlayingAudio():
                self.stop()
    
    
    def stop(self, forceStop = False):
        # Only stop if playing audio
        if xbmc.Player().isPlayingAudio() or forceStop == True:
            self.playingTheme = False
            cur_vol = self.getVolume()
            
            # Calculate how fast to fade the theme, this determines
            # the number of step to drop the volume in
            numSteps = 15
            vol_step = cur_vol / numSteps
            # do not mute completely else the mute icon shows up
            for step in range (0,(numSteps-1)):
                vol = cur_vol - vol_step
                self.setVolume(vol)
                cur_vol = vol
                xbmc.sleep(200)
            xbmc.Player().stop()
            self.setVolume(self.volume)  
        
    # Works out if the currently displayed area on the screen is something
    # that is deemed a zone where themes should be played
    def isPlayingZone(self):
        
        if "plugin://plugin.video.xbmb3c" in xbmc.getInfoLabel( "ListItem.Path" ):
            return True
        
        # Any other area is deemed to be a non play area
        return False 
    
    # Works out if we should change/start a theme
    def isChangeTheme(self):
        id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        if id != "":
            if self.volume == '':
                self.volume = self.getVolume()
            # we have something to start with
            addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c') 
            if addonSettings.getSetting('useThemeMusic') == "true":
              # cool theme music is on continue
              if id == self.themeId:
                  # same as before now do we need to restart 
                  if addonSettings.getSetting('loopThemeMusic') == "true" and xbmc.Player().isPlayingAudio() == False:
                      return True
              if id != self.themeId:
                  # new id return true
                  return True  
              
        # still here return False 
        return False 
    
    # This will return the volume in a range of 0-100
    def getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = json.loads(result)
        if "result" in json_query and json_query['result'].has_key('volume'):
            # Get the volume value
            volume = json_query['result']['volume']

        return volume

    # Sets the volume in the range 0-100
    def setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % newvolume, True)
     
        
    def updateItemArtLinks(self):
        self.logMsg("updateItemArtLinks Called")
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users?format=json"
        

        
        self.item_art_links = []
        id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
        self.logMsg("updateItemArtLinks itemGUID : " + id)
    
        if id != "":
            try:
                requesthandle = urllib.urlopen(userUrl, proxies={})
                jsonData = requesthandle.read()
                requesthandle.close()   
            except Exception, e:
                self.logMsg("updateArtItemLinks urlopen : " + str(e) + " (" + userUrl + ")", level=0)
                return        
        
            userid = ""
            result = json.loads(jsonData)
            for user in result:
                if(user.get("Name") == userName):
                    userid = user.get("Id")    
                    break
        
            self.logMsg("updateItemArtLinks UserID : " + userid)
            try:
                currId=lastId
            except UnboundLocalError:
                currId=''
            self.logMsg("updateItemArtLinks id : " + id)
            if currId != id:
                itemUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json"
                try:
                    requesthandle = urllib2.urlopen(itemUrl, timeout=60)
                    jsonData = requesthandle.read()
                    requesthandle.close()   
                except Exception, e:
                    self.logMsg("updateItemArtLinks urlopen : " + str(e) + " (" + itemUrl + ")", level=0)
                    return          
        
                item = json.loads(jsonData)
        
                #result = result.get("Items")
                if(item == None):
                    item = []   
    
                #for item in result:
                images = item.get("BackdropImageTags")
                id = item.get("Id")
                origid = id
                name = item.get("Name")
                
                if (images == None or images == []):
                  images = item.get("ParentBackdropImageTags")
                  id = item.get("ParentId")
                  if (images == None):
                    images = []
                index = 0
             
                for backdrop in images:
                    info = {}
                    info["url"] = "http://localhost:15001/?id=" + str(id) + "&type=Backdrop" + "&index=" + str(index) + "&tag=" + backdrop
                    info["index"] = index
                    info["parent"] = id
                    info["name"] = name
                    self.logMsg("BG Item Image Info : " + str(info), level=2)
            
                    if (info not in self.item_art_links):
                        self.item_art_links.append(info)
                    index = index + 1
                    
                if (images == None or images == []):
                    # no backdrops try and get primary image
                    imageTags = item.get("ImageTags")
                    image = imageTags.get("Primary")
                    info = {}
                    info["url"] = "http://localhost:15001/?id=" + str(origid) + "&type=Primary&tag=" + image
                    info["index"] = index
                    info["parent"] = id
                    info["name"] = name
                    self.logMsg("BG Item Image Info : " + str(info), level=2)
            
                    if (info not in self.item_art_links):
                        self.item_art_links.append(info)
                    

                random.shuffle(self.item_art_links)
                self.logMsg("Background Item Art Links : " + str(len(self.item_art_links)))
                lastId=id
        elif id == "":
            WINDOW = xbmcgui.Window( 10000 )
            WINDOW.clearProperty("MB3.Background.Item.FanArt")

 