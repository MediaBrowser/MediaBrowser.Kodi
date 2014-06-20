#################################################################################################
# Skin Manager
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import urllib
import xml.etree.ElementTree as etree
import os

_MODE_MANAGESKINS=4

class SkinManagement():
    
    def ProcessAction(self, pluginName, pluginHandle, params):
    
        if(params.get("action") == None or params.get("action") == "show"):
            self.ShowAvailableSkins(pluginName, pluginHandle, params)
        elif(params.get("action") == "install"):
            self.InstallSkin(pluginName, pluginHandle, params)
        else:
            xbmcgui.Dialog().ok("Action Not Found", "The selected action was not found")
            
    def InstallSkin(self, pluginName, pluginHandle, params):
        
        # get the skin list
        skinListUrl = urllib.urlopen("https://raw.githubusercontent.com/MediaBrowser/MediaBrowser.XBMC/master/resources/skins.xml")
        skinListData = skinListUrl.read()
        skinListUrl.close()
        
        #xbmc.log(skinListData)
        
        root = etree.fromstring(skinListData)
        skinInfo = None
        for skin in root.iter('skin'):

            values = {}
            for tag in skin:
                values[tag.tag] = tag.text

            if(values.get("id") == params.get("skin_id")):
                skinInfo = values
                break
                
        if(skinInfo == None):
            xbmcgui.Dialog().ok("Not Found", "Skin with ID : " + params.get("skin_id") + " not found!")
            return
            
        confirm = xbmcgui.Dialog().yesno("Install Skin?", "Are you sure you want to install Skin : " + skinInfo.get("name"))    
        
        if(confirm == 0):
            return
        
        xbmc.log("Found Skin : " + str(skinInfo))
        
        local_path = self.Download(skinInfo.get("id"), skinInfo.get("version"), skinInfo.get("download"))
        
        addonPath = xbmc.translatePath("special://home/addons/")
        xbmc.log("addonPath : " + addonPath)
        
        fp, ok = self.Unzip(filename=local_path, destination=addonPath, report=True )
        
        xbmc.executebuiltin("UpdateLocalAddons")
        xbmc.sleep( 300 )
        #xbmc.executebuiltin("ReloadSkin()")
        #xbmc.sleep( 100 )
        
        confirm = xbmcgui.Dialog().yesno("Skin Installed", "To use this new skin you will need to activate it in the appearance setting, do you want to do that now?")
        if(confirm == 1):
            xbmc.executebuiltin("ActivateWindow(appearancesettings)")
            
        #xbmc.executebuiltin("ActivateWindow(home)")
      
    def UpdateDefaultSkin(self, id):
        xbmc.log("Setting skin as default : " + id)
        
        guisettings = os.path.join(xbmc.translatePath( "special://userdata" ), "guisettings.xml")
        xbmc.log("Settings file : " + guisettings)
        
        file = open(guisettings, 'r')
        fileData = file.read()
        file.close()
        
        startTag = fileData.find("<skin>")
        endTag = fileData.find("</skin>")
        xbmc.log("startTag : " + str(startTag) + " endTag : " + str(endTag))
        
        newSettings = None
        
        if(startTag > -1 and endTag > -1):
            newSettings = fileData[:startTag+6] + id + fileData[endTag:]
        else:
            startTag = fileData.find("<lookandfeel>")
            if(startTag > -1):
                newSettings = fileData[:startTag+13] + "<skin>" + id + "</skin>" + fileData[startTag+13:]
        
        if(newSettings != None):
            file = open(guisettings, 'w')
            file.write(newSettings)
            file.close()
    
    def ShowAvailableSkins(self, pluginName, pluginHandle, params):
       
        # get the skin list
        skinListUrl = urllib.urlopen("https://raw.githubusercontent.com/MediaBrowser/MediaBrowser.XBMC/master/resources/skins.xml")
        skinListData = skinListUrl.read()
        skinListUrl.close()
        
        #xbmc.log(skinListData)
        
        root = etree.fromstring(skinListData)
        
        for skin in root.iter('skin'):

            values = {}
            for tag in skin:
                values[tag.tag] = tag.text

            xbmc.log(str(values))
            
            installedVersion = None
            try:
                addonInfo = xbmcaddon.Addon(id=values.get("id"))
                installedVersion = addonInfo.getAddonInfo('version')
            except:
                pass            
            
            name = values.get("name")
            
            if(installedVersion != None):
                
                newer = self.version_cmp(installedVersion, values.get("version"))
                xbmc.log("Version Check : " + str(newer))
                
                if(newer == 0):
                    name = name + " (Installed : " + installedVersion + ")"
                else:
                    name = name + " (Update Available : " + values.get("version") + ")"
                
            else:
                name = name + " (Available : " + values.get("version") + ")"
            
            listItem = xbmcgui.ListItem(name, "test")
            xbmcplugin.addDirectoryItem(pluginHandle, "plugin://plugin.video.xbmb3c?mode=" + str(_MODE_MANAGESKINS) + "&action=install&skin_id=" + values.get("id"), listItem)
        
        xbmcplugin.endOfDirectory(pluginHandle, cacheToDisc=False)
        
    def version_cmp(self, version1, version2):
        parts1 = [int(x) for x in version1.split('.')]
        parts2 = [int(x) for x in version2.split('.')]

        # fill up the shorter version with zeros ...
        lendiff = len(parts1) - len(parts2)
        if lendiff > 0:
            parts2.extend([0] * lendiff)
        elif lendiff < 0:
            parts1.extend([0] * (-lendiff))

        for i, p in enumerate(parts1):
            ret = cmp(p, parts2[i])
            if ret: return ret
        return 0        
        
    def Download(self, id, version, repoURL):

        destination = os.path.join(xbmc.translatePath( "special://home/addons/packages/" ), id + "-" + version + ".zip")
        xbmc.log("Download to : " + destination)
        
        DIALOG_PROGRESS = xbmcgui.DialogProgress()
        DIALOG_PROGRESS.create("Downloading Skin")
        DIALOG_PROGRESS.update(0, "Starting")

        #try:
        def _report_hook( count, blocksize, totalsize ):
            percent = int( float( count * blocksize * 100 ) / totalsize )
            DIALOG_PROGRESS.update( percent, "Downloading")        
        
        fp, h = urllib.urlretrieve(repoURL, destination, _report_hook)
        #except:
        #    pass
        
        DIALOG_PROGRESS.close()
        
        return destination
     
    def Unzip(self, filename, destination=None, report=False ):
    
        from zipfile import ZipFile
        
        DIALOG_PROGRESS = None
        
        if(report):
            DIALOG_PROGRESS = xbmcgui.DialogProgress()
            DIALOG_PROGRESS.create("Extracting Skin")
            DIALOG_PROGRESS.update(0, "Starting")
        
        base_dir = ""
        if destination is None:
            destination = os.path.dirname( filename ) #=> extraction in current directory
            
        # extract the zip file
        
        zip = ZipFile( filename, "r" )
        namelist = zip.namelist()
        total_items = len( namelist ) or 1
        diff = 100.0 / total_items
        percent = 0

        root_dir = namelist[ 0 ]
        is_root_dir = True

        if not root_dir.endswith( "/" ) and ( zip.getinfo( root_dir ).file_size > 0 ):
            is_root_dir = False
        else:
            for i in namelist:
                #print root_dir in i, i
                if not root_dir in i:
                    is_root_dir = False
                    break
        base_dir = os.path.join( destination, root_dir.rstrip( "/" ) )
        if not is_root_dir:#root_dir.endswith( "/" ) and ( zip.getinfo( root_dir ).file_size > 0 ):
            root_dir = os.path.basename( os.path.splitext( filename )[ 0 ] )
            #destination = os.path.join( destination, root_dir )
            base_dir = destination
        #if os.path.isdir( base_dir ):
        # shutil2.rmtree( base_dir )
        #os.makedirs( base_dir )
        for count, item in enumerate( namelist ):
            percent += diff
            
            if(DIALOG_PROGRESS != None):
                if(DIALOG_PROGRESS.iscanceled()):
                    break
                DIALOG_PROGRESS.update( int( percent ), "UnZip: %i of %i items" % ( count + 1, total_items ), item, "Please wait..." )
  
            if not item.endswith( "/" ):
                root, name = os.path.split( item )
                directory = os.path.normpath( os.path.join( destination, root ) )
                if not os.path.isdir( directory ): os.makedirs( directory )
                file( os.path.join( directory, name ), "wb" ).write( zip.read( item ) )
        zip.close()
        del zip
        
        if(DIALOG_PROGRESS != None):
            DIALOG_PROGRESS.close()   
        
        return base_dir, True
