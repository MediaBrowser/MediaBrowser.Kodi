import xbmc
import xbmcgui
import xbmcaddon
import urllib
import httplib
import os
import time
import socket
import inspect
import sys
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

__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = xbmcaddon.Addon(id='plugin.video.xbmb3c').getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__language__     = __addon__.getLocalizedString
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)
base_window = xbmcgui.Window( 10000 )

from InfoUpdater import InfoUpdaterThread
from NextUpItems import NextUpUpdaterThread
from SuggestedItems import SuggestedUpdaterThread
from RandomItems import RandomInfoUpdaterThread
from ArtworkLoader import ArtworkRotationThread
from ThemeMedia import ThemeMediaThread
from RecentItems import RecentInfoUpdaterThread
from InProgressItems import InProgressUpdaterThread
from WebSocketClient import WebSocketThread
from ClientInformation import ClientInformation
from MenuLoad import LoadMenuOptionsThread
from PlaylistItems import PlaylistItemUpdaterThread
from DownloadUtils import DownloadUtils
from BackgroundData import BackgroundDataUpdaterThread
from Utils import PlayUtils
from SkinHelperThread import SkinHelperThread

downloadUtils = DownloadUtils()

skinHelperThread = None
newInProgressThread = None
newRecentInfoThread = None
newRandomInfoThread = None
newNextUpThread = None
newSuggestedThread = None
newWebSocketThread = None
newMenuThread = None
artworkRotationThread = None
newThemeMediaThread = None
newInfoThread = None
newPlaylistsThread = None
newBackgroundDataThread = None

logLevel = 0
try:
    logLevel = int(__settings__.getSetting('logLevel'))   
except:
    pass

