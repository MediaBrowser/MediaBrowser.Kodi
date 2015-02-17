from uuid import uuid4 as uuid4
import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()

class ClientInformation():

    def getMachineId(self):
    
        WINDOW = xbmcgui.Window( 10000 )
        deviceId = addon.getSetting('deviceId')
        
        # Verify if deviceId exists in settings
        if deviceId == "":
            
            xbmc.log("deviceId - > Not found in Settings")
            
            # Generate deviceId
            guid = uuid4()
            deviceId = str("%012X" % guid).lower()
            
            xbmc.log("deviceId - > New deviceId : %s" % deviceId)
            
            # Set deviceId to window and addon settings
            WINDOW.setProperty('deviceId', deviceId)
            addon.setSetting('deviceId', deviceId)
        
        else:
            
            xbmc.log("deviceId - > deviceId saved to WINDOW from Settings : %s" % deviceId)

            # deviceId already exists, set to window
            WINDOW.setProperty('deviceId', deviceId)

        return deviceId
        
        
        # TO BE DELETED ONCE NEW METHOD FULLY IS TESTED - 02/16/2015 - ANGEL
        """WINDOW = xbmcgui.Window( 10000 )
        
        clientId = WINDOW.getProperty("client_id")
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        if(clientId == None or clientId == ""):
            xbmc.log("CLIENT_ID - > No Client ID in WINDOW")
            clientId = self.addonSettings.getSetting('client_id')
        
            if(clientId == None or clientId == ""):
                xbmc.log("CLIENT_ID - > No Client ID in SETTINGS")
                uuid = uuid4()
                clientId = str("%012X" % uuid)
                WINDOW.setProperty("client_id", clientId)
                self.addonSettings.setSetting('client_id', clientId)
                xbmc.log("CLIENT_ID - > New Client ID : " + clientId)
            else:
                WINDOW.setProperty('client_id', clientId)
                xbmc.log("CLIENT_ID - > Client ID saved to WINDOW from Settings : " + clientId)
                
        return clientId"""
        
    def getVersion(self):
        version = xbmcaddon.Addon(id="plugin.video.xbmb3c").getAddonInfo("version")
        return version
