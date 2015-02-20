from uuid import uuid4 as uuid4
import xbmc
import xbmcaddon
import xbmcgui

class ClientInformation():
    
    def __init__(self):
        
        # Internal variables
        self.window = xbmcgui.Window( 10000 )
        self.addonId = self.getAddonId()
        self.addon =  xbmcaddon.Addon(id=self.addonId)
        self.addonName = self.addon.getAddonInfo('name').upper()
        
        # Preparation for headers
        self.deviceName = self.addon.getSetting('deviceName').replace("\\", "_")
        self.deviceId = self.window.getProperty('deviceId')
        self.username = self.addon.getSetting('username')
        self.version = self.addon.getAddonInfo('version')
    
    
    def getAddonId(self):
        
        # If addon Id is ever changed...
        addonId = 'plugin.video.xbmb3c'
        
        return addonId
        
        
    def getMachineId(self):
        
        # Shortcut variables
        className = self.__class__.__name__
        addon = self.addon
        addonName = self.addonName
        window = self.window
        deviceId = self.deviceId
        
        # Verify if deviceId is already loaded from Settings
        if deviceId == "":

            deviceId = addon.getSetting('deviceId')
        
            # Verify if deviceId exists in settings
            if deviceId == "":
                
                xbmc.log("%s %s -> DeviceId not found in Settings" % (addonName, className))
                
                # Generate deviceId
                guid = uuid4()
                deviceId = str("%012X" % guid).lower()
                xbmc.log("%s %s -> New deviceId : %s" % (addonName, className, deviceId))
                
                # Set deviceId to window and addon settings
                window.setProperty('deviceId', deviceId)
                addon.setSetting('deviceId', deviceId)
            
            else:
                
                # deviceId already exists, set to window
                window.setProperty('deviceId', deviceId)
                xbmc.log("%s %s -> DeviceId saved to Window from Settings : %s" % (addonName, className, deviceId))

        return deviceId
        
        
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

    
    def getHeader(self):
        
        # Shortcut variables
        window = self.window
        deviceName = self.deviceName
        deviceId = self.getMachineId()
        version = self.version
        username = self.username
        
        userId = ""
        token = ""

        # Verify if userId is currently used
        if window.getProperty('userid' + username) != "":
            userId = 'UserId="%s",' % window.getProperty('userid' + username)

        # Verify if token for userId has been returned
        if window.getProperty('AccessToken' + username) != "":
            token = window.getProperty('AccessToken' + username)
            
        # Authorization=Mediabrowser, Device Name, Device Id, Version. Optional: UserId, Token
        return {'Accept-Charset':'UTF-8,*', 'Accept-encoding':'gzip', 'Authorization':'Mediabrowser Client="Kodi", Device="' + deviceName + '", DeviceId="' + deviceId + '", ' + userId + ' Version="' + version + '"', 'X-Mediabrowser-Token': token}
