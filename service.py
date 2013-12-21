import xbmc, xbmcgui, xbmcaddon, urllib, httplib, os, time
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
    #xbmc.executebuiltin("Container.Refresh")

def setPosition (url,method):
    conn = Http()
    WINDOW = xbmcgui.Window( 10000 )
    userid=WINDOW.getProperty("userid")    
    authString='MediaBrowser UserId=\"' + userid + '\",Client=\"XBMC\",Device=\"XBMB3C\",DeviceId=\"42\",Version=\"0.5.5\"'
    print('Setting position via: ' + url)
    resp, content = conn.request(
        uri=url,
        method=method,
        headers={'Accept-encoding': 'gzip','Authorization' : authString},
        body='position',
    )
   # xbmc.executebuiltin("Container.Refresh")
    
class Service( xbmc.Player ):

    def __init__( self, *args ):
        print("starting monitor service")
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            positionurl=WINDOW.getProperty("positionurl")
            setPosition(positionurl + '/Progress?PositionTicks=0','POST')

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        print( "LED Status: Playback Stopped, LED OFF" )

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            watchedurl=WINDOW.getProperty("watchedurl")
            positionurl=WINDOW.getProperty("positionurl")
            setPosition(positionurl +'?PositionTicks=' + str(int(playTime*10000000)),'DELETE')
            print "runtimeticks:" + WINDOW.getProperty("runtimeticks")
            percentComplete=(playTime*10000000)/int(WINDOW.getProperty("runtimeticks"))
            print "Percent complete:" + str(percentComplete)
            if ((playTime*10000000)/(int(WINDOW.getProperty("runtimeticks")))) > 0.95:
                markWatched(watchedurl)
            WINDOW.setProperty("watchedurl","")
            WINDOW.setProperty("positionurl","")
            WINDOW.setProperty("runtimeticks","")
            print("stopped at time:" + str(playTime))
            #xbmc.executebuiltin("Container.Refresh")
            #xbmc.sleep(100)


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