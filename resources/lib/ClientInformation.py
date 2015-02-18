from uuid import uuid4 as uuid4
import xbmc
import xbmcaddon
import xbmcgui

class ClientInformation():
    
    def __init__(self):
        
        # Internal variables
        self.addon =  xbmcaddon.Addon()
        self.window = xbmcgui.Window( 10000 )
        self.addonName = self.addon.getAddonInfo('name').upper()
        
        # Preparation for headers
        self.deviceName = self.addon.getSetting('deviceName')
        self.deviceId = self.window.getProperty('deviceId')
        self.username = self.addon.getSetting('username')
        self.version = self.addon.getAddonInfo('version')
    
    def getMachineId(self):
        
        # Shortcut variables
        addon = self.addon
        addonName = self.addonName
        window = self.window
        deviceId = self.deviceId
        
        # Verify if deviceId is already loaded from Settings
        if window.getProperty('deviceId') != "":

            deviceId = window.getProperty('deviceId')
            xbmc.log("%s ClientInformation -> DeviceId loaded from Window : %s" % (addonName, deviceId))

        else:

            deviceId = addon.getSetting('deviceId')
        
            # Verify if deviceId exists in settings
            if deviceId == "":
                
                xbmc.log("%s ClientInformation -> DeviceId not found in Settings" % addonName)
                
                # Generate deviceId
                guid = uuid4()
                deviceId = str("%012X" % guid).lower()
                xbmc.log("%s ClientInformation -> New deviceId : %s" % (addonName, deviceId))
                
                # Set deviceId to window and addon settings
                window.setProperty('deviceId', deviceId)
                addon.setSetting('deviceId', deviceId)
            
            else:
                
                # deviceId already exists, set to window
                window.setProperty('deviceId', deviceId)
                xbmc.log("%s ClientInformation -> DeviceId saved to Window from Settings : %s" % (addonName, deviceId))

        return deviceId
        
        
        # TO BE DELETED ONCE NEW METHOD IS FULLY TESTED - 02/16/2015 - ANGEL
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
        
    def getPlatform(self):

        if xbmc.getCondVisibility('system.platform.osx'):
            return "OSX"
        elif xbmc.getCondVisibility('system.platform.atv2'):
            return "ATV2"
        elif xbmc.getCondVisibility('system.platform.ios'):
            return "iOS"
        elif xbmc.getCondVisibility('system.platform.windows'):
            return "Windows"
        elif xbmc.getCondVisibility('system.platform.linux'):
            return "Linux/RPi"
        elif xbmc.getCondVisibility('system.platform.android'): 
            return "Linux/Android"

        return "Unknown"
    
    def getVersion(self):
        
        # Get the version of Mediabrowser add-on
        version = self.version
        
        return version
        
        # TO BE DELETED ONCE NEW METHOD IS FULLY TESTED - 02/16/2015 - ANGEL
        """version = xbmcaddon.Addon(id="plugin.video.xbmb3c").getAddonInfo("version")
        return version"""
    
    def getHeader(self):
        
        # Shortcut variables
        window = self.window
        deviceName = self.deviceName
        deviceId = self.getMachineId()
        version = self.getVersion()
        userName = self.username
        
        userId = ""
        token = ""

        # Verify if userId is currently used
        if window.getProperty('userid' + userName) != "":
            userId = 'UserId="%s",' % window.getProperty('userid' + userName)

        # Verify if token for userId has been returned
        if window.getProperty('AccessToken' + userName) != "":
            token = window.getProperty('AccessToken' + userName)
            
        # Authorization=Mediabrowser, Device Name, Device Id, Version. Optional: UserId, Token
        return {'Accept-Charset':'UTF-8,*', 'Accept-encoding':'gzip', 'Authorization':'Mediabrowser Client="Kodi", Device="' + deviceName + '", DeviceId="' + deviceId + '", ' + userId + ' Version="' + version + '"', 'X-Mediabrowser-Token': token}