def printDebug( msg, level = 1):
    if(logLevel >= level):
        if(logLevel == 2):
            try:
                xbmc.log("XBMB3C " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg))
            except UnicodeEncodeError:
                xbmc.log("XBMB3C " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')))
        else:
            try:
                xbmc.log("XBMB3C " + str(level) + " -> " + str(msg))
            except UnicodeEncodeError:
                xbmc.log("XBMB3C " + str(level) + " -> " + str(msg.encode('utf-8')))


###########################################################################  
##Start of Service
###########################################################################
    
def ServiceEntryPoint():
    # auth the service
    try:
        downloadUtils.authenticate()
    except Exception, e:
        pass
    
    # start some worker threads
    if __addon__.getSetting('useSkinHelper') == "true":
        skinHelperThread = SkinHelperThread()
        skinHelperThread.start()
    else:
        printDebug("XBMB3C Service SkinHelperThread Disabled")
        skinHelperThread = None
    
    if __addon__.getSetting('useInProgressUpdater') == "true":
        newInProgressThread = InProgressUpdaterThread()
        newInProgressThread.start()
    else:
        printDebug("XBMB3C Service InProgressUpdater Disabled")
        newInProgressThread = None
      
    if __addon__.getSetting('useRecentInfoUpdater') == "true":
        newRecentInfoThread = RecentInfoUpdaterThread()
        newRecentInfoThread.start()
    else:
        printDebug("XBMB3C Service RecentInfoUpdater Disabled")
        newRecentInfoThread = None
    
    if __addon__.getSetting('useRandomInfo') == "true":
        newRandomInfoThread = RandomInfoUpdaterThread()
        newRandomInfoThread.start()
    else:
        printDebug("XBMB3C Service RandomInfo Disabled")
        newRandomInfoThread = None
    
    if __addon__.getSetting('useNextUp') == "true":
        newNextUpThread = NextUpUpdaterThread()
        newNextUpThread.start()
    else:
        printDebug("XBMB3C Service NextUp Disabled")    
        newNextUpThread = None
        
    if __addon__.getSetting('useSuggested') == "true":
        newSuggestedThread = SuggestedUpdaterThread()
        newSuggestedThread.start()
    else:
        printDebug("XBMB3C Service Suggested Disabled")   
        newSuggestedThread = None
    
    if __addon__.getSetting('useWebSocketRemote') == "true":
        newWebSocketThread = WebSocketThread()
        newWebSocketThread.start()
    else:
        printDebug("XBMB3C Service WebSocketRemote Disabled")
        newWebSocketThread = None
    
    if __addon__.getSetting('useMenuLoader') == "true":
        newMenuThread = LoadMenuOptionsThread()
        newMenuThread.start()
    else:
        printDebug("XBMB3C Service MenuLoader Disabled")
        newMenuThread = None
    
    if __addon__.getSetting('useBackgroundLoader') == "true":
        artworkRotationThread = ArtworkRotationThread()
        artworkRotationThread.start()
    else:
        printDebug("XBMB3C Service BackgroundLoader Disabled")
        artworkRotationThread = None
        
    if __addon__.getSetting('useThemeMovies') == "true" or __addon__.getSetting('useThemeMusic') == "true":
        newThemeMediaThread = ThemeMediaThread()
        newThemeMediaThread.start()
    else:
        printDebug("XBMB3C Service ThemeMedia Disabled")
        newThemeMediaThread = None
     
    if __addon__.getSetting('useInfoLoader') == "true":
        newInfoThread = InfoUpdaterThread()
        newInfoThread.start()
    else:
        printDebug("XBMB3C Service InfoLoader Disabled")
        newInfoThread = None
        
    if __addon__.getSetting('usePlaylistsUpdater') == "true":
        newPlaylistsThread = PlaylistItemUpdaterThread()
        newPlaylistsThread.start()
    else:
        printDebug("XBMB3C Service PlaylistsUpdater Disabled")
        newPlaylistsThread = None
    
    if __addon__.getSetting('useBackgroundData') == "true":
        newBackgroundDataThread = BackgroundDataUpdaterThread()
        newBackgroundDataThread.start()
    else:
        printDebug("XBMB3C BackgroundDataUpdater Disabled")
        newBackgroundDataThread = None
    
    # start the service
    monitor = Service()
    lastProgressUpdate = datetime.today()
    
    addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    if socket.gethostname() != None and socket.gethostname() != '' and addonSettings.getSetting("deviceName") == 'XBMB3C':
        addonSettings.setSetting("deviceName", socket.gethostname())
    
    xbmc.log("XBMB3C Service -> Starting Service")
    
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
                    try:
                        monitor.reportPlayback()
                        #if(monitor.played_information.get(currentFile) != None and monitor.played_information.get(currentFile).get("item_id") != None):
                            #item_id =  monitor.played_information.get(currentFile).get("item_id")
                            #if(newWebSocketThread != None):
                                #newWebSocketThread.sendProgressUpdate(item_id, str(int(playTime * 10000000)))
                    except Exception, msg:
                        xbmc.log("XBMB3C Service -> Exception reporting progress : " + msg)
                        pass
                    lastProgressUpdate = datetime.today()
                
            except Exception, e:
                xbmc.log("XBMB3C Service -> Exception in Playback Monitor : " + str(e))
                pass
    
        xbmc.sleep(1000)
        xbmcgui.Window(10000).setProperty("XBMB3C_Service_Timestamp", str(int(time.time())))
    
    xbmc.log("XBMB3C Service -> Stopping Service")
    
    # stop all worker threads
    if(newWebSocketThread != None):
        newWebSocketThread.stopClient()    

    if(skinHelperThread != None):
        skinHelperThread.stop()
    if(newInProgressThread != None):
        newInProgressThread.stop()
    if(newRecentInfoThread != None):
        newRecentInfoThread.stop()
    if(newRandomInfoThread != None):
        newRandomInfoThread.stop()
    if(newNextUpThread != None):
        newNextUpThread.stop()
    if(newSuggestedThread != None):
        newSuggestedThread.stop()
    if(newMenuThread != None):
        newMenuThread.stop()
    if(artworkRotationThread != None):
        artworkRotationThread.stop()
    if(newThemeMediaThread != None):
        newThemeMediaThread.stopThread()
    if(newInfoThread != None):
        newInfoThread.stop()
    if(newPlaylistsThread != None):
        newPlaylistsThread.stop()
    if(newBackgroundDataThread != None):
        newBackgroundDataThread.stop()        
      
    xbmc.log("XBMB3C Service -> Service shutting down")

    
# service class for playback monitoring
class Service( xbmc.Player ):

    played_information = {}
    
    def deleteItem (self, url):
        return_value = xbmcgui.Dialog().yesno(__language__(30091),__language__(30092))
        if return_value:
            printDebug('Deleting via URL: ' + url)
            progress = xbmcgui.DialogProgress()
            progress.create(__language__(30052), __language__(30053))
            downloadUtils.downloadUrl(url, type="DELETE")
            progress.close()
            xbmc.executebuiltin("Container.Refresh")
            return 1
        else:
            return 0
        
    def hasData(self, data):
        if(data == None or len(data) == 0 or data == "None"):
            return False
        else:
            return True 
    
    def stopAll(self):

        if(len(self.played_information) == 0):
            return 
            
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        printDebug("XBMB3C Service -> played_information : " + str(self.played_information))
        
        for item_url in self.played_information:
            data = self.played_information.get(item_url)
            
            if(data != None):
                printDebug("XBMB3C Service -> item_url  : " + item_url)
                printDebug("XBMB3C Service -> item_data : " + str(data))
                
                deleteurl = data.get("deleteurl")
                runtime = data.get("runtime")
                currentPossition = data.get("currentPossition")
                item_id = data.get("item_id")
                refresh_id = data.get("refresh_id")
                currentFile = data.get("currentfile")
                
                if(refresh_id != None):
                    BackgroundDataUpdaterThread().updateItem(refresh_id)
                
                if(currentPossition != None and self.hasData(runtime)):
                    runtimeTicks = int(runtime)
                    printDebug("XBMB3C Service -> runtimeticks:" + str(runtimeTicks))
                    percentComplete = (currentPossition * 10000000) / runtimeTicks
                    markPlayedAt = float(addonSettings.getSetting("markPlayedAt")) / 100    

                    printDebug("XBMB3C Service -> Percent Complete:" + str(percentComplete) + " Mark Played At:" + str(markPlayedAt))
                    self.stopPlayback(data)
                    
                    if (percentComplete > markPlayedAt):
                        gotDeleted = 0
                        if(deleteurl != None and deleteurl != ""):
                            printDebug("XBMB3C Service -> Offering Delete:" + str(deleteurl))
                            gotDeleted = self.deleteItem(deleteurl)

        if(newNextUpThread != None):
            newNextUpThread.updateNextUp()
            
        if(artworkRotationThread != None):
            artworkRotationThread.updateActionUrls()
            
        self.played_information.clear()

        # stop transcoding - todo check we are actually transcoding?
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getMachineId()
        url = ("http://%s:%s/mediabrowser/Videos/ActiveEncodings" % (addonSettings.getSetting('ipaddress'), addonSettings.getSetting('port')))  
        url = url + '?DeviceId=' + txt_mac
        downloadUtils.downloadUrl(url, type="DELETE")
    
    def stopPlayback(self, data):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        item_id = data.get("item_id")
        audioindex = data.get("AudioStreamIndex")
        subtitleindex = data.get("SubtitleStreamIndex")
        playMethod = data.get("playmethod")
        currentPossition = data.get("currentPossition")
        positionTicks = str(int(currentPossition * 10000000))
                
        url = ("http://%s:%s/mediabrowser/Sessions/Playing/Stopped" % (addonSettings.getSetting('ipaddress'), addonSettings.getSetting('port')))  
            
        url = url + "?itemId=" + item_id

        url = url + "&canSeek=true"
        url = url + "&PlayMethod=" + playMethod
        url = url + "&QueueableMediaTypes=Video"
        url = url + "&MediaSourceId=" + item_id
        url = url + "&PositionTicks=" + positionTicks   
        if(audioindex != None and audioindex!=""):
          url = url + "&AudioStreamIndex=" + audioindex
            
        if(subtitleindex != None and subtitleindex!=""):
          url = url + "&SubtitleStreamIndex=" + subtitleindex
            
        downloadUtils.downloadUrl(url, postBody="", type="POST")    
    
    
    def reportPlayback(self):
        printDebug("reportPlayback Called")
        
        currentFile = xbmc.Player().getPlayingFile()
        playTime = xbmc.Player().getTime()
        
        data = self.played_information.get(currentFile)
        
        # only report playback if xbmb3c has initiated the playback (item_id has value)
        if(data != None and data.get("item_id") != None):
            addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
            
            item_id = data.get("item_id")
            audioindex = data.get("AudioStreamIndex")
            subtitleindex = data.get("SubtitleStreamIndex")
            playMethod = data.get("playmethod")
            paused = data.get("paused")
            
            url = ("http://%s:%s/mediabrowser/Sessions/Playing/Progress" % (addonSettings.getSetting('ipaddress'), addonSettings.getSetting('port')))  
                
            url = url + "?itemId=" + item_id

            url = url + "&canSeek=true"
            url = url + "&PlayMethod=" + playMethod
            url = url + "&QueueableMediaTypes=Video"
            url = url + "&MediaSourceId=" + item_id
            
            url = url + "&PositionTicks=" + str(int(playTime * 10000000))   
                
            if(audioindex != None and audioindex!=""):
              url = url + "&AudioStreamIndex=" + audioindex
                
            if(subtitleindex != None and subtitleindex!=""):
              url = url + "&SubtitleStreamIndex=" + subtitleindex
            
            if(paused == None):
                paused = "false"
            url = url + "&IsPaused=" + paused
           
            downloadUtils.downloadUrl(url, postBody="", type="POST")
    
    def __init__( self, *args ):
        printDebug("XBMB3C Service -> starting monitor service")
        self.played_information = {}
        pass
    
    def onPlayBackPaused( self ):
        currentFile = xbmc.Player().getPlayingFile()
        printDebug("PLAYBACK_PAUSED : " + currentFile)
        if(self.played_information.get(currentFile) != None):
            self.played_information[currentFile]["paused"] = "true"
        self.reportPlayback()
    
    def onPlayBackResumed( self ):
        currentFile = xbmc.Player().getPlayingFile()
        printDebug("PLAYBACK_RESUMED : " + currentFile)
        if(self.played_information.get(currentFile) != None):
            self.played_information[currentFile]["paused"] = "false"
        self.reportPlayback()
    
    def onPlayBackSeek( self, time, seekOffset ):
        printDebug("PLAYBACK_SEEK")
        self.reportPlayback()
        
    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        WINDOW = xbmcgui.Window( 10000 )
        self.stopAll()
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        if xbmc.Player().isPlaying():
            currentFile = xbmc.Player().getPlayingFile()
            printDebug("XBMB3C Service -> onPlayBackStarted" + currentFile)
            
            # grab all the info about this item from the stored windows props
            # only ever use the win props here, use the data map in all other places
            deleteurl = WINDOW.getProperty(currentFile + "deleteurl")
            runtime = WINDOW.getProperty(currentFile + "runtimeticks")
            item_id = WINDOW.getProperty(currentFile + "item_id")
            refresh_id = WINDOW.getProperty(currentFile + "refresh_id")
            audioindex = WINDOW.getProperty(currentFile + "AudioStreamIndex")
            subtitleindex = WINDOW.getProperty(currentFile + "SubtitleStreamIndex")
            playMethod = WINDOW.getProperty(currentFile + "playmethod")
            
            if(item_id == None or len(item_id) == 0):
                return
        
            url = ("http://%s:%s/mediabrowser/Sessions/Playing" % (addonSettings.getSetting('ipaddress'), addonSettings.getSetting('port')))  
            
            url = url + "?itemId=" + item_id

            url = url + "&canSeek=true"
            url = url + "&PlayMethod=" + playMethod
            url = url + "&QueueableMediaTypes=Video"
            url = url + "&MediaSourceId=" + item_id
            
            if(audioindex != None and audioindex!=""):
              url = url + "&AudioStreamIndex=" + audioindex
            
            if(subtitleindex != None and subtitleindex!=""):
              url = url + "&SubtitleStreamIndex=" + subtitleindex
            
            downloadUtils.downloadUrl(url, postBody="", type="POST")
            
            # save data map for updates and position calls
            data = {}
            data["deleteurl"] = deleteurl
            data["runtime"] = runtime
            data["item_id"] = item_id
            data["refresh_id"] = refresh_id
            data["currentfile"] = currentFile
            data["AudioStreamIndex"] = audioindex
            data["SubtitleStreamIndex"] = subtitleindex
            data["playmethod"] = playMethod
            self.played_information[currentFile] = data
            
            printDebug("XBMB3C Service -> ADDING_FILE : " + currentFile)
            printDebug("XBMB3C Service -> ADDING_FILE : " + str(self.played_information))

            # reset in progress possition
            self.reportPlayback()

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        printDebug("XBMB3C Service -> onPlayBackEnded")
        self.stopAll()

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        printDebug("XBMB3C Service -> onPlayBackStopped")
        self.stopAll()
