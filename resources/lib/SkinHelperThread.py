#################################################################################################
# Skin HelperUpdater
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
import urllib
from DownloadUtils import DownloadUtils
from Database import Database
import MainModule

from datetime import datetime, timedelta, time
import urllib2
import random
import time
import os

__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')

#define our global download utils
downloadUtils = DownloadUtils()

class SkinHelperThread(threading.Thread):

    logLevel = 0
    addonSettings = None
    favorites_art_links = []
    favoriteshows_art_links = []
    channels_art_links = []
    global_art_links = []
    musicvideo_art_links = []
    photo_art_links = []
    current_fav_art = 0
    current_favshow_art = 0
    current_channel_art = 0
    current_musicvideo_art = 0
    current_photo_art = 0
    current_global_art = 0
    fullcheckinterval = 3600
    shortcheckinterval = 60
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')   
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        if(self.logLevel == 2):
            self.LogCalls = True
        xbmc.log("XBMB3C SkinHelperThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C SkinHelperThread -> " + msg)
                
    def run(self):
        self.logMsg("Started")

        self.SetMB3WindowProperties()
        self.getImagesFromCache()
        self.updateTypeArtLinks()
        self.updateCollectionArtLinks()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            updateInterval = 60
            if (xbmc.Player().isPlaying()):
                updateInterval = 300
                
            if(secTotal > updateInterval):
                self.SetMB3WindowProperties()
                self.getImagesFromCache()
                self.updateTypeArtLinks()
                self.updateCollectionArtLinks()
                lastRun = datetime.today()
                
                if xbmc.getCondVisibility("Player.HasVideo"):
                    self.logMsg("[MB3 SkinHelper] ...skipped - video playing...")
                else: 
                    WINDOW = xbmcgui.Window( 10000 )
                    userId = WINDOW.getProperty("userid")                   
                    if userId != "":
                        
                        # set some extra global backgrounds
                        self.setBackgroundLink("MB3.Background.FavouriteMovies.FanArt", "favoritemovies")
                        self.setBackgroundLink("MB3.Background.FavouriteShows.FanArt", "favoriteshows")
                        self.setBackgroundLink("MB3.Background.Channels.FanArt", "channels")
                        self.setBackgroundLink("MB3.Background.MusicVideos.FanArt", "musicvideos")
                        self.setBackgroundLink("MB3.Background.Photos.FanArt", "photos")
    
                        # set MB3 user collection backgrounds
                        self.updateGlobalBackgrounds()                    
                        totalUserLinks = int(WINDOW.getProperty("MediaBrowser.usr.Count"))
                        linkCount = 0
                        while linkCount != totalUserLinks:
                            mbstring = "MediaBrowser.usr." + str(linkCount)
                            self.logMsg("set backgroundlink for: " + WINDOW.getProperty(mbstring + ".title"))
                            self.setBackgroundLink(mbstring + ".background", WINDOW.getProperty(mbstring + ".title"))
                            linkCount += 1
                                
                        # set last known images in cache
                        self.setImagesInCache()
                

            xbmc.sleep(30000)
                        
        self.logMsg("Exited")
        
    def findNextLink(self, linkList, startIndex, filterOnName):
        currentIndex = startIndex

        isParentMatch = False

        while(isParentMatch == False):

            currentIndex = currentIndex + 1

            if(currentIndex == len(linkList)):
                currentIndex = 0

            if(currentIndex == startIndex):
                return (currentIndex, linkList[currentIndex])

            isParentMatch = True
            if(filterOnName != None and filterOnName != ""):
                isParentMatch = filterOnName in linkList[currentIndex]["collections"]

        nextIndex = currentIndex + 1

        if(nextIndex == len(linkList)):
            nextIndex = 0

        return (nextIndex, linkList[currentIndex])                 

    # get background images for user collections
    def updateCollectionArtLinks(self):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')

        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')
        WINDOW = xbmcgui.Window( 10000 )
        userid = WINDOW.getProperty("userid")                   
                    
        if userName == "":
            self.logMsg("[MB3 SkinHelper] updateCollectionArtLinks -- xbmb3c username empty, skipping task")
            return False
        else:
            self.logMsg("[MB3 SkinHelper] updateCollectionArtLinks -- xbmb3c username: " + userName)

        userUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/Root?format=json"
        jsonData = downloadUtils.downloadUrl(userUrl, suppress=True, popup=0 )

        result = json.loads(jsonData)

        parentid = result.get("Id")

        userRootPath = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?ParentId=&SortBy=SortName&Fields=CollectionType,Overview,RecursiveItemCount&format=json"
        jsonData = downloadUtils.downloadUrl(userRootPath, suppress=True, popup=0 )

        result = json.loads(jsonData)
        result = result.get("Items")

        artLinks = {}
        collection_count = 0
        WINDOW = xbmcgui.Window( 10000 )

        # process collections
        for item in result:

            collectionType = item.get("CollectionType", "")
            name = item.get("Name")
            childCount = item.get("RecursiveItemCount")
            if(childCount == None or childCount == 0):
                continue

            # Process collection item Backdrops
            self.logMsg("[MB3 SkinHelper get Collection Images Movies and Series]")
            collectionUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?&SortOrder=Descending&ParentId=" + item.get("Id") + "&IncludeItemTypes=Movie,Series,MusicVideo&Fields=ParentId,Overview&SortOrder=Descending&Recursive=true&CollapseBoxSetItems=false&format=json"
            jsonData = downloadUtils.downloadUrl(collectionUrl, suppress=True, popup=0 )  
            collectionResult = json.loads(jsonData)

            self.logMsg("[MB3 SkinHelper COLLECTION] -- " + item.get("Name") + " -- " + collectionUrl)

            collectionResult = collectionResult.get("Items")
            if(collectionResult == None):
                collectionResult = []   

            for col_item in collectionResult:

                id = col_item.get("Id")
                name = col_item.get("Name")
                MB3type = col_item.get("Type")
                images = col_item.get("BackdropImageTags")
                images2 = col_item.get("ImageTags")

                stored_item = artLinks.get(id)

                if(stored_item == None):

                    stored_item = {}
                    collections = []
                    collections.append(item.get("Name"))
                    stored_item["collections"] = collections
                    links = []
                    images = col_item.get("BackdropImageTags")
                    images2 = col_item.get("ImageTags")
                    parentID = col_item.get("ParentId")
                    name = col_item.get("Name")
                    if (images == None):
                        images = []
                    if (images2 == None):
                        images2 = []                    

                    index = 0
                    count = 0

                    if images != []:
                        for backdrop in images:
                            # only get first image
                            while not count == 1:
                                try:
                                    info = {}
                                    info["url"] = downloadUtils.getArtwork(col_item, "Backdrop")
                                    info["type"] = MB3type
                                    info["index"] = index
                                    info["id"] = id
                                    info["parent"] = parentID
                                    info["name"] = name
                                    links.append(info)
                                    if self.doDebugLog:
                                        self.logMsg("[MB3 SkinHelper Backdrop:] -- " + name + " -- " + info["url"])
                                    index = index + 1
    
                                    stored_item["links"] = links
                                    artLinks[id] = stored_item
                                    
                                except Exception, e:
                                    self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))
                                count += 1


                else:
                    stored_item["collections"].append(item.get("Name"))


            # Process collection item Photos
            self.logMsg("[MB3 SkinHelper get Collection Images Photos]")
            collectionUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?Limit=20&SortOrder=Descending&ParentId=" + item.get("Id") + "&IncludeItemTypes=Photo&Fields=ParentId,Overview&SortOrder=Descending&Recursive=true&CollapseBoxSetItems=false&format=json"
            jsonData = downloadUtils.downloadUrl(collectionUrl, suppress=True, popup=0 )  
            collectionResult = json.loads(jsonData)

            self.logMsg("[MB3 SkinHelper COLLECTION] -- " + item.get("Name") + " -- " + collectionUrl)

            collectionResult = collectionResult.get("Items")
            if(collectionResult == None):
                collectionResult = []   

            for col_item in collectionResult:

                id = col_item.get("Id")
                name = col_item.get("Name")
                MB3type = col_item.get("Type")
                images = col_item.get("ImageTags")

                stored_item = artLinks.get(id)

                if(stored_item == None):

                    stored_item = {}
                    collections = []
                    collections.append(item.get("Name"))
                    stored_item["collections"] = collections
                    links = []
                    images = col_item.get("ImageTags")
                    parentID = col_item.get("ParentId")
                    name = col_item.get("Name")
                    if (images == None):
                        images = []

                    index = 0

                    if(col_item.get("Type") == "Photo"):
                        for imagetag in images:
                            try:
                                info = {}
                                info["url"] = downloadUtils.getArtwork(col_item, "Primary")
                                info["type"] = MB3type
                                info["index"] = index
                                info["id"] = id
                                info["parent"] = parentID
                                info["name"] = name
                                links.append(info)
                                index = index + 1
                                if self.doDebugLog:
                                    self.logMsg("[MB3 SkinHelper Photo Thumb:] -- " + name + " -- " + info["url"])
                                stored_item["links"] = links
                                artLinks[id] = stored_item
                            except Exception, e:
                                self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))


                        stored_item["links"] = links
                        artLinks[id] = stored_item
                else:
                    stored_item["collections"].append(item.get("Name"))
                    
            
            # Process collection item Music and all Other
            self.logMsg("[MB3 SkinHelper get Collection Images Other]")
            collectionUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/items?&SortOrder=Descending&ParentId=" + item.get("Id") + "&IncludeItemTypes=MusicArtist,MusicAlbum,Audio&Fields=ParentId,Overview&SortOrder=Descending&Recursive=true&CollapseBoxSetItems=false&format=json"
            jsonData = downloadUtils.downloadUrl(collectionUrl, suppress=True, popup=0 )  
            collectionResult = json.loads(jsonData)

            self.logMsg("[MB3 SkinHelper COLLECTION] -- " + item.get("Name") + " -- " + collectionUrl)

            collectionResult = collectionResult.get("Items")
            if(collectionResult == None):
                collectionResult = []   

            for col_item in collectionResult:

                id = col_item.get("Id")
                name = col_item.get("Name")
                MB3type = col_item.get("Type")
                images = col_item.get("ImageTags")
                
                stored_item = artLinks.get(id)
                
                if(stored_item == None):
                    stored_item = {}
                    collections = []
                    collections.append(item.get("Name"))
                    stored_item["collections"] = collections
                    links = []
                    images2 = col_item.get("ImageTags")
                    images = col_item.get("BackdropImageTags")
                    parentID = col_item.get("ParentId")
                    name = col_item.get("Name")
                    if (images == None):
                        images = []
                    if (images == None):
                        images2 = []                    

                    index = 0
                    
                    for imagetag in images:
                        try:
                            info = {}
                            info["url"] = downloadUtils.getArtwork(col_item, "Backdrop", index=str(index))
                            info["type"] = MB3type
                            info["index"] = index
                            info["id"] = id
                            info["parent"] = parentID
                            info["name"] = name
                            links.append(info)
                            index = index + 1
                            if self.doDebugLog:
                                self.logMsg("[MB3 SkinHelper Backdrop:] -- " + name + " -- " + info["url"])
                            stored_item["links"] = links
                            artLinks[id] = stored_item
                        except Exception, e:
                            self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))                    
                    
                    if images == []:
                        for imagetag in images2:
                            try:
                                info = {}
                                info["url"] = downloadUtils.getArtwork(col_item, "Primary", index=str(index))
                                info["type"] = MB3type
                                info["index"] = index
                                info["id"] = id
                                info["parent"] = parentID
                                info["name"] = name
                                links.append(info)
                                index = index + 1
                                if self.doDebugLog:
                                    self.logMsg("[MB3 SkinHelper Primary:] -- " + name + " -- " + info["url"])
                                stored_item["links"] = links
                                artLinks[id] = stored_item
                            except Exception, e:
                                self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))
                                              

                        stored_item["links"] = links
                        artLinks[id] = stored_item
                else:
                    stored_item["collections"].append(item.get("Name"))            

        collection_count = collection_count + 1

        # build global link list
        final_global_art = []

        for id in artLinks:
            item = artLinks.get(id)
            collections = item.get("collections")
            links = item.get("links")

            for link_item in links:
                link_item["collections"] = collections
                final_global_art.append(link_item)

        self.global_art_links = final_global_art
        random.shuffle(self.global_art_links)

        return True        


    # set a new background image on a item
    def setBackgroundLink(self, windowPropertyName, filterOnCollectionName):

        WINDOW = xbmcgui.Window( 10000 )
        backGroundUrl = ""

        if (filterOnCollectionName == "favoritemovies"):
            if(len(self.favorites_art_links) > 0):
                next, nextItem = self.findNextLink(self.favorites_art_links, self.current_fav_art, "")
                self.current_fav_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "favoriteshows"):
            if(len(self.favoriteshows_art_links) > 0):
                next, nextItem = self.findNextLink(self.favoriteshows_art_links, self.current_favshow_art, "")
                self.current_favshow_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "channels"):
            if(len(self.channels_art_links) > 0):
                next, nextItem = self.findNextLink(self.channels_art_links, self.current_channel_art, "")
                self.current_channel_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "musicvideos"):
            if(len(self.musicvideo_art_links) > 0):
                next, nextItem = self.findNextLink(self.musicvideo_art_links, self.current_musicvideo_art, "")
                self.current_musicvideo_art = next
                backGroundUrl = nextItem["url"]
        elif (filterOnCollectionName == "photos"):
            if(len(self.photo_art_links) > 0):
                next, nextItem = self.findNextLink(self.photo_art_links, self.current_photo_art, "")
                self.current_photo_art = next
                backGroundUrl = nextItem["url"]
        else:
            if(len(self.global_art_links) > 0):
                next, nextItem = self.findNextLink(self.global_art_links, self.current_global_art, filterOnCollectionName)
                self.current_global_art = next
                backGroundUrl = nextItem["url"]
                
        if "/10000/10000/" in backGroundUrl:        
            backGroundUrl = backGroundUrl.split("/10000/10000/",1)[0]
            backGroundUrl_small = backGroundUrl
            backGroundUrl = backGroundUrl + "/1920/1080/0?"
            backGroundUrl_small = backGroundUrl_small + "/620/350/0?"
        else:
            backGroundUrl_small = backGroundUrl
        
        WINDOW.setProperty(windowPropertyName, backGroundUrl)
        WINDOW.setProperty(windowPropertyName + ".small", backGroundUrl_small)

    
    #get background images for specific content types
    def updateTypeArtLinks(self):

        from DownloadUtils import DownloadUtils
        downloadUtils = DownloadUtils()        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')

        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')
        WINDOW = xbmcgui.Window( 10000 )
        userid = WINDOW.getProperty("userid")                               

        if userName == "":
            self.logMsg("[MB3 SkinHelper] -- xbmb3c username empty, skipping task")
            return False
        else:
            self.logMsg("[MB3 SkinHelper] updateTypeArtLinks-- xbmb3c username: " + userName)

        # load Favorite Movie BG's
        favMoviesUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=20&Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=Movie&Filters=IsFavorite&format=json"
        xbmc.log("fav mov:"+favMoviesUrl)
        jsonData = downloadUtils.downloadUrl(favMoviesUrl, suppress=True, popup=0 )
        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            count = 0
            for backdrop in images:
                while not count == 1:
                    try:                
                        info = {}
                        info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                        info["index"] = index
                        info["id"] = id
                        info["parent"] = parentID
                        info["name"] = name
                        self.logMsg("BG Favorite Movie Image Info : " + str(info), level=0)
        
                        if (info not in self.favorites_art_links):
                            self.favorites_art_links.append(info)
                        index = index + 1
                    except Exception, e:
                        self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))
                    count += 1                    

        random.shuffle(self.favorites_art_links)       

        # load Favorite TV Show BG's
        favShowsUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=20&Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=Series&Filters=IsFavorite&format=json"
        jsonData = downloadUtils.downloadUrl(favShowsUrl, suppress=True, popup=0 )
        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            count = 0
            for backdrop in images:
                while not count == 1:
                    try:                
                        info = {}
                        info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                        info["index"] = index
                        info["id"] = id
                        info["parent"] = parentID
                        info["name"] = name
                        self.logMsg("BG Favorite Shows Image Info : " + str(info), level=0)
        
                        if (info not in self.favoriteshows_art_links):
                            self.favoriteshows_art_links.append(info)
                        index = index + 1
                    except Exception, e:
                        self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))
                    count += 1                    

        random.shuffle(self.favoriteshows_art_links)    

        # load Music Video BG's
        musicMoviesUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=40&SortOrder=Descending&Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=MusicVideo&format=json"
        jsonData = downloadUtils.downloadUrl(musicMoviesUrl, suppress=True, popup=0 )
        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            if (images == None):
                images = []
            index = 0
            count = 0
            for backdrop in images:
                while not count == 1:
                    try:                
                        info = {}
                        info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                        info["index"] = index
                        info["id"] = id
                        info["parent"] = parentID
                        info["name"] = name
                        self.logMsg("BG MusicVideo Image Info : " + str(info), level=0)
        
                        if (info not in self.musicvideo_art_links):
                            self.musicvideo_art_links.append(info)
                        index = index + 1
                    except Exception, e:
                            self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))
                    count += 1                    

        random.shuffle(self.musicvideo_art_links)

        # load Photo BG's
        photosUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Limit=20&SortOrder=Descending&Fields=ParentId,Overview&CollapseBoxSetItems=false&Recursive=true&IncludeItemTypes=Photo&format=json"
        jsonData = downloadUtils.downloadUrl(photosUrl, suppress=True, popup=0 )
        result = json.loads(jsonData)

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            index = 0
            
            try: 
                info = {}
                info["url"] = downloadUtils.getArtwork(item, "Primary", index=str(index))
                info["index"] = index
                info["id"] = id
                info["parent"] = parentID
                info["name"] = name
    
                if (info not in self.photo_art_links):
                    self.photo_art_links.append(info)
                index = index + 1
            except Exception, e:
                    self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))         

        random.shuffle(self.photo_art_links)       

        # load Channels BG links
        channelsUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Channels?&SortOrder=Descending&format=json"
        jsonData = downloadUtils.downloadUrl(channelsUrl, suppress=True, popup=0 )
        result = json.loads(jsonData)        

        result = result.get("Items")
        if(result == None):
            result = []   

        for item in result:
            images = item.get("BackdropImageTags")
            id = item.get("Id")
            parentID = item.get("ParentId")
            name = item.get("Name")
            plot = item.get("Overview")
            if (images == None):
                images = []
            index = 0
            for backdrop in images:
                try:
                    info = {}
                    info["url"] = downloadUtils.getArtwork(item, "Backdrop", index=str(index))
                    info["index"] = index
                    info["id"] = id
                    info["plot"] = plot
                    info["parent"] = parentID
                    info["name"] = name
                    self.logMsg("BG Channel Image Info : " + str(info), level=0)
                except Exception, e:
                        self.logMsg("[MB3 SkinHelper] error occurred: " + str(e))             

            if (info not in self.channels_art_links):
                self.channels_art_links.append(info)    
            index = index + 1

        random.shuffle(self.channels_art_links)

        return True
    
    # primitive cache by getting last known images from skin-settings           
    def getImagesFromCache(self):
        WINDOW = xbmcgui.Window( 10000 )
        self.logMsg("[MB3 skin helper] get properties from cache...")
        
        # user collections
        totalUserLinks = int(WINDOW.getProperty("MediaBrowser.usr.Count"))
        linkCount = 0
        while linkCount !=totalUserLinks:
            mbstring = "MediaBrowser.usr." + str(linkCount)
            if xbmc.getInfoLabel("Skin.String(" + mbstring + '.background)') != "":
                WINDOW.setProperty(mbstring + '.background', xbmc.getInfoLabel("Skin.String(" + mbstring + '.background)'))
                WINDOW.setProperty(mbstring + '.background.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.background.small)'))
            linkCount += 1
        
        #global backgrounds
        mbstring = "MB3.Background.FavouriteMovies.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.FavouriteShows.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.Channels.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.MusicVideos.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.Photos.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.Movie.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.TV.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))
        mbstring = "MB3.Background.Music.FanArt"
        WINDOW.setProperty(mbstring, xbmc.getInfoLabel("Skin.String(" + mbstring + ')'))
        WINDOW.setProperty(mbstring + '.small', xbmc.getInfoLabel("Skin.String(" + mbstring + '.small)'))

    # primitive cache by storing last known images in skin-settings
    def setImagesInCache(self):         
        WINDOW = xbmcgui.Window( 10000 )
        
        #user collections
        totalUserLinks = 10
        totalUserLinks = int(WINDOW.getProperty("MediaBrowser.usr.Count"))
        linkCount = 0
        while linkCount !=totalUserLinks:
            mbstring = "MediaBrowser.usr." + str(linkCount)
            xbmc.executebuiltin('Skin.SetString(' + mbstring + '.background,' + WINDOW.getProperty(mbstring + '.background') + ")")
            xbmc.executebuiltin('Skin.SetString(' + mbstring + '.background.small,' + WINDOW.getProperty(mbstring + '.background.small') + ")")
            linkCount += 1
            
        #global backgrounds
        mbstring = "MB3.Background.FavouriteMovies.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.FavouriteShows.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.Channels.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.MusicVideos.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.Photos.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.Movie.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.TV.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        mbstring = "MB3.Background.Music.FanArt"
        xbmc.executebuiltin('Skin.SetString(' + mbstring + ',' + WINDOW.getProperty(mbstring) + ")")
        xbmc.executebuiltin('Skin.SetString(' + mbstring + '.small,' + WINDOW.getProperty(mbstring + '.small') + ")")
        
    
    def SetMB3WindowProperties(self, filter=None, shared=False ):
        self.logMsg("[MB3 SkinHelper] setting skin properties...")
        
        try:
            #Get the global host variable set in settings
            WINDOW = xbmcgui.Window( 10000 )
            sectionCount=0
            usrMoviesCount=0
            usrMusicCount=0
            usrTVshowsCount=0
            stdMoviesCount=0
            stdTVshowsCount=0
            stdMusicCount=0
            stdPhotoCount=0
            stdChannelsCount=0
            stdPlaylistsCount=0
            stdSearchCount=0
            dirItems = []
            
            # some default settings (todo: get this from a skin setting)
            collapseBoxSets = True #todo: get this from (skin)settings
            useNextUpforInProgressTvShowsWidget = True #todo: get this from (skin)settings
            
            allSections = MainModule.getCollections(MainModule.getDetailsString())
            collectionCount = 0
            mode=0
            
            for section in allSections:
            
                details={'title' : section.get('title', 'Unknown') }

                extraData={ 'fanart_image' : '' ,
                            'type'         : "Video" ,
                            'thumb'        : '' ,
                            'token'        : section.get('token',None) }

                extraData['mode']=mode
                modeurl="&mode=0"
                s_url='http://%s%s' % (section['address'], section['path'])
                murl= "?url="+urllib.quote(s_url)+modeurl
                searchurl = "?url="+urllib.quote(s_url)+"&mode=2"

                #Build that listing..
                total = section.get('total')
                if (total == None):
                    total = 0
                
                window=""
                if section.get('sectype')=='photo':
                    window="Pictures"
                elif section.get('sectype')=='music':
                    window="MusicLibrary "
                else:
                    window="VideoLibrary"
                
                #get user collections
                if not "std." in section.get('sectype'):
                    collectionCount += 1
                    #get user collections - NOT indexed by type
                    WINDOW.setProperty("MediaBrowser.usr.%d.title"               % (sectionCount) , section.get('title', 'Unknown'))
                    WINDOW.setProperty("MediaBrowser.usr.%d.path"                % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                    WINDOW.setProperty("MediaBrowser.usr.%d.type"                % (sectionCount) , section.get('section'))
                    WINDOW.setProperty("MediaBrowser.usr.%d.fanart"              % (sectionCount) , section.get('fanart_image'))
                    WINDOW.setProperty("MediaBrowser.usr.%d.recent.path"         % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
                    WINDOW.setProperty("MediaBrowser.usr.%d.recent.content"      % (sectionCount) , "plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl)
                    WINDOW.setProperty("MediaBrowser.usr.%d.total" % (sectionCount) , str(total))
                    if section.get('sectype')=='movies':
                        if collapseBoxSets == True:
                            WINDOW.setProperty("MediaBrowser.usr.%d.path"      % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('collapsed_path', '')) + modeurl + ",return)")
                    if section.get('sectype')=='tvshows':
                        WINDOW.setProperty("MediaBrowser.usr.%d.nextepisodes.path"   % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.%d.nextepisodes.content"   % (sectionCount) , "plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl)
                    if section.get('sectype')!='photo' and section.get('sectype')!='music':
                        WINDOW.setProperty("MediaBrowser.usr.%d.unwatched.path"      % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.%d.unwatched.content"      % (sectionCount) , "plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl)
                        WINDOW.setProperty("MediaBrowser.usr.%d.inprogress.path"     % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.%d.inprogress.content"     % (sectionCount) , "plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl)
                        WINDOW.setProperty("MediaBrowser.usr.%d.genre.path"          % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
                    if useNextUpforInProgressTvShowsWidget == True and section.get('sectype')=='tvshows':
                        WINDOW.setProperty("MediaBrowser.usr.%d.inprogress.content"     % (sectionCount) , "plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl)
          
                    #get user collections - indexed by type
                    if section.get('sectype')=='movies':
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.title"         % (usrMoviesCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.path"          % (usrMoviesCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.type"          % (usrMoviesCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.content"       % (usrMoviesCount) , "plugin://plugin.video.xbmb3c/" + murl)
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.recent.path"         % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.unwatched.path"      % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.inprogress.path"     % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.movies.%d.genre.path"          % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
                        usrMoviesCount +=1
                        
                    if section.get('sectype')=='tvshows':
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.title"        % (usrTVshowsCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.path"         % (usrTVshowsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.type"         % (usrTVshowsCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.content"       % (usrTVshowsCount) , "plugin://plugin.video.xbmb3c/" + murl)
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.recent.path"         % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.unwatched.path"      % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.inprogress.path"     % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.genre.path"          % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
                        WINDOW.setProperty("MediaBrowser.usr.tvshows.%d.nextepisodes.path"   % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl + ",return)")
                        usrTVshowsCount +=1
                        
                    if section.get('sectype')=='music':
                        WINDOW.setProperty("MediaBrowser.usr.music.%d.title"        % (usrMusicCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.usr.music.%d.path"         % (usrMusicCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.usr.music.%d.type"         % (usrMusicCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.usr.music.%d.content"       % (usrMusicCount) , "plugin://plugin.video.xbmb3c/" + murl)
                        usrMusicCount +=1
                    
                else:    
                    # get standard MB3 root items
                    if section.get('sectype')=='std.movies':
                        WINDOW.setProperty("MediaBrowser.std.movies.%d.title"               % (stdMoviesCount) , section.get('title', 'Unknown'))
                        if collapseBoxSets == True:
                            collapsed_url = murl.replace("&mode=0", "")
                            collapsed_url = collapsed_url + "%26CollapseBoxSetItems%3Dtrue&mode=0"
                        else:
                            collapsed_url = murl
                        WINDOW.setProperty("MediaBrowser.std.movies.%d.path"                % (stdMoviesCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + collapsed_url+",return)")
                        WINDOW.setProperty("MediaBrowser.std.movies.%d.content"                % (stdMoviesCount) , "plugin://plugin.video.xbmb3c/" + murl)
                        WINDOW.setProperty("MediaBrowser.std.movies.%d.type"                % (stdMoviesCount) , section.get('section'))
                        stdMoviesCount +=1
                    elif section.get('sectype')=='std.tvshows':
                        WINDOW.setProperty("MediaBrowser.std.tvshows.%d.title"        % (stdTVshowsCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.tvshows.%d.path"         % (stdTVshowsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.tvshows.%d.type"         % (stdTVshowsCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.std.tvshows.%d.content"       % (stdTVshowsCount) , "plugin://plugin.video.xbmb3c/" + murl)
                        stdTVshowsCount +=1    
                    elif section.get('sectype')=='std.music':
                        WINDOW.setProperty("MediaBrowser.std.music.%d.title"        % (stdMusicCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.music.%d.path"         % (stdMusicCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.music.%d.type"         % (stdMusicCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.std.music.%d.content"       % (stdMusicCount) , "plugin://plugin.video.xbmb3c/" + murl)  
                        stdMusicCount +=1     
                    elif section.get('sectype')=='std.photo':
                        WINDOW.setProperty("MediaBrowser.std.photo.%d.title"        % (stdPhotoCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.photo.%d.path"         % (stdPhotoCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.photo.%d.type"         % (stdPhotoCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.std.photo.%d.content"       % (stdPhotoCount) , "plugin://plugin.video.xbmb3c/" + murl) 
                        stdPhotoCount +=1
                    elif section.get('sectype')=='std.channels':
                        WINDOW.setProperty("MediaBrowser.std.channels.%d.title"        % (stdChannelsCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.channels.%d.path"         % (stdChannelsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.channels.%d.type"         % (stdChannelsCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.std.channels.%d.content"       % (stdChannelsCount) , "plugin://plugin.video.xbmb3c/" + murl)  
                        stdChannelsCount +=1
                    elif section.get('sectype')=='std.playlists':
                        WINDOW.setProperty("MediaBrowser.std.playlists.%d.title"        % (stdPlaylistsCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.playlists.%d.path"         % (stdPlaylistsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.playlists.%d.type"         % (stdPlaylistsCount) , section.get('section'))
                        WINDOW.setProperty("MediaBrowser.std.playlists.%d.content"       % (stdPlaylistsCount) , "plugin://plugin.video.xbmb3c/" + murl)  
                        stdPlaylistsCount +=1
                    elif section.get('sectype')=='std.search':
                        WINDOW.setProperty("MediaBrowser.std.search.%d.title"        % (stdSearchCount) , section.get('title', 'Unknown'))
                        WINDOW.setProperty("MediaBrowser.std.search.%d.path"         % (stdSearchCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + searchurl+",return)")
                        WINDOW.setProperty("MediaBrowser.std.search.%d.type"         % (stdSearchCount) , section.get('section')) 
                        stdSearchCount +=1 
                sectionCount += 1 
            WINDOW.setProperty("MediaBrowser.usr.Count", str(collectionCount))
        except Exception, e:
            self.logMsg("[MB3 SkinHelper] exception in SetMB3WindowProperties: " + str(e))
            return False

        return True
    
    def updateGlobalBackgrounds(self):
        win = xbmcgui.Window( 10000 )
        
        # add small thumb to global items
        backGroundString = "MB3.Background.Music.FanArt"
        backGroundUrl = win.getProperty(backGroundString)
        if "/10000/10000/" in backGroundUrl:
            backGroundUrl = backGroundUrl.split("/10000/10000/",1)[0]
            backGroundUrl = backGroundUrl + "/620/350/0"
        win.setProperty(backGroundString + ".small", backGroundUrl)
        
        backGroundString = "MB3.Background.Movie.FanArt"
        backGroundUrl = win.getProperty(backGroundString)
        if "/10000/10000/" in backGroundUrl:
            backGroundUrl = backGroundUrl.split("/10000/10000/",1)[0]
            backGroundUrl = backGroundUrl + "/620/350/0"
        win.setProperty(backGroundString + ".small", backGroundUrl)
        
        backGroundString = "MB3.Background.TV.FanArt"
        backGroundUrl = win.getProperty(backGroundString)
        if "/10000/10000/" in backGroundUrl:
            backGroundUrl = backGroundUrl.split("/10000/10000/",1)[0]
            backGroundUrl = backGroundUrl + "/620/350/0"
        win.setProperty(backGroundString + ".small", backGroundUrl)
            
      