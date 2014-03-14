import sys
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
import json
import urllib
from BackgroundLoader import BackgroundRotationThread

_MODE_BG_EDIT=13

class BackgroundEdit():

    def showBackgrounds(self, pluginName, pluginHandle, params):
    
        xbmc.log("Shows Backgrounds")
        
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
            xbmc.log("Loaded BL : " + str(black_list))
        except:
            xbmc.log("No Blacklist found, starting with empty BL")
            black_list = []
        
        if(params.get("url") != None):
            newItem = params.get("url")
            newItem = urllib.unquote(newItem)
            
            if(newItem in black_list):
                black_list.remove(newItem)
            else:
                xbmc.log("Adding background to BG blacklist")
                black_list.append(newItem)
                
            stringdata = json.dumps(black_list)
            dataFile = open(lastDataPath, 'w')
            dataFile.write(stringdata)
            dataFile.close()   
            
            xbmc.executebuiltin("Container.Refresh")    
            return
        
        backgrounds = BackgroundRotationThread()
        backgrounds.updateArtLinks()
        allbackGrounds = backgrounds.global_art_links
        
        dirItems = []
        
        for bg in allbackGrounds:
            if(bg in black_list):
                list = xbmcgui.ListItem("DISABLED", iconImage=bg, thumbnailImage=bg)
            else:
                list = xbmcgui.ListItem("ENABLED", iconImage=bg, thumbnailImage=bg)
                
            url = pluginName + "?mode=" + str(_MODE_BG_EDIT) + "&url=" + urllib.quote(bg)
            dirItems.append((url, list, True))
        
        dirItems.sort()
        
        xbmcplugin.addDirectoryItems(pluginHandle, dirItems)
        xbmcplugin.endOfDirectory(pluginHandle,cacheToDisc=False)


