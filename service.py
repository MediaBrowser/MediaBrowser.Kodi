import xbmc, xbmcgui, xbmcaddon, urllib, httplib, os
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )

sDto='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}'
sEntities='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Entities}'
sArrays='{http://schemas.microsoft.com/2003/10/Serialization/Arrays}'

sys.path.append(BASE_RESOURCE_PATH)
import httplib2
from httplib2 import Http
playTime=0
def markWatched (url):
    conn = Http()
    print('Marking watched via URL: ' + url)
    resp, content = conn.request(
        uri=url,
        method='POST',
        headers={'Accept-encoding': 'gzip','Authorization' : 'MediaBrowser', 'Client' : 'Dashboard', 'Device' : "Chrome 31.0.1650.57", 'DeviceId' : "f50543a4c8e58e4b4fbb2a2bcee3b50535e1915e", 'Version':"3.0.5070.20258", 'UserId':"ff"},
        body='watched',
    )
    xbmc.executebuiltin("Container.Refresh")
    
class Service( xbmc.Player ):

    def __init__( self, *args ):
        print("starting monitor service")
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        print( "LED Status: Playback Started, LED ON" )

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        print( "LED Status: Playback Stopped, LED OFF" )

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        print( "LED Status: Playback Stopped, LED OFF" )
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            watchedurl=WINDOW.getProperty("watchedurl")
            markWatched(watchedurl)
            WINDOW.setProperty("watchedurl","")
            print("stopped at time:" + str(playTime))
montior=Service()        
while not xbmc.abortRequested:
    if xbmc.Player().isPlaying():
        try:
            playTime=xbmc.Player().getTime()
        except:
            pass
        xbmc.sleep(100)
    else:
        xbmc.sleep(1000)
    
print("Service shutting down")