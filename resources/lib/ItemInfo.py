
import sys
import xbmcgui
import xbmc

class ItemInfo(xbmcgui.WindowXMLDialog):

    details = {}
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        xbmc.log("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        self.getControl(3000).setLabel(self.details["name"])
        self.getControl(3009).setImage(self.details["image"])
        
    def setInfo(self, data):
        self.details = data
        
    def onFocus(self, controlId):
        pass
        
    def doAction(self):
        pass

    def closeDialog(self):
        self.close()
        
    def onClick(self, controlID):

        if(controlID == 3002):
           
            xbmc.executebuiltin("RunPlugin(" + self.details["playUrl"] + ")")

            self.close()

        pass          