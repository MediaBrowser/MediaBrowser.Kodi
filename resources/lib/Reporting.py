import xbmc
import xbmcgui
import xbmcaddon
import json
import traceback
import urllib
import encodings
import hashlib
import threading
import os

from ClientInformation import ClientInformation
from DownloadUtils import DownloadUtils

class Reporting(threading.Thread):

    def __init__(self, *args):
        threading.Thread.__init__(self, *args)
    
    def run(self):
        try:
            self.ReportStats()
        except:
            tb = traceback.format_exc()
            xbmc.log("Error reporting stats to server")
            xbmc.log(tb)
    
    def SaveLastStats(self, stats):
        
        try:
            __addon__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
            __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile') )
            lastDataPath = __addondir__ + "LastSessionStats.json"
            dataFile = open(lastDataPath, 'w')
            stringdata = json.dumps(stats)
            #xbmc.log("Last Session Stats (Save): " + stringdata)
            dataFile.write(stringdata)
            dataFile.close()
        except:
            tb = traceback.format_exc()
            xbmc.log("Could not save last session stats")
            xbmc.log(tb)    
        
    def LoadLastStats(self):
    
        try:
            __addon__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
            __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile') )
            lastDataPath = __addondir__ + "LastSessionStats.json"
            dataFile = open(lastDataPath, 'r')
            jsonData = dataFile.read()
            dataFile.close()
            #xbmc.log("Last Session Stats (Load): " + jsonData)
            stats = json.loads(jsonData)        
            return stats
        except:
            tb = traceback.format_exc()
            xbmc.log("Could not load last session stats")
            xbmc.log(tb)
            return {}
        
    def ReportStats(self):
        
        __addon__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
            
        clientInfo = ClientInformation()
        
        xbmc.log("Reporting Stats")
        stats = self.LoadLastStats()
        
        machine_id = clientInfo.getMachineId()
        
        accountString = __addon__.getSetting('username').lower() + "-" + __addon__.getSetting('password')
        hash = hashlib.sha1(accountString)
        hashString = hash.hexdigest()        
        account_hash = hashString
        
        addon_ver = clientInfo.getVersion()
        kodi_ver = xbmc.getInfoLabel("System.BuildVersion")
        
        kodi_skin = xbmc.translatePath('special://skin')
        try:
            if(kodi_skin.endswith("\\") or kodi_skin.endswith("/")):
                kodi_skin = kodi_skin[0:-1]
                kodi_skin = os.path.basename(kodi_skin)
        except:
            pass
        
        messageData = ( "machine_id=" + urllib.quote_plus(machine_id) +
                        "&account_hash=" + urllib.quote_plus(account_hash) +
                        "&addon_ver=" + urllib.quote_plus(addon_ver) +
                        "&kodi_ver=" + urllib.quote_plus(kodi_ver) +
                        "&kodi_skin=" + urllib.quote_plus(kodi_skin))
                        
        messageData += "&" + self.AddStatToMessage("Movie", stats)
        messageData += "&" + self.AddStatToMessage("Episode", stats)
        messageData += "&" + self.AddStatToMessage("Audio", stats)
        messageData += "&" + self.AddStatToMessage("DirectStream", stats)
        messageData += "&" + self.AddStatToMessage("DirectPlay", stats)
        messageData += "&" + self.AddStatToMessage("Transcode", stats)
        
        downloadUtils = DownloadUtils()
        url = "http://magnesium.cloudapp.net/submit/"
        downloadUtils.downloadUrl(url, postBody=messageData, type="POST", authenticate=False, suppress=True)
        
 
    def AddStatToMessage(self, name, stats):
        
        if(stats.get(name) == None):
            return "last_session_" + name.lower() + "=" + "0"
        else:
            return "last_session_" + name.lower() + "=" + urllib.quote_plus(str(stats.get(name)))
        