
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
        result = json.loads(jsonData)
        
        id = result.get("Id")
        name = result.get("Name")
        image = downloadUtils.getArtwork(result, "Primary")
        fanArt = downloadUtils.getArtwork(result, "Backdrop")
        
        url =  server + ',;' + id
        url = urllib.quote(url)
        self.playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
        
        self.getControl(3000).setLabel(name)
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
        
