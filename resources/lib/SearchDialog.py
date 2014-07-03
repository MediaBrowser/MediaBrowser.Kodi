import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils
import threading

class SearchDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        newThread = BackgroundSearchThread()
        newThread.setDialog(self)
        newThread.start()
        

    def onFocus(self, controlId):
        pass
        
    def doAction(self, action):
        pass

    def closeDialog(self):
        thread.stopRunning()
        self.close()
        
    def onClick(self, controlID):

        if(controlID == 3020):
            self.addCharacter("A")
        elif(controlID == 3021):
            self.addCharacter("B")
        elif(controlID == 3022):
            self.addCharacter("C")
        elif(controlID == 3023):
            self.addCharacter("D")
        elif(controlID == 3024):
            self.addCharacter("E")
        elif(controlID == 3025):
            self.addCharacter("F")
        elif(controlID == 3026):
            self.addCharacter("G")
        elif(controlID == 3027):
            self.addCharacter("H")
        elif(controlID == 3028):
            self.addCharacter("I")
        elif(controlID == 3029):
            self.addCharacter("J")
        elif(controlID == 3030):
            self.addCharacter("K")
        elif(controlID == 3031):
            self.addCharacter("L")
        elif(controlID == 3032):
            self.addCharacter("M")
        elif(controlID == 3033):
            self.addCharacter("N")
        elif(controlID == 3034):
            self.addCharacter("O")
        elif(controlID == 3035):
            self.addCharacter("P")
        elif(controlID == 3036):
            self.addCharacter("Q")
        elif(controlID == 3037):
            self.addCharacter("R")
        elif(controlID == 3038):
            self.addCharacter("S")
        elif(controlID == 3039):
            self.addCharacter("T")
        elif(controlID == 3040):
            self.addCharacter("U")
        elif(controlID == 3041):
            self.addCharacter("V")
        elif(controlID == 3042):
            self.addCharacter("W")
        elif(controlID == 3043):
            self.addCharacter("X")
        elif(controlID == 3044):
            self.addCharacter("Y")
        elif(controlID == 3045):
            self.addCharacter("Z")
        elif(controlID == 3046):
            self.addCharacter("0")    
        elif(controlID == 3047):
            self.addCharacter("1")  
        elif(controlID == 3048):
            self.addCharacter("2")  
        elif(controlID == 3049):
            self.addCharacter("3")  
        elif(controlID == 3050):
            self.addCharacter("4")  
        elif(controlID == 3051):
            self.addCharacter("5")  
        elif(controlID == 3052):
            self.addCharacter("6")  
        elif(controlID == 3053):
            self.addCharacter("7")  
        elif(controlID == 3054):
            self.addCharacter("8")  
        elif(controlID == 3055):
            self.addCharacter("9")  
        elif(controlID == 3056):
            searchTerm = self.getControl(3010).getLabel()
            searchTerm = searchTerm[:-1]
            self.getControl(3010).setLabel(searchTerm)
        elif(controlID == 3057):
            self.addCharacter(" ") 
        elif(controlID == 3058):
            self.getControl(3010).setLabel("")
            

        pass

    def addCharacter(self, char):
        searchTerm = self.getControl(3010).getLabel()
        searchTerm = searchTerm + char
        self.getControl(3010).setLabel(searchTerm)
        
class BackgroundSearchThread(threading.Thread):
 
    active = True
    searchDialog = None

    def __init__(self, *args):
        xbmc.log("BackgroundSearchThread Init")
        threading.Thread.__init__(self, *args)

    def stopRunning(self):
        self.active = False
        
    def setDialog(self, searchDialog):
        self.searchDialog = searchDialog
        
    def run(self):
        xbmc.log("BackgroundSearchThread Started")     

        while(xbmc.abortRequested == False and self.active == True):
            xbmc.log("BackgroundSearchThread Doing Stuff")   
            
            movieResultsList = self.searchDialog.getControl(3110)
            
            poster = "http://localhost:15001/?id=9e03dfe16b3dcbbd6ae13428cd5a70f2&type=Primary&tag=9cb2b20a2eedd4d5eec4e94c9d15a520"
            listItem = xbmcgui.ListItem(label="Test 01", label2="Test 02", iconImage=poster, thumbnailImage=poster)
            movieResultsList.addItem(listItem)

            xbmc.sleep(2000)

        xbmc.log("BackgroundSearchThread Exited")
        
        