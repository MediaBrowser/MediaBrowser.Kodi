import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils

class SearchDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
    def onInit(self):
        self.action_exitkeys_id = [10, 13]

    def onFocus(self, controlId):
        pass
        
    def doAction(self, action):
        pass

    def closeDialog(self):
        self.close()
        
    def onClick(self, controlID):

        xbmc.log("doAction")
        if(controlID == 3020):
            self.addCharacter("A")
        
        elif(controlID == 3021):
        
            self.close()

        pass

    def addCharacter(self, char):
        searchTerm = self.getControl(3010).getLabel()
        searchTerm = searchTerm + char
        self.getControl(3010).setLabel(searchTerm)