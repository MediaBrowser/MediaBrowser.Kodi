
import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils

_MODE_BASICPLAY=12

class ItemInfo(xbmcgui.WindowXMLDialog):

    id = ""
    playUrl = ""
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        xbmc.log("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        port = __settings__.getSetting('port')
        host = __settings__.getSetting('ipaddress')
        server = host + ":" + port         
        
        downloadUtils = DownloadUtils()
        
        userid = downloadUtils.getUserId()
       
        jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + self.id + "?format=json", suppress=False, popup=1 )     
        item = json.loads(jsonData)
        
        id = item.get("Id")
        name = item.get("Name")
        image = downloadUtils.getArtwork(item, "Primary")
        fanArt = downloadUtils.getArtwork(item, "Backdrop")
        
        episodeInfo = ""
        type = item.get("Type")
        if(type == "Episode" or type == "Season"):
            name = item.get("SeriesName") + ": " + name
            season = str(item.get("ParentIndexNumber")).zfill(2)
            episodeNum = str(item.get("IndexNumber")).zfill(2)
            episodeInfo = "S" + season + "xE" + episodeNum
            
        url =  server + ',;' + id
        url = urllib.quote(url)
        self.playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
        
        videoInfo = ""
        audioInfo = ""
        
        mediaStreams = item.get("MediaStreams")
        if(mediaStreams != None):
            for mediaStream in mediaStreams:
                if(mediaStream.get("Type") == "Video" and len(videoInfo) == 0):
                    videocodec = mediaStream.get("Codec")
                    height = str(mediaStream.get("Height"))
                    width = str(mediaStream.get("Width"))
                    aspectratio = mediaStream.get("AspectRatio")
                    videoInfo = width + "x" + height + " (" + aspectratio + ") " + videocodec
                if(mediaStream.get("Type") == "Audio" and len(audioInfo) == 0):
                    audiocodec = mediaStream.get("Codec")
                    channels = mediaStream.get("Channels")
                    audioInfo = audiocodec + " " + str(channels)
        
        self.getControl(3202).setLabel(videoInfo)
        self.getControl(3204).setLabel(audioInfo)
        
        self.getControl(3000).setLabel(name)
        self.getControl(3003).setLabel(episodeInfo)
        self.getControl(3001).setImage(fanArt)
        self.getControl(3009).setImage(image)
        
    def setId(self, id):
        self.id = id
        
    def onFocus(self, controlId):
        pass
        
    def doAction(self):
        pass

    def closeDialog(self):
        self.close()
        
    def onClick(self, controlID):

        if(controlID == 3002):
           
            xbmc.executebuiltin("RunPlugin(" + self.playUrl + ")")

            self.close()

        pass
        
