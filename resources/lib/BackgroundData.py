#################################################################################################
# Background Data Updater
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils
from Database import Database
from API import API

_MODE_BASICPLAY=12
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')

#define our global download utils
downloadUtils = DownloadUtils()
db = Database()

class BackgroundDataUpdaterThread(threading.Thread):

    logLevel = 0
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')   
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)
        if(self.logLevel == 2):
            self.LogCalls = True
        xbmc.log("XBMB3C BackgroundDataUpdaterThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C BackgroundDataUpdaterThread -> " + msg)
                
    def run(self):
        self.logMsg("Started")
        
        self.updateBackgroundData()
        lastRun = datetime.today()
        lastProfilePath = xbmc.translatePath('special://profile')
        
        while (xbmc.abortRequested == False):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            profilePath = xbmc.translatePath('special://profile')
            
            updateInterval = 600
                
            if((secTotal > updateInterval or lastProfilePath != profilePath) and not xbmc.Player().isPlaying()):
                self.updateBackgroundData()
                lastRun = datetime.today()

            lastProfilePath = profilePath
            
            xbmc.sleep(30000)
                        
        self.logMsg("Exited")
        
    def updateBackgroundData(self):
        self.logMsg("updateBackgroundData Called")
        db.set("itemString","")
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userid = downloadUtils.getUserId()
        
        self.logMsg("UserName : " + userName + " UserID : " + userid)
        
        self.logMsg("Updating BackgroundData Movie List")
        WINDOW = xbmcgui.Window( 10000 )
        dataUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items?Recursive=true&SortBy=SortName&Fields=Path,People,Genres,MediaStreams,Overview,ShortOverview,CriticRatingSummary,EpisodeCount,SeasonCount,Studios,CumulativeRunTimeTicks,Metascore,SeriesStudio&SortOrder=Ascending&Filters=IsNotFolder&ExcludeLocationTypes=Virtual&IncludeItemTypes=Movie&format=json"
         
        jsonData = downloadUtils.downloadUrl(dataUrl, suppress=False, popup=1 )
        result = json.loads(jsonData)
        self.logMsg("BackgroundData Movie Json Data : " + str(result), level=2)
        
        result = result.get("Items")
        if(result == None):
            result = []
        item_count = 1
        for item in result:
            self.updateDB(item)
            
    def updateDB(self, item):
        id=item.get("Id")
        itemString=db.get("itemString")
        if itemString=='':
            itemString=id
        else:
            itemString=itemString + "," +id
        db.set("itemString", itemString)
        Temp = item.get("Name")
        if Temp == None:
            Temp = ""
        Name=Temp.encode('utf-8')
        db.set(id+".Name",Name)
        Temp = item.get("Overview")
        if Temp == None:
            Temp=''
        Overview1=Temp.encode('utf-8')
        Overview=str(Overview1)
        mediaStreams=API().getMediaStreams(item)
        db.set(id+".Overview",Overview)
        db.set(id+".OfficialRating",item.get("OfficialRating"))
        CommunityRating=item.get("CommunityRating")
        if CommunityRating != None:
            db.set(id+".CommunityRating",       str(CommunityRating))
        db.set(id+".CriticRating",              str(item.get("CriticRating")))
        db.set(id+".ProductionYear",            str(item.get("ProductionYear")))
        db.set(id+".LocationType",              item.get("LocationType"))
        db.set(id+".Primary",                   downloadUtils.getArtwork(item, "Primary")) 
        db.set(id+".Backdrop",                  downloadUtils.getArtwork(item, "Backdrop"))
        db.set(id+".poster",                    downloadUtils.getArtwork(item, "poster")) 
        db.set(id+".tvshow.poster",             downloadUtils.getArtwork(item, "tvshow.poster")) 
        db.set(id+".Banner",                    downloadUtils.getArtwork(item, "Banner")) 
        db.set(id+".Logo",                      downloadUtils.getArtwork(item, "Logo")) 
        db.set(id+".Disc",                      downloadUtils.getArtwork(item, "Disc")) 
        db.set(id+".Art",                       downloadUtils.getArtwork(item, "Art")) 
        db.set(id+".Thumb",                     downloadUtils.getArtwork(item, "Thumb")) 
        db.set(id+".Thumb3",                    downloadUtils.getArtwork(item, "Thumb3")) 
        db.set(id+".Primary2",                  downloadUtils.getArtwork(item, "Primary2")) 
        db.set(id+".Primary4",                  downloadUtils.getArtwork(item, "Primary4")) 
        db.set(id+".Primary3",                  downloadUtils.getArtwork(item, "Primary3")) 
        db.set(id+".Backdrop2",                 downloadUtils.getArtwork(item, "Backdrop2")) 
        db.set(id+".Backdrop3",                 downloadUtils.getArtwork(item, "Backdrop3")) 
        db.set(id+".BackdropNoIndicators",      downloadUtils.getArtwork(item, "BackdropNoIndicators"))                
        db.set(id+".Channels",                  mediaStreams.get('channels'))
        db.set(id+".VideoCodec",                mediaStreams.get('videocodec'))
        db.set(id+".AspectRatio",               mediaStreams.get('aspectratio'))
        db.set(id+".AudioCodec",                mediaStreams.get('audiocodec'))
        db.set(id+".Height",                    mediaStreams.get('height'))
        db.set(id+".Width",                     mediaStreams.get('width'))       
        db.set(id+".ItemType",                  item.get("Type"))
        if(item.get("PremiereDate") != None):
            premieredatelist = (item.get("PremiereDate")).split("T")
            db.set(id+".PremiereDate",              premieredatelist[0])
        else:
            premieredate = ""

        # Process Genres
        genre = ""
        genres = item.get("Genres")
        if(genres != None and genres != []):
            for genre_string in genres:
                if genre == "": 
                    genre = genre_string
                elif genre_string != None:
                    genre = genre + " / " + genre_string   
        db.set(id+".Genre",                     genre)
        

        db.set(id+".Studio",                    API().getStudio(item))

        #Process User Data
        userData = item.get("UserData")
        resumeTime = 0
        if(userData != None):
            if userData.get("Played") != True:
                db.set(id+".Watched",           "True")
            else:
                db.set(id+".Watched",           "False")
            if userData.get("IsFavorite") == True:
                db.set(id+".Favorite",          "True")
            else:
                db.set(id+".Favorite",          "False")
            if userData.get("PlaybackPositionTicks") != None:
                PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
                reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
                resumeTime = str(reasonableTicks / 10000)
                db.set(id+".ResumeTime",        resumeTime)
            if(userData.get("Played") == True):
                db.set(id+".PlayCount",            "1")
            else:
                db.set(id+".PlayCount",            "0")
                
        duration, percent = API().getDuration(item)#Process Duration
        db.set(id + ".Duration",                duration)
        db.set(id + ".CompletePercentage",      percent)
        # add resume percentage text to titles
        if (__settings__.getSetting('addResumePercent') == 'true' and Name != '' and percent != None):
            db.set(id+".Name", Name + " (" + percent + "%)")

        director, writer, cast = API().getPeople(item)
        db.set(id+".Director",              director)
        db.set(id+".Writer",                writer)
        #db.set(id+".Cast",                  cast)        
 