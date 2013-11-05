'''
    @document   : default.py
    @package    : XBMB3C add-on
    @author     : xnappo
    @copyleft   : 2013, xnappo
    @version    : 0.1 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: XBMB3C XBMC add-on

    This file is part of the XBMC XBMB3C Plugin.

    XBMB3C Plugin is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    XBMB3C Plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with XBMB3C Plugin.  If not, see <http://www.gnu.org/licenses/>.
    
    Thanks to Hippojay for the PleXBMC plugin this is derived from

'''

import urllib
#import urllib2
import re
import xbmcplugin
import xbmcgui
import xbmcaddon
import httplib
import socket
import sys
import os
#import datetime
import time
import inspect
import base64
#import hashlib
import random
from urlparse import urlparse

__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)
XBMB3C_VERSION="3.1.5"

print "===== XBMB3C START ====="

print "XBMB3C -> running Python: " + str(sys.version_info)
print "XBMB3C -> running XBMB3C: " + str(XBMB3C_VERSION)

try:
  import lxml.etree.ElementTree as etree
  print("XBMB3C -> Running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("XBMB3C -> Running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("XBMB3C -> Running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("XBMB3C -> Running with built-in cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("XBMB3C -> Running with built-in ElementTree")
        except ImportError:
            try:
                import ElementTree as etree
                print("XBMB3C -> Running addon ElementTree version")
            except ImportError:
                print("XBMB3C -> Failed to import ElementTree from any known place")
#try:
#    import StorageServer
#except:
#    import storageserverdummy as StorageServer
#
#cache = StorageServer.StorageServer("plugins.video.XBMB3C", 1)
    
#Get the setting from the appropriate file.
DEFAULT_PORT="32400"
_MODE_GETCONTENT=0
_MODE_TVSHOWS=1
_MODE_MOVIES=2
_MODE_ARTISTS=3
_MODE_TVSEASONS=4
_MODE_PLAYLIBRARY=5
_MODE_TVEPISODES=6
_MODE_PROCESSXML=8
_MODE_CHANNELSEARCH=9
_MODE_CHANNELPREFS=10
_MODE_PLAYSHELF=11
_MODE_BASICPLAY=12
_MODE_SHARED_MOVIES=13
_MODE_ALBUMS=14
_MODE_TRACKS=15
_MODE_PHOTOS=16
_MODE_MUSIC=17
_MODE_VIDEOPLUGINPLAY=18
_MODE_CHANNELINSTALL=20
_MODE_CHANNELVIEW=21
_MODE_DISPLAYSERVERS=22
_MODE_PLAYLIBRARY_TRANSCODE=23
_MODE_SHARED_SHOWS=25
_MODE_SHARED_MUSIC=26
_MODE_SHARED_PHOTOS=27

_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_NEVER_SHOW="2"

#Check debug first...
g_debug = __settings__.getSetting('debug')
#g_debug = "true"
def printDebug( msg, functionname=True ):
    if g_debug == "true":
        if functionname is False:
            print str(msg)
        else:
            print "XBMB3C -> " + inspect.stack()[1][3] + ": " + str(msg)

def getPlatform( ):

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

XBMB3C_PLATFORM=getPlatform()
print "XBMB3C -> Platform: " + str(XBMB3C_PLATFORM)

#Next Check the WOL status - lets give the servers as much time as possible to come up
g_wolon = __settings__.getSetting('wolon')
if g_wolon == "true":
    from WOL import wake_on_lan
    printDebug("XBMB3C -> Wake On LAN: " + g_wolon, False)
    for i in range(1,12):
        wakeserver = __settings__.getSetting('wol'+str(i))
        if not wakeserver == "":
            try:
                printDebug ("XBMB3C -> Waking server " + str(i) + " with MAC: " + wakeserver, False)
                wake_on_lan(wakeserver)
            except ValueError:
                printDebug("XBMB3C -> Incorrect MAC address format for server " + str(i), False)
            except:
                printDebug("XBMB3C -> Unknown wake on lan error", False)

g_stream = __settings__.getSetting('streaming')
g_secondary = __settings__.getSetting('secondary')
g_streamControl = __settings__.getSetting('streamControl')
g_channelview = __settings__.getSetting('channelview')
g_flatten = __settings__.getSetting('flatten')
printDebug("XBMB3C -> Flatten is: "+ g_flatten, False)
g_forcedvd = __settings__.getSetting('forcedvd')

if g_debug == "true":
    print "XBMB3C -> Settings streaming: " + g_stream
    print "XBMB3C -> Setting filter menus: " + g_secondary
    print "XBMB3C -> Setting debug to " + g_debug
    if g_streamControl == _SUB_AUDIO_XBMC_CONTROL:
        print "XBMB3C -> Setting stream Control to : XBMC CONTROL (%s)" % g_streamControl
    elif g_streamControl == _SUB_AUDIO_NEVER_SHOW:
        print "XBMB3C -> Setting stream Control to : NEVER SHOW (%s)" % g_streamControl

    print "XBMB3C -> Force DVD playback: " + g_forcedvd
else:
    print "XBMB3C -> Debug is turned off.  Running silent"

#NAS Override
g_nasoverride = __settings__.getSetting('nasoverride')
printDebug("XBMB3C -> SMB IP Override: " + g_nasoverride, False)
if g_nasoverride == "true":
    g_nasoverrideip = __settings__.getSetting('nasoverrideip')
    if g_nasoverrideip == "":
        printDebug("XBMB3C -> No NAS IP Specified.  Ignoring setting")
    else:
        printDebug("XBMB3C -> NAS IP: " + g_nasoverrideip, False)

    g_nasroot = __settings__.getSetting('nasroot')

#Get look and feel
if __settings__.getSetting("contextreplace") == "true":
    g_contextReplace=True
else:
    g_contextReplace=False

g_skipcontext = __settings__.getSetting("skipcontextmenus")
g_skipmetadata= __settings__.getSetting("skipmetadata")
g_skipmediaflags= __settings__.getSetting("skipflags")
g_skipimages= __settings__.getSetting("skipimages")

g_loc = "special://home/addons/plugin.video.XBMB3C"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)',
              }

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None
        
def discoverAllServers( ):
    '''
        Take the users settings and add the required master servers
        to the server list.  These are the devices which will be queried
        for complete library listings.  There are 3 types:
            local server - from IP configuration
            bonjour server - from a bonjour lookup
        Alters the global g_serverDict value
        @input: None
        @return: None
    '''
    printDebug("== ENTER: discoverAllServers ==", False)
    
    das_servers={}
    das_server_index=0
    
    das_host = __settings__.getSetting('ipaddress')
    das_port =__settings__.getSetting('port')

    if not das_host or das_host == "<none>":
        das_host=None
    elif not das_port:
        printDebug( "XBMB3C -> No port defined.  Using default of " + DEFAULT_PORT, False)
        das_port=DEFAULT_PORT
       
    printDebug( "XBMB3C -> Settings hostname and port: %s : %s" % ( das_host, das_port), False)

    if das_host is not None:
        local_server = getLocalServers(das_host, das_port)
        if local_server:
            das_servers[das_server_index] = local_server
            das_server_index = das_server_index + 1
                                 
    if __settings__.getSetting('myplex_user') != "":
        printDebug( "XBMB3C -> Adding myplex as a server location", False)

    return das_servers
def getUserId( ip_address, port ):
    html = getURL(ip_address+":"+port+"/mediabrowser/Users?format=xml")
    #printDebug("userhtml:" + html)
    tree= etree.fromstring(html).getiterator('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}UserDto')
    for UserDto in tree:
        userid=str(UserDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text)
    printDebug("userid:" + userid)
    return userid
    
def getLocalServers( ip_address, port ):
    '''
        Connect to the defined local server (either direct or via bonjour discovery)
        and get a list of all known servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''
    printDebug("== ENTER: getLocalServers ==", False)
    url_path="/mediabrowser/Users/" + getUserId( ip_address, port) + "/items?format=xml"
    html = getURL(ip_address+":"+port+url_path)

    if html is False:
         return []
    server=etree.fromstring(html)

    return {'serverName': server.get('friendlyName','Unknown').encode('utf-8') ,
                        'server'    : ip_address,
                        'port'      : port ,
                        'discovery' : 'local' ,
                        'token'     : None ,
                        'uuid'      : server.get('machineIdentifier') ,
                        'owned'     : '1' ,
                        'master'    : 1 }


                                       
def getServerSections ( ip_address, port, name, uuid):
    printDebug("== ENTER: getServerSections ==", False)
    userid=str(getUserId( ip_address, port))
    html = getURL(ip_address+":"+port+"/mediabrowser/Users/"+userid+"/Items/Root?format=xml")
    printDebug("html:" + html)
    tree= etree.fromstring(html).getiterator('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}BaseItemDto')
    for BaseItemDto in tree:
        parentid=str(BaseItemDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text)
    htmlpath=("http://%s:%s/mediabrowser/Users/" % ( ip_address, port))
    html=getURL(htmlpath + userid + "/items?ParentId=" + parentid + "&format=xml")

    if html is False:
        return {}

    
    tree = etree.fromstring(html).getiterator("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}BaseItemDto")
    temp_list=[]
    for BaseItemDto in tree:
        if(str(BaseItemDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}RecursiveItemCount').text)!='0'):
            temp_list.append( {'title'      : (str(BaseItemDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Name').text)).encode('utf-8'),
                    'address'    : ip_address+":"+port ,
                    'serverName' : name ,
                    'uuid'       : uuid ,
                    'path'       : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + str(BaseItemDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text) + '&SortBy=Name&format=xml') ,
                    'token'      : str(BaseItemDto.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text)  ,
                    'location'   : "local" ,
                    'art'        : str(BaseItemDto.text) ,
                    'local'      : '1' ,
                    'type'       : "movie",
                    'owned'      : '1' })
            printDebug("Title " + str(BaseItemDto.tag))

    for item in temp_list:
        printDebug ("temp_list: " + str(item))
    return temp_list


def getAllSections( server_list = None ):
    '''
        from server_list, get a list of all the available sections
        and deduplicate the sections list
        @input: None
        @return: None (alters the global value g_sectionList)
    '''
    printDebug("== ENTER: getAllSections ==", False)
    
    if not server_list:
        server_list = discoverAllServers()
    
    printDebug("Using servers list: " + str(server_list))

    section_list=[]
    local_complete=False
    
    for server in server_list.itervalues():

        if server['discovery'] == "local" or server['discovery'] == "auto":
            section_details =  getServerSections( server['server'], server['port'] , server['serverName'], server['uuid']) 
            section_list += section_details
            printDebug ("Sectionlist:" + str(section_list))
            local_complete=True
            
    return section_list

def getURL( url, suppress=True, type="GET", popup=0 ):
    printDebug("== ENTER: getURL ==", False)
    try:
        if url[0:4] == "http":
            serversplit=2
            urlsplit=3
        else:
            serversplit=0
            urlsplit=1

        server=url.split('/')[serversplit]
        urlPath="/"+"/".join(url.split('/')[urlsplit:])

        printDebug("url = "+url)
        printDebug("server = "+str(server))
        printDebug("urlPath = "+str(urlPath))
        conn = httplib.HTTPConnection(server)
        conn.request(type, urlPath)
        data = conn.getresponse()
        if int(data.status) == 200:
            link=data.read()
            printDebug("====== XML 200 returned =======")
            printDebug(link, False)
            printDebug("====== XML 200 finished ======")

        elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
            try: conn.close()
            except: pass
            return data.getheader('Location')

        elif int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            print error
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                else:
                    xbmcgui.Dialog().ok("Error",server)
            print error
            try: conn.close()
            except: pass
            return False
        else:
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        print error
        if suppress is False:
            if popup==0:
                xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\": URL error: Unable to find server,)")
            else:
                xbmcgui.Dialog().ok("","Unable to contact host")
        print error
        return False
    except socket.error, msg :
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        print error
        if suppress is False:
            if popup == 0:
                xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\": URL error: Unable to connect to server,)")
            else:
                xbmcgui.Dialog().ok("","Unable to connect to host")
        print error
        return False
    else:
        try: conn.close()
        except: pass

        return link

def mediaType( partData, server, dvdplayback=False ):
    printDebug("== ENTER: mediaType ==", False)
    stream=partData['key']
    file=partData['file']

    global g_stream

    if ( file is None ) or ( g_stream == "1" ):
        printDebug( "Selecting stream")
        return "http://"+server+stream

    #First determine what sort of 'file' file is

    if file[0:2] == "\\\\":
        printDebug("Looks like a UNC")
        type="UNC"
    elif file[0:1] == "/" or file[0:1] == "\\":
        printDebug("looks like a unix file")
        type="nixfile"
    elif file[1:3] == ":\\" or file[1:2] == ":/":
        printDebug("looks like a windows file")
        type="winfile"
    else:
        printDebug("uknown file type")
        printDebug(str(file))
        type="notsure"

    # 0 is auto select.  basically check for local file first, then stream if not found
    if g_stream == "0":
        #check if the file can be found locally
        if type == "nixfile" or type == "winfile":
            try:
                printDebug("Checking for local file")
                exists = open(file, 'r')
                printDebug("Local file found, will use this")
                exists.close()
                return "file:"+file
            except: pass

        printDebug("No local file")
        if dvdplayback:
            printDebug("Forcing SMB for DVD playback")
            g_stream="2"
        else:
            return "http://"+server+stream


    # 2 is use SMB
    elif g_stream == "2" or g_stream == "3":
        if g_stream == "2":
            protocol="smb"
        else:
            protocol="afp"

        printDebug( "Selecting smb/unc")
        if type=="UNC":
            filelocation=protocol+":"+file.replace("\\","/")
        else:
            #Might be OSX type, in which case, remove Volumes and replace with server
            server=server.split(':')[0]
            loginstring=""

            if g_nasoverride == "true":
                if not g_nasoverrideip == "":
                    server=g_nasoverrideip
                    printDebug("Overriding server with: " + server)

                nasuser=__settings__.getSetting('nasuserid')
                if not nasuser == "":
                    loginstring=__settings__.getSetting('nasuserid')+":"+__settings__.getSetting('naspass')+"@"
                    printDebug("Adding AFP/SMB login info for user " + nasuser)


            if file.find('Volumes') > 0:
                filelocation=protocol+":/"+file.replace("Volumes",loginstring+server)
            else:
                if type == "winfile":
                    filelocation=protocol+"://"+loginstring+server+"/"+file[3:]
                else:
                    #else assume its a file local to server available over smb/samba (now we have linux PMS).  Add server name to file path.
                    filelocation=protocol+"://"+loginstring+server+file

        if g_nasoverride == "true" and g_nasroot != "":
            #Re-root the file path
            printDebug("Altering path " + filelocation + " so root is: " +  g_nasroot)
            if '/'+g_nasroot+'/' in filelocation:
                components = filelocation.split('/')
                index = components.index(g_nasroot)
                for i in range(3,index):
                    components.pop(3)
                filelocation='/'.join(components)
    else:
        printDebug( "No option detected, streaming is safest to choose" )
        filelocation="http://"+server+stream

    printDebug("Returning URL: " + filelocation)
    return filelocation

def addGUIItem( url, details, extraData, context=None, folder=True ):
        printDebug("== ENTER: addGUIItem ==", False)
        printDebug("Adding Dir for [%s]" % details.get('title','Unknown'))
        printDebug("Passed details: " + str(details))
        printDebug("Passed extraData: " + str(extraData))
        #printDebug("urladdgui:" + str(url))
        if details.get('title','') == '':
            return

        if extraData.get('mode',None) is None:
            mode="&mode=0"
        else:
            mode="&mode=%s" % extraData['mode']

        #Create the URL to pass to the item
        if ( not folder) and ( extraData['type'] == "image" ):
            u=sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            u=u.replace("\\\\","smb://")
            u=u.replace("\\","/")
        elif url.startswith('http') or url.startswith('file'):
            u=sys.argv[0]+"?url="+urllib.quote(url)+mode
        else:
            #u=sys.argv[0]+"?url="+str(url)+mode
            u=sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            u=u.replace("\\\\","smb://")
            u=u.replace("\\","/")
        
        #if extraData.get('parameters'):
            #for argument, value in extraData.get('parameters').items():
                #u="%s&%s=%s" % ( u, argument, urllib.quote(value) )
        #printDebug("URL to use for listing: " + urllib.quote(u))

        #Create the ListItem that will be displayed
        thumb=str(extraData.get('thumb',''))
        if thumb.startswith('http'):
            if '?' in thumb:
                thumbPath=thumb
            else:
                thumbPath=thumb.encode('utf-8') 
        else:
            thumbPath=thumb
        liz=xbmcgui.ListItem(details.get('title','Unknown'), iconImage=thumbPath, thumbnailImage=thumbPath)
        printDebug("Setting thumbnail as " + thumbPath)

        #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo( type=extraData.get('type','Video'), infoLabels=details )
#        if extraData.get('plot',None) is not None:
#            liz.setProperty('Plot', (str(extraData.get('plot','').encode('utf-8'))))
#            liz.setProperty('PlotOutline', (str(extraData.get('plot','').encode('utf-8'))))
#            printDebug('Found a plot:' + (str(extraData.get('plot','').encode('utf-8'))))
        #Music related tags
        if extraData.get('type','').lower() == "music":
            liz.setProperty('Artist_Genre', details.get('genre',''))
            liz.setProperty('Artist_Description', extraData.get('plot',''))
            liz.setProperty('Album_Description', extraData.get('plot',''))

        #For all end items    
        if ( not folder):
            liz.setProperty('IsPlayable', 'true')

            if extraData.get('type','video').lower() == "video":
                #liz.setProperty('TotalTime', str(extraData.get('duration')))
                liz.setProperty('ResumeTime', str(extraData.get('resume')))
            
                if g_skipmediaflags == "false":
                    printDebug("Setting VrR as : %s" % extraData.get('VideoResolution',''))
                    liz.setProperty('VideoResolution', extraData.get('VideoResolution',''))
                    liz.setProperty('VideoCodec', extraData.get('VideoCodec',''))
                    liz.setProperty('AudioCodec', extraData.get('AudioCodec',''))
                    liz.setProperty('AudioChannels', extraData.get('AudioChannels',''))
                    liz.setProperty('VideoAspect', extraData.get('VideoAspect',''))

                    video_codec={}
                    if extraData.get('xbmc_VideoCodec'): video_codec['codec'] = extraData.get('xbmc_VideoCodec')
                    if extraData.get('xbmc_VideoAspect') : video_codec['aspect'] = float(extraData.get('xbmc_VideoAspect'))
                    if extraData.get('xbmc_height') : video_codec['height'] = int(extraData.get('xbmc_height'))
                    if extraData.get('xbmc_width') : video_codec['width'] = int(extraData.get('xbmc_height'))
                    if extraData.get('duration') : video_codec['duration'] = int(extraData.get('duration'))

                    audio_codec={}
                    if extraData.get('xbmc_AudioCodec') : audio_codec['codec'] = extraData.get('xbmc_AudioCodec')
                    if extraData.get('xbmc_AudioChannels') : audio_codec['channels'] = int(extraData.get('xbmc_AudioChannels'))

                    liz.addStreamInfo('video', video_codec )
                    liz.addStreamInfo('audio', audio_codec )
                
        try:
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
            
            #Hack to show partial flag for TV shows and seasons
            if extraData.get('partialTV') == 1:            
                liz.setProperty('TotalTime', '100')
                liz.setProperty('ResumeTime', '50')
                
        except: pass

        #Set the fanart image if it has been enabled
        fanart=str(extraData.get('fanart_image',''))
        if '?' in fanart:
            liz.setProperty('fanart_image', fanart)
        else:
            liz.setProperty('fanart_image', fanart)

        printDebug( "Setting fan art as " + fanart )

        if extraData.get('banner'):
            liz.setProperty('banner', extraData.get('banner'))
            printDebug( "Setting banner as " + extraData.get('banner'))

        if context is not None:
            printDebug("Building Context Menus")
            liz.addContextMenuItems( context, g_contextReplace )

        return xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=folder)

def displaySections( filter=None, shared=False ):
        printDebug("== ENTER: displaySections() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')

        ds_servers=discoverAllServers()
        numOfServers=len(ds_servers)
        printDebug( "Using list of "+str(numOfServers)+" servers: " +  str(ds_servers))
        
        for section in getAllSections(ds_servers):
        
            if shared and section.get('owned') == '1':
                continue
                
        
            details={'title' : section.get('title', 'Unknown') }

            if len(ds_servers) > 1:
                details['title']=section.get('serverName')+": "+details['title']

            #extraData={ 'fanart_image' : getFanart(section, section.get('address')) ,
            #            'type'         : "Video" ,
            #            'thumb'        : getFanart(section, section.get('address'), False) ,
            #            'token'        : section.get('token',None) }
            #hack!
            extraData={ 'fanart_image' : '' ,
                        'type'         : "Video" ,
                        'thumb'        : '' ,
                        'token'        : section.get('token',None) }

            #Determine what we are going to do process after a link is selected by the user, based on the content we find

            path=section['path']

            if section.get('type') == 'show':
                mode=_MODE_TVSHOWS
                if (filter is not None) and (filter != "tvshows"):
                    continue

            elif section.get('type') == 'movie':
                mode=_MODE_MOVIES
                printDebug("MovieType!")
                if (filter is not None) and (filter != "movies"):
                    continue

            elif section.get('type') == 'artist':
                mode=_MODE_ARTISTS
                if (filter is not None) and (filter != "music"):
                    continue

            elif section.get('type') == 'photo':
                mode=_MODE_PHOTOS
                if (filter is not None) and (filter != "photos"):
                    continue
            else:
                printDebug("Ignoring section "+details['title']+" of type " + section.get('type') + " as unable to process")
                continue

            if g_secondary == "true":
                mode=_MODE_GETCONTENT
            else:
                path=path+'/all'

            extraData['mode']=mode
            s_url='http://%s%s' % ( section['address'], path)

            if g_skipcontext == "false":
                context=[]
                refreshURL="http://"+section.get('address')+section.get('path')+"/refresh"
                libraryRefresh = "XBMC.RunScript("+g_loc+"/default.py, update ," + refreshURL + ")"
                context.append(('Refresh library section', libraryRefresh , ))
            else:
                context=None

            #Build that listing..
            printDebug("addGUIItem:"+str(s_url)+str(details)+str(extraData)+str(context))
            addGUIItem(s_url, details,extraData, context)

        if shared:
            xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
            return
                    
        #For each of the servers we have identified
        allservers=ds_servers
        numOfServers=len(allservers)

        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def enforceSkinView(mode):
    '''
        Ensure that the views are consistance across plugin usage, depending
        upon view selected by user
        @input: User view selection
        @return: view id for skin
    '''
    printDebug("== ENTER: enforceSkinView ==", False)

    if __settings__.getSetting('skinoverride') == "false":
        return None

    skinname = __settings__.getSetting('skinname')

    current_skin_name = xbmc.getSkinDir()

    skin_map = { '2' : 'skin.confluence' ,
                 '0' : 'skin.quartz' ,
                 '1' : 'skin.quartz3' }
    
    if skin_map[skinname] not in current_skin_name:
        printDebug("Do not have the correct skin [%s] selected in settings [%s] - ignoring" % (current_skin_name, skin_map[skinname]))
        return None
    
    if mode == "movie":
        printDebug("Looking for movie skin settings")
        viewname = __settings__.getSetting('mo_view_%s' % skinname)

    elif mode == "tv":
        printDebug("Looking for tv skin settings")
        viewname = __settings__.getSetting('tv_view_%s' % skinname)

    elif mode == "music":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('mu_view_%s' % skinname)

    elif mode == "episode":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('ep_view_%s' % skinname)

    elif mode == "season":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('se_view_%s' % skinname)

    else:
        viewname = "None"

    printDebug("view name is %s" % viewname)

    if viewname == "None":
        return None

    QuartzV3_views={ 'List' : 50,
                     'Big List' : 51,
                     'MediaInfo' : 52,
                     'MediaInfo 2' : 54,
                     'Big Icons' : 501,
                     'Icons': 53,
                     'Panel' : 502,
                     'Wide' : 55,
                     'Fanart 1' : 57,
                     'Fanart 2' : 59,
                     'Fanart 3' : 500 }

    Quartz_views={ 'List' : 50,
                   'MediaInfo' : 51,
                   'MediaInfo 2' : 52,
                   'Icons': 53,
                   'Wide' : 54,
                   'Big Icons' : 55,
                   'Icons 2' : 56 ,
                   'Panel' : 57,
                   'Fanart' : 58,
                   'Fanart 2' : 59 }

    Confluence_views={ 'List' : 50,
                       'Big List' : 51,
                       'Thumbnail' : 500,
                       'Poster Wrap': 501,
                       'Fanart' : 508,
                       'Media Info' : 504,
                       'Media Info 2' : 503,
                       'Wide Icons' : 505 }

    skin_list={"0" : Quartz_views ,
               "1" : QuartzV3_views,
               "2" : Confluence_views}

    printDebug("Using skin view: %s" % skin_list[skinname][viewname])

    try:
        return skin_list[skinname][viewname]
    except:
        print "XBMB3C -> skin name or view name error"
        return None

def Movies( url, tree=None ):
    printDebug("== ENTER: Movies() ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')

    #get the server name from the URL, which was passed via the on screen listing..
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)

    setWindowHeading(tree)
    randomNumber=str(random.randint(1000000000,9999999999))
    #Find all the video tags, as they contain the data we need to link to a file.
    MovieTags=tree.findall('Video')
    fullList=[]
    for movie in MovieTags:

        movieTag(url, server, tree, movie, randomNumber)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('movie')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle)

def buildContextMenu( url, itemData ):
    context=[]
    server=getServerFromURL(url)
    refreshURL=url.replace("/all", "/refresh")
    plugin_url="XBMC.RunScript("+g_loc+"/default.py, "
    ID=itemData.get('ratingKey','0')

    #Initiate Library refresh
    libraryRefresh = plugin_url+"update, " + refreshURL.split('?')[0]+getAuthDetails(itemData,prefix="?") + ")"
    context.append(('Rescan library section', libraryRefresh , ))

    #Mark media unwatched
    unwatchURL="http://"+server+"/:/unscrobble?key="+ID+"&identifier=com.fixme.plugins.library"+getAuthDetails(itemData)
    unwatched=plugin_url+"watch, " + unwatchURL + ")"
    context.append(('Mark as Unwatched', unwatched , ))

    #Mark media watched
    watchURL="http://"+server+"/:/scrobble?key="+ID+"&identifier=com.fixme.plugins.library"+getAuthDetails(itemData)
    watched=plugin_url+"watch, " + watchURL + ")"
    context.append(('Mark as Watched', watched , ))

    #Delete media from Library
    deleteURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    removed=plugin_url+"delete, " + deleteURL + ")"
    context.append(('Delete media', removed , ))

    #Display plugin setting menu
    settingDisplay=plugin_url+"setting)"
    context.append(('XBMB3C settings', settingDisplay , ))

    #Reload media section
    listingRefresh=plugin_url+"refresh)"
    context.append(('Reload Section', listingRefresh , ))

    #alter audio
    alterAudioURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    alterAudio=plugin_url+"audio, " + alterAudioURL + ")"
    context.append(('Select Audio', alterAudio , ))

    #alter subs
    alterSubsURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    alterSubs=plugin_url+"subs, " + alterSubsURL + ")"
    context.append(('Select Subtitle', alterSubs , ))

    printDebug("Using context menus " + str(context))

    return context

def TVShows( url, tree=None ):
    printDebug("== ENTER: TVShows() ==", False)
    xbmcplugin.setContent(pluginhandle, 'tvshows')

    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)

    setWindowHeading(tree)
    #For each directory tag we find
    ShowTags=tree.findall('Directory')
    for show in ShowTags:

        tempgenre=[]

        for child in show:
            tempgenre.append(child.get('tag',''))

        watched=int(show.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : show.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : show.get('titleSort', show.get('title','Unknown')).encode('utf-8') ,
                 'tvshowname' : show.get('title','Unknown').encode('utf-8') ,
                 'studio'     : show.get('studio','').encode('utf-8') ,
                 'plot'       : show.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(show.get('leafCount',0)) ,
                 'mpaa'       : show.get('contentRating','') ,
                 'aired'      : show.get('originallyAvailableAt','') ,
                 'genre'      : " / ".join(tempgenre) }

        extraData={'type'              : 'video' ,
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(show, server) ,
                   'fanart_image'      : getFanart(show, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : show.get('key','') ,
                   'ratingKey'         : str(show.get('ratingKey',0)) }

        #banner art
        if show.get('banner',None) is not None:
            extraData['banner']='http://'+server+show.get('banner')

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        #Create URL based on whether we are going to flatten the season view
        if g_flatten == "2":
            printDebug("Flattening all shows")
            extraData['mode']=_MODE_TVEPISODES
            u='http://%s%s'  % ( server, extraData['key'].replace("children","allLeaves"))
        else:
            extraData['mode']=_MODE_TVSEASONS
            u='http://%s%s'  % ( server, extraData['key'])

        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)
        else:
            context=None

        addGUIItem(u,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('tv')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def TVSeasons( url ):
    printDebug("== ENTER: season() ==", False)
    xbmcplugin.setContent(pluginhandle, 'seasons')

    #Get URL, XML and parse
    server=getServerFromURL(url)
    tree=getXML(url)
    if tree is None:
        return

    willFlatten=False
    if g_flatten == "1":
        #check for a single season
        if int(tree.get('size',0)) == 1:
            printDebug("Flattening single season show")
            willFlatten=True

    sectionart=getFanart(tree, server)
    banner=tree.get('banner')
    setWindowHeading(tree)
    #For all the directory tags
    SeasonTags=tree.findall('Directory')
    for season in SeasonTags:

        if willFlatten:
            url='http://'+server+season.get('key')
            TVEpisodes(url)
            return

        watched=int(season.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : season.get('title','Unknown').encode('utf-8') ,
                 'tvshowname' : season.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : season.get('titleSort', season.get('title','Unknown')).encode('utf-8') ,
                 'studio'     : season.get('studio','').encode('utf-8') ,
                 'plot'       : season.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(season.get('leafCount',0)) ,
                 'mpaa'       : season.get('contentRating','') ,
                 'aired'      : season.get('originallyAvailableAt','') }

        if season.get('sorttitle'): details['sorttitle'] = season.get('sorttitle')

        extraData={'type'              : 'video' ,
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(season, server) ,
                   'fanart_image'      : getFanart(season, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : season.get('key','') ,
                   'ratingKey'         : str(season.get('ratingKey',0)) ,
                   'mode'              : _MODE_TVEPISODES }

        if banner:
            extraData['banner']="http://"+server+banner
                   
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        url='http://%s%s' % ( server , extraData['key'] )

        if g_skipcontext == "false":
            context=buildContextMenu(url, season)
        else:
            context=None

        #Build the screen directory listing
        addGUIItem(url,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('season')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def TVEpisodes( url, tree=None ):
    printDebug("== ENTER: TVEpisodes() ==", False)
    xbmcplugin.setContent(pluginhandle, 'episodes')

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    banner = tree.get('banner')
    ShowTags=tree.findall('Video')
    server=getServerFromURL(url)

    if g_skipimages == "false":
        sectionart=getFanart(tree, server)

    randomNumber=str(random.randint(1000000000,9999999999))

    for episode in ShowTags:

        printDebug("---New Item---")
        tempgenre=[]
        tempcast=[]
        tempdir=[]
        tempwriter=[]

        for child in episode:
            if child.tag == "Media":
                mediaarguments = dict(child.items())
            elif child.tag == "Genre" and g_skipmetadata == "false":
                tempgenre.append(child.get('tag'))
            elif child.tag == "Writer"  and g_skipmetadata == "false":
                tempwriter.append(child.get('tag'))
            elif child.tag == "Director"  and g_skipmetadata == "false":
                tempdir.append(child.get('tag'))
            elif child.tag == "Role"  and g_skipmetadata == "false":
                tempcast.append(child.get('tag'))

        printDebug("Media attributes are " + str(mediaarguments))

        #Gather some data
        view_offset=episode.get('viewOffset',0)
        duration=int(mediaarguments.get('duration',episode.get('duration',0)))/1000

        #Required listItem entries for XBMC
        details={'plot'        : episode.get('summary','').encode('utf-8') ,
                 'title'       : episode.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'   : episode.get('titleSort', episode.get('title','Unknown')).encode('utf-8')  ,
                 'rating'      : float(episode.get('rating',0)) ,
                 'studio'      : episode.get('studio',tree.get('studio','')).encode('utf-8') ,
                 'mpaa'        : episode.get('contentRating', tree.get('grandparentContentRating','')) ,
                 'year'        : int(episode.get('year',0)) ,
                 'tagline'     : episode.get('tagline','').encode('utf-8') ,
                 'episode'     : int(episode.get('index',0)) ,
                 'aired'       : episode.get('originallyAvailableAt','') ,
                 'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') ,
                 'season'      : int(episode.get('parentIndex',tree.get('parentIndex',0))) }

        if episode.get('sorttitle'): details['sorttitle'] = episode.get('sorttitle').encode('utf-8')

        if tree.get('mixedParents','0') == '1':
            details['title'] = "%s - %sx%s %s" % ( details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'] )
        else:
            details['title'] = str(details['episode']).zfill(2) + ". " + details['title']


        #Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'thumb'        : getThumb(episode, server) ,
                   'fanart_image' : getFanart(episode, server) ,
                   'token'        : _PARAM_TOKEN ,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)),
                   'duration'     : duration,
                   'resume'       : int(int(view_offset)/1000) }

        if extraData['fanart_image'] == "" and g_skipimages == "false":
            extraData['fanart_image']=sectionart

        if banner:
            extraData['banner'] = "http://"+server+banner
            
        #Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount',0)) > 0:
            details['playcount'] = 1
        else: 
            details['playcount'] = 0

        #Extended Metadata
        if g_skipmetadata == "false":
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)

        #Add extra media flag data
        if g_skipmediaflags == "false":
            extraData.update(getMediaData(mediaarguments))

        #Build any specific context menu entries
        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)
        else:
            context=None

        extraData['mode']=_MODE_PLAYLIBRARY
        # http:// <server> <path> &mode=<mode> &t=<rnd>
        u="http://%s%s?t=%s" % (server, extraData['key'], randomNumber)

        addGUIItem(u,details,extraData, context, folder=False)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('episode')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def playLibraryMedia( vids, override=False, force=None, full_data=False ):
    printDebug("== ENTER: playLibraryMedia ==", False)

    getTranscodeSettings(override)

    server=getServerFromURL(vids)

    id=vids.split('?')[0].split('&')[0].split('/')[-1]

    if force:
        full_data = True
        
    streams=getAudioSubtitlesMedia(server,id, full_data)
    url=selectMedia(streams, server)

    if url is None:
        return

    protocol=url.split(':',1)[0]

    if protocol == "file":
        printDebug( "We are playing a local file")
        playurl=url.split(':',1)[1]
    elif protocol == "http":
        printDebug( "We are playing a stream")
        if g_transcode == "true":
            printDebug( "We will be transcoding the stream")
            playurl=transcode(id,url)+getAuthDetails({'token':_PARAM_TOKEN})

        else:
            playurl=url+getAuthDetails({'token':_PARAM_TOKEN},prefix="?")
    else:
        playurl=url

    resume=int(int(streams['media']['viewOffset'])/1000)
    duration=int(int(streams['media']['duration'])/1000)

    printDebug("Resume has been set to " + str(resume))

    item = xbmcgui.ListItem(path=playurl)

    if streams['full_data']:
        item.setInfo( type='Video', infoLabels=streams['full_data'] )
        item.setThumbnailImage(streams['full_data'].get('thumbnailImage',''))
        item.setIconImage(streams['full_data'].get('thumbnailImage',''))
    
    if force:
        
        if int(force) > 0:
            resume=int(int(force)/1000)
        else:
            resume=force
        
        if resume:
            printDebug ("Playback from resume point")
            item.setProperty('ResumeTime', str(resume) )
            item.setProperty('TotalTime', str(duration) )

    if override:
        start=xbmc.Player().play(listitem=item)
    else:
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    #Set a loop to wait for positive confirmation of playback
    count = 0
    while not xbmc.Player().isPlaying():
        printDebug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 20:
            return
        else:
            time.sleep(2)

    if not (g_transcode == "true" ):
        setAudioSubtitles(streams)

    monitorPlayback(id,server)

    return
def remove_html_tags( data ):
    p = re.compile(r'<.*?>')
    return p.sub('', data)
    
def monitorPlayback( id, server ):
    printDebug("== ENTER: monitorPlayback ==", False)

    if len(server.split(':')) == 1:
        server=server

    monitorCount=0
    progress = 0
    complete = 0
    #Whilst the file is playing back
    while xbmc.Player().isPlaying():
        #Get the current playback time

        currentTime = int(xbmc.Player().getTime())
        totalTime = int(xbmc.Player().getTotalTime())
        try:
            progress = int(( float(currentTime) / float(totalTime) ) * 100)
        except:
            progress = 0

        if currentTime < 30:
            printDebug("Less that 30 seconds, will not set resume")

        #If we are less than 95% completem, store resume time
        elif progress < 95:
            printDebug( "Movies played time: %s secs of %s @ %s%%" % ( currentTime, totalTime, progress) )
            getURL("http://"+server+"/:/progress?key="+id+"&identifier=com.fixme.plugins.library&time="+str(currentTime*1000),suppress=True)
            complete=0

        #Otherwise, mark as watched
        else:
            if complete == 0:
                printDebug( "Movie marked as watched. Over 95% complete")
                getURL("http://"+server+"/:/scrobble?key="+id+"&identifier=com.fixme.plugins.library",suppress=True)
                complete=1

        time.sleep(5)

    #If we get this far, playback has stopped
    printDebug("Playback Stopped")

    if g_sessionID is not None:
        printDebug("Stopping PMS transcode job with session " + g_sessionID)
        stopURL='http://'+server+'/video/:/transcode/segmented/stop?session='+g_sessionID
        html=getURL(stopURL)

    return

def PLAY( url ):
        printDebug("== ENTER: PLAY ==", False)

        if url[0:4] == "file":
            printDebug( "We are playing a local file")
            #Split out the path from the URL
            playurl=url.split(':',1)[1]
        elif url[0:4] == "http":
            printDebug( "We are playing a stream")
            if '?' in url:
                playurl=url+getAuthDetails({'token':_PARAM_TOKEN})
            else:
                playurl=url
        else:
            playurl=url
        #playurl=("smb://jupiter/e/Video/Movies/Man of Steel (2013)/man.of.steel.2013.720p.bluray.x264-felony.mkv")
        #playurl=("\\\\jupiter\e\Video\Movies\Man of Steel (2013)\man.of.steel.2013.720p.bluray.x264-felony.mkv")
        item = xbmcgui.ListItem(path=playurl)
        xbmc.Player().play(urllib.unquote(playurl))
        #Set a loop to wait for positive confirmation of playback
        count = 0
        while not xbmc.Player().isPlaying():
            printDebug( "Not playing yet...sleep for 2")
            count = count + 2
            if count >= 20:
                return
            else:
                time.sleep(2)
        while xbmc.Player().isPlaying():
                dont_worry=1
                #currentTime = int(xbmc.Player().getTime())
        #return xbmcplugin.setResolvedUrl(pluginhandle, True, item)
        return


def get_params( paramstring ):
    printDebug("== ENTER: get_params ==", False)
    printDebug("Parameter string: " + paramstring)
    param={}
    if len(paramstring)>=2:
            params=paramstring

            if params[0] == "?":
                cleanedparams=params[1:]
            else:
                cleanedparams=params

            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]

            pairsofparams=cleanedparams.split('&')
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                    elif (len(splitparams))==3:
                            param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
    print "XBMB3C -> Detected parameters: " + str(param)
    return param



def getContent( url ):
    '''
        This function takes the URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    '''
    printDebug("== ENTER: getContent ==", False)

    server=getServerFromURL(url)
    lastbit=url.split('/')[-1]
    printDebug("URL suffix: " + str(lastbit))
    printDebug("server: " + str(server))
    printDebug("URL: " + str(url))    
    #Catch search requests, as we need to process input before getting results.
    if lastbit.startswith('search'):
        printDebug("This is a search URL.  Bringing up keyboard")
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term')
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            printDebug("Search term input: "+ text)
            url=url+'&query='+urllib.quote(text)
        else:
            return

    html=getURL(url, suppress=False, popup=1 )

    if html is False:
        return
    tree = etree.fromstring(html).getiterator("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}BaseItemDto")
    #tree=etree.fromstring(html).getiterator()

    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    #WINDOW.setProperty("heading", tree.get('title2',tree.get('title1','')))


    if lastbit == "folder":
        processXML(url,tree)
        return

    #view_group=tree.get('viewGroup',None)
    view_group=""

    if view_group == "movie":
        printDebug( "This is movie XML, passing to Movies")
        if not (lastbit.startswith('recently') or lastbit.startswith('newest')):
            xbmcplugin.addSortMethod(pluginhandle,xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        Movies(url, tree)
    elif view_group == "show":
        printDebug( "This is tv show XML")
        TVShows(url,tree)
    elif view_group == "episode":
        printDebug("This is TV episode XML")
        TVEpisodes(url,tree)
    elif view_group == 'artist':
        printDebug( "This is music XML")
        artist(url, tree)
    elif view_group== 'album' or view_group == 'albums':
        albums(url,tree)
    elif view_group == "track":
        printDebug("This is track XML")
        tracks(url, tree)
    elif view_group =="photo":
        printDebug("This is a photo XML")
        photo(url,tree)
    else:
        processDirectory(url,tree)

    return

def processDirectory( url, tree=None ):
    printDebug("== ENTER: processDirectory ==", False)
    parsed = urlparse(url)
    parsedserver,parsedport=parsed.netloc.split(':')
    userid=getUserId(parsedserver,parsedport)
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, 'movies')

    server=getServerFromURL(url)
    setWindowHeading(tree)
    for directory in tree:
        tempTitle=((directory.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Name').text)).encode('utf-8')
        id=str(directory.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text).encode('utf-8')
        isFolder=str(directory.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}IsFolder').text).encode('utf-8')
        #printDebug('server: http://'+server+'/mediabrowser/Items/'+str(id) +'&format=xml')
        html=getURL(('http://'+server+'/mediabrowser/Users/' + userid + '/Items/'+str(id) +'?format=xml') , suppress=False, popup=1 )
        episode=(etree.fromstring(html).find("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}IndexNumber").text)
        if episode is None:
            episode='0'
        season=(etree.fromstring(html).find("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}ParentIndexNumber").text)
        if season is None:
            season='0'
        printDebug("Season/Ep" + season + '/' + episode)
        #if episode == None:
        #    episode=""
        details={'title' : tempTitle,
                 'plot'  : etree.fromstring(html).find("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Overview").text,
                 'episode'     : int(episode) ,
                 #'aired'       : episode.get('originallyAvailableAt','') ,
                 #'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') ,
                 'season'      : int(season) }
        extraData={'thumb'        : getThumb(directory, server) ,
                   'fanart_image' : getFanart(directory, server) }

        if extraData['thumb'] == '':
            extraData['thumb']=extraData['fanart_image']

        extraData['mode']=_MODE_GETCONTENT

        #printDebug('Details html:' + html)
        if isFolder=='true':
            u= 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&SortBy=SortName&format=xml'
            if (str(directory.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}RecursiveItemCount').text).encode('utf-8')!='0'):
                addGUIItem(u,details,extraData)
        else:
            u= etree.fromstring(html).find("{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Path").text
            if u == None:
                printDebug('NotReallyThere')
                u=""
            else:
                addGUIItem(u,details,extraData)
        
        #u=('http://'+server+'/mediabrowser/Items/'+str(id)+'/File')
        #details=""
        #extraData=""
        #addGUIItem(u,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)


def artist( url, tree=None ):
    '''
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    '''
    printDebug("== ENTER: artist ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')

    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    setWindowHeading(tree)
    ArtistTag=tree.findall('Directory')
    for artist in ArtistTag:

        details={'artist'  : artist.get('title','').encode('utf-8') }

        details['title']=details['artist']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(artist, server) ,
                   'fanart_image' : getFanart(artist, server) ,
                   'ratingKey'    : artist.get('title','') ,
                   'key'          : artist.get('key','') ,
                   'mode'         : _MODE_ALBUMS ,
                   'plot'         : artist.get('summary','') }

        url='http://%s%s' % (server, extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def albums( url, tree=None ):
    printDebug("== ENTER: albums ==", False)
    xbmcplugin.setContent(pluginhandle, 'albums')

    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    sectionart=getFanart(tree, server)
    setWindowHeading(tree)
    AlbumTags=tree.findall('Directory')
    for album in AlbumTags:

        details={'album'   : album.get('title','').encode('utf-8') ,
                 'year'    : int(album.get('year',0)) ,
                 'artist'  : tree.get('parentTitle', album.get('parentTitle','')).encode('utf-8') }

        details['title']=details['album']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(album, server) ,
                   'fanart_image' : getFanart(album, server) ,
                   'key'          : album.get('key',''),
                   'mode'         : _MODE_TRACKS ,
                   'plot'         : album.get('summary','')}

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        url='http://%s%s' % (server, extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def tracks( url,tree=None ):
    printDebug("== ENTER: tracks ==", False)
    xbmcplugin.setContent(pluginhandle, 'songs')

    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    sectionart=getFanart(tree,server)
    setWindowHeading(tree)
    TrackTags=tree.findall('Track')
    for track in TrackTags:

        trackTag(server, tree, track)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getXML (url, tree=None):
    printDebug("== ENTER: getXML ==", False)

    if tree is None:

        html=getURL(url)

        if html is False:
            return None

        tree=etree.fromstring(html)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header','Message'),tree.get('message',''))
        return None

    setWindowHeading(tree)

    return tree



def processXML( url, tree=None ):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER: processXML ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')
    server=getServerFromURL(url)
    tree=getXML(url,tree)
    if tree is None:
        return
    setWindowHeading(tree)
    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, plugin, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":
            extraData['mode']=_MODE_PROCESSXML
            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Track":
            trackTag(server, tree, plugin)

        elif tree.get('viewGroup') == "movie":
            Movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            TVEpisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def movieTag(url, server, tree, movie, randomNumber):

    printDebug("---New Item---")
    tempgenre=[]
    tempcast=[]
    tempdir=[]
    tempwriter=[]

    #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    #We'll process it later
    for child in movie:
        if child.tag == "Media":
            mediaarguments = dict(child.items())
        elif child.tag == "Genre" and g_skipmetadata == "false":
            tempgenre.append(child.get('tag'))
        elif child.tag == "Writer"  and g_skipmetadata == "false":
            tempwriter.append(child.get('tag'))
        elif child.tag == "Director"  and g_skipmetadata == "false":
            tempdir.append(child.get('tag'))
        elif child.tag == "Role"  and g_skipmetadata == "false":
            tempcast.append(child.get('tag'))

    printDebug("Media attributes are " + str(mediaarguments))

    #Gather some data
    view_offset=movie.get('viewOffset',0)
    duration=int(mediaarguments.get('duration',movie.get('duration',0)))/1000

    #Required listItem entries for XBMC
    details={'plot'      : movie.get('summary','').encode('utf-8') ,
             'title'     : movie.get('title','Unknown').encode('utf-8') ,
             'sorttitle'  : movie.get('titleSort', movie.get('title','Unknown')).encode('utf-8') ,
             'rating'    : float(movie.get('rating',0)) ,
             'studio'    : movie.get('studio','').encode('utf-8') ,
             'mpaa'      : "Rated " + movie.get('contentRating', 'unknown') ,
             'year'      : int(movie.get('year',0)) ,
             'tagline'   : movie.get('tagline','') } 

    #Extra data required to manage other properties
    extraData={'type'         : "Video" ,
               'thumb'        : getThumb(movie, server) ,
               'fanart_image' : getFanart(movie, server) ,
               'token'        : _PARAM_TOKEN ,
               'key'          : movie.get('key',''),
               'ratingKey'    : str(movie.get('ratingKey',0)),
               'duration'     : duration,
               'resume'       : int (int(view_offset)/1000) }

    #Determine what tupe of watched flag [overlay] to use
    if int(movie.get('viewCount',0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount',0)) == 0:
        details['playcount'] = 0

    #Extended Metadata
    if g_skipmetadata == "false":
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)

    #Add extra media flag data
    if g_skipmediaflags == "false":
        extraData.update(getMediaData(mediaarguments))

    #Build any specific context menu entries
    if g_skipcontext == "false":
        context=buildContextMenu(url, extraData)
    else:
        context=None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extraData['mode']=_MODE_PLAYLIBRARY
    u="http://%s%s?t=%s" % (server, extraData['key'], randomNumber)

    addGUIItem(u,details,extraData,context,folder=False)
    return

def getMediaData ( tag_dict ):
    '''
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    '''
    printDebug("== ENTER: getMediaData ==", False)

    return     {'VideoResolution'    : tag_dict.get('videoResolution','') ,
                'VideoCodec'         : tag_dict.get('videoCodec','') ,
                'AudioCodec'         : tag_dict.get('audioCodec','') ,
                'AudioChannels'      : tag_dict.get('audioChannels','') ,
                'VideoAspect'        : tag_dict.get('aspectRatio','') ,
                'xbmc_height'        : tag_dict.get('height') ,
                'xbmc_width'         : tag_dict.get('width') ,
                'xbmc_VideoCodec'    : tag_dict.get('videoCodec') ,
                'xbmc_AudioCodec'    : tag_dict.get('audioCodec') ,
                'xbmc_AudioChannels' : tag_dict.get('audioChannels') ,
                'xbmc_VideoAspect'   : tag_dict.get('aspectRatio') }

def trackTag( server, tree, track ):
    printDebug("== ENTER: trackTAG ==", False)
    xbmcplugin.setContent(pluginhandle, 'songs')

    for child in track:
        for babies in child:
            if babies.tag == "Part":
                partDetails=(dict(babies.items()))

    printDebug( "Part is " + str(partDetails))

    details={'TrackNumber' : int(track.get('index',0)) ,
             'title'       : str(track.get('index',0)).zfill(2)+". "+track.get('title','Unknown').encode('utf-8') ,
             'rating'      : float(track.get('rating',0)) ,
             'album'       : track.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
             'artist'      : track.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 }

    extraData={'type'         : "Music" ,
               'fanart_image' : getFanart(track, server) ,
               'thumb'        : getThumb(track, server) ,
               'ratingKey'    : track.get('key','') }

    if '/resources/mb3.png' in extraData['thumb']:
        printDebug("thumb is default")
        extraData['thumb']=getThumb(tree, server)

    if extraData['fanart_image'] == "":
        extraData['fanart_image']=getFanart(tree, server)

    #If we are streaming, then get the virtual location
    url=mediaType(partDetails,server)

    extraData['mode']=_MODE_BASICPLAY
    u="%s" % (url)

    addGUIItem(u,details,extraData,folder=False)

def photo( url,tree=None ):
    printDebug("== ENTER: photos ==", False)
    server=url.split('/')[2]

    xbmcplugin.setContent(pluginhandle, 'photo')

    tree=getXML(url,tree)
    if tree is None:
        return

    sectionArt=getFanart(tree,server)
    setWindowHeading(tree)
    for picture in tree:

        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') }

        extraData={'thumb'        : getThumb(picture, server) ,
                   'fanart_image' : getFanart(picture, server) ,
                   'type'         : "image" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionArt

        u=getLinkURL(url, picture, server)

        if picture.tag == "Directory":
            extraData['mode']=_MODE_PHOTOS
            addGUIItem(u,details,extraData)

        elif picture.tag == "Photo":

            if tree.get('viewGroup','') == "photo":
                for photo in picture:
                    if photo.tag == "Media":
                        for images in photo:
                            if images.tag == "Part":
                                extraData['key']="http://"+server+images.get('key','')
                                details['size']=int(images.get('size',0))
                                u=extraData['key']

            addGUIItem(u,details,extraData,folder=False)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def music( url, tree=None ):
    printDebug("== ENTER: music ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')

    server=getServerFromURL(url)

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    for grapes in tree:

        if grapes.get('key',None) is None:
            continue

        details={'genre'       : grapes.get('genre','').encode('utf-8') ,
                 'artist'      : grapes.get('artist','').encode('utf-8') ,
                 'year'        : int(grapes.get('year',0)) ,
                 'album'       : grapes.get('album','').encode('utf-8') ,
                 'tracknumber' : int(grapes.get('index',0)) ,
                 'title'       : "Unknown" }


        extraData={'type'        : "Music" ,
                   'thumb'       : getThumb(grapes, server) ,
                   'fanart_image': getFanart(grapes, server) }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        u=getLinkURL(url, grapes, server)

        if grapes.tag == "Track":
            printDebug("Track Tag")
            xbmcplugin.setContent(pluginhandle, 'songs')

            details['title']=grapes.get('track',grapes.get('title','Unknown')).encode('utf-8')
            details['duration']=int(int(grapes.get('totalTime',0))/1000)

            extraData['mode']=_MODE_BASICPLAY
            addGUIItem(u,details,extraData,folder=False)

        else:

            if grapes.tag == "Artist":
                printDebug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                details['title']=grapes.get('artist','Unknown').encode('utf-8')

            elif grapes.tag == "Album":
                printDebug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                details['title']=grapes.get('album','Unknown').encode('utf-8')

            elif grapes.tag == "Genre":
                details['title']=grapes.get('genre','Unknown').encode('utf-8')

            else:
                printDebug("Generic Tag: " + grapes.tag)
                details['title']=grapes.get('title','Unknown').encode('utf-8')

            extraData['mode']=_MODE_MUSIC
            addGUIItem(u,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getThumb( data, server, transcode=False, width=None, height=None ):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''
    
    if g_skipimages == "true":
        return ''
        
    printDebug('getThumb server:' + server)
    #hack!
    id=data.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text
    #thumbnail=getURL('http://'+server+'/mediabrowser/Items/'+str(id)+'/Images?Type=Primary&format=xml')
    thumbnail=('http://'+server+'/mediabrowser/Items/'+str(id)+'/Images/Primary?Format=png')
    printDebug('The temp path is:' + __addondir__)
    from urllib import urlretrieve
    try:
      with open(__addondir__ + id + '.png'):
         printDebug('Already there')
    except IOError:
         urlretrieve(thumbnail, (__addondir__ + id+ '.png'))
    #printDebug('getThumb html:' + th)
    #tree = etree.fromstring(html).getiterator('ImageType')
    #printDebug("html: " + html)
    #for stupidCrap in tree:
    #thumbnail=tree.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Primary')
    thumbnail=(__addondir__ + id + '.png')
    printDebug('Thumb:' + thumbnail)
    return thumbnail
    


    if thumbnail == '':
        return g_loc+'/resources/mb3.png'

    elif thumbnail[0:4] == "http" :
        return thumbnail

    elif thumbnail[0] == '/':
        if transcode:
            return photoTranscode(server,'http://localhost:32400'+thumbnail,width,height)
        else:
            return 'http://'+server+thumbnail

    else:
        return g_loc+'/resources/mb3.png'

def getFanart( data, server, transcode=False ):
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''
    if g_skipimages == "true":
        return ''
    id=data.find('{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}Id').text
    fanart=('http://'+server+'/mediabrowser/Items/'+str(id)+'/Images/Backdrop?Format=png')
    from urllib import urlretrieve
    try:
      with open(__addondir__+'fanart_' + id + '.png'):
         printDebug('Already there')
    except IOError:
         urlretrieve(fanart, (__addondir__+'fanart_' + id+ '.png'))
    fanart=(__addondir__+'fanart_' + id + '.png')
    printDebug('Fanart:' + fanart)
    return fanart

def getServerFromURL( url ):
    '''
    Simply split the URL up and get the server portion, sans port
    @ input: url, woth or without protocol
    @ return: the URL server
    '''
    if url[0:4] == "http":
        return url.split('/')[2]
    else:
        return url.split('/')[0]

def getLinkURL( url, pathData, server ):
    '''
        Investigate the passed URL and determine what is required to
        turn it into a usable URL
        @ input: url, XML data and PM server address
        @ return: Usable http URL
    '''
    printDebug("== ENTER: getLinkURL ==")
    path=pathData.get('key','')
    printDebug("Path is " + path)

    if path == '':
        printDebug("Empty Path")
        return

    #If key starts with http, then return it
    if path[0:4] == "http":
        printDebug("Detected http link")
        return path

    #If key starts with a / then prefix with server address
    elif path[0] == '/':
        printDebug("Detected base path link")
        return 'http://%s%s' % ( server, path )

    elif path[0:5] == "rtmp:":
        printDebug("Detected  link")
        return path

    #Any thing else is assumed to be a relative path and is built on existing url
    else:
        printDebug("Detected relative link")
        return "%s/%s" % ( url, path )

    return url


def install( url, name ):
    printDebug("== ENTER: install ==", False)
    tree=getXML(url)
    if tree is None:
        return

    operations={}
    i=0
    for plums in tree.findall('Directory'):
        operations[i]=plums.get('title')

        #If we find an install option, switch to a yes/no dialog box
        if operations[i].lower() == "install":
            printDebug("Not installed.  Print dialog")
            ret = xbmcgui.Dialog().yesno("XBMB3C","About to install " + name)

            if ret:
                printDebug("Installing....")
                installed = getURL(url+"/install")
                tree = etree.fromstring(installed)

                msg=tree.get('message','(blank)')
                printDebug(msg)
                xbmcgui.Dialog().ok("XBMB3C",msg)
            return

        i+=1

    #Else continue to a selection dialog box
    ret = xbmcgui.Dialog().select("This plugin is already installed..",operations.values())

    if ret == -1:
        printDebug("No option selected, cancelling")
        return

    printDebug("Option " + str(ret) + " selected.  Operation is " + operations[ret])
    u=url+"/"+operations[ret].lower()

    action = getURL(u)
    tree = etree.fromstring(action)

    msg=tree.get('message')
    printDebug(msg)
    xbmcgui.Dialog().ok("XBMB3C",msg)
    xbmc.executebuiltin("Container.Refresh")


    return


def photoTranscode( server, url, width=1280, height=720 ):
        return 'http://%s/photo/:/transcode?url=%s&width=%s&height=%s' % (server, urllib.quote_plus(url), width, height)

def libraryRefresh( url ):
    printDebug("== ENTER: libraryRefresh ==", False)
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\",Library Refresh started,100)")
    return

def watched( url ):
    printDebug("== ENTER: watched ==", False)

    if url.find("unscrobble") > 0:
        printDebug ("Marking as unwatched with: " + url)
    else:
        printDebug ("Marking as watched with: " + url)

    html=getURL(url)
    xbmc.executebuiltin("Container.Refresh")

    return

def displayServers( url ):
    printDebug("== ENTER: displayServers ==", False)
    type=url.split('/')[2]
    printDebug("Displaying entries for " + type)
    Servers = discoverAllServers()
    Servers_list=len(Servers)

    #For each of the servers we have identified
    for mediaserver in Servers.values():

        details={'title' : mediaserver.get('serverName','Unknown') }

        if mediaserver.get('token',None):
            extraData={'token' : mediaserver.get('token') }
        else:
            extraData={}

#            elif type == "music":
#            extraData['mode']=_MODE_MUSIC
#            s_url='http://%s:%s/music' % ( mediaserver.get('server', ''),mediaserver.get('port') )
#            if Servers_list == 1:
#                music(s_url+getAuthDetails(extraData,prefix="?"))
#        return

#        elif type == "photo":
#            extraData['mode']=_MODE_PHOTOS
#            s_url='http://%s:%s/photos' % ( mediaserver.get('server', ''),mediaserver.get('port') )
#            if Servers_list == 1:
#                photo(s_url+getAuthDetails(extraData,prefix="?"))
#                return

        addGUIItem(s_url, details, extraData )

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def deleteMedia( url ):
    printDebug("== ENTER: deleteMedia ==", False)
    printDebug ("deleteing media at: " + url)

    return_value = xbmcgui.Dialog().yesno("Confirm file delete?","Delete this item? This action will delete media and associated data files.")

    if return_value:
        printDebug("Deleting....")
        installed = getURL(url,type="DELETE")
        xbmc.executebuiltin("Container.Refresh")

    return True

        
def setWindowHeading(tree) :
    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    #WINDOW.setProperty("heading", tree.get('title2',tree.get('title1','')))

def setMasterServer () :
    printDebug("== ENTER: setmasterserver ==", False)

    servers=getMasterServer(True)
    printDebug(str(servers))
    
    current_master=__settings__.getSetting('masterServer')
    
    displayList=[]
    for address in servers:
        found_server = address['name']
        if found_server == current_master:
            found_server = found_server+"*"
        displayList.append(found_server)
    
    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select master server',displayList)
    if result == -1:
        return False

    printDebug("Setting master server to: %s" % (servers[result]['name'],))
    __settings__.setSetting('masterServer',servers[result]['name'])
    return
###########################################################################  
##Start of Main
###########################################################################
printDebug( "XBMB3C -> Script argument is " + str(sys.argv[1]), False)

try:
    params=get_params(sys.argv[2])
except:
    params={}

#Now try and assign some data to them
param_url=params.get('url',None)

if param_url and ( param_url.startswith('http') or param_url.startswith('file') ):
        param_url = urllib.unquote(param_url)

param_name=urllib.unquote_plus(params.get('name',""))
mode=int(params.get('mode',-1))
param_transcodeOverride=int(params.get('transcode',0))
param_identifier=params.get('identifier',None)
param_indirect=params.get('indirect',None)
force=params.get('force')

if str(sys.argv[1]) == "skin":
     skin()
elif str(sys.argv[1]) == "shelf":
     shelf()
elif str(sys.argv[1]) == "channelShelf":
     shelfChannel()
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
elif sys.argv[1] == "watch":
    url=sys.argv[2]
    watched(url)
elif sys.argv[1] == "setting":
    __settings__.openSettings()
    WINDOW = xbmcgui.getCurrentWindowId()
    if WINDOW == 10000:
        printDebug("Currently in home - refreshing to allow new settings to be taken")
        xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
elif sys.argv[1] == "refreshXBMB3C":
    server_list = discoverAllServers()
    skin(server_list)
    shelf(server_list)
    shelfChannel(server_list)
elif sys.argv[1] == "delete":
    url=sys.argv[2]
    deleteMedia(url)
elif sys.argv[1] == "refresh":
    xbmc.executebuiltin("Container.Refresh")
elif sys.argv[1] == "subs":
    url=sys.argv[2]
    alterSubs(url)
elif sys.argv[1] == "audio":
    url=sys.argv[2]
    alterAudio(url)
elif sys.argv[1] == "master":
    setMasterServer()
else:

    pluginhandle = int(sys.argv[1])

    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    WINDOW.clearProperty("heading")
    #mode=_MODE_BASICPLAY
    if g_debug == "true":
        print "XBMB3C -> Mode: "+str(mode)
        print "XBMB3C -> URL: "+str(param_url)
        print "XBMB3C -> Name: "+str(param_name)
        print "XBMB3C -> identifier: " + str(param_identifier)

    #Run a function based on the mode variable that was passed in the URL
    if ( mode == None ) or ( param_url == None ) or ( len(param_url)<1 ):
        displaySections()

    elif mode == _MODE_GETCONTENT:
        getContent(param_url)

    elif mode == _MODE_TVSHOWS:
        TVShows(param_url)

    elif mode == _MODE_MOVIES:
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE )
        Movies(param_url)

    elif mode == _MODE_ARTISTS:
        artist(param_url)

    elif mode == _MODE_TVSEASONS:
        TVSeasons(param_url)

    elif mode == _MODE_PLAYLIBRARY:
        playLibraryMedia(param_url,force=force)

    elif mode == _MODE_PLAYSHELF:
        playLibraryMedia(param_url,full_data=True)

    elif mode == _MODE_TVEPISODES:
        TVEpisodes(param_url)

    elif mode == _MODE_PROCESSXML:
        processXML(param_url)

    elif mode == _MODE_BASICPLAY:
        PLAY(param_url)

    elif mode == _MODE_ALBUMS:
        albums(param_url)

    elif mode == _MODE_TRACKS:
        tracks(param_url)

    elif mode == _MODE_PHOTOS:
        photo(param_url)

    elif mode == _MODE_MUSIC:
        music(param_url)

    elif mode == _MODE_VIDEOPLUGINPLAY:
        videoPluginPlay(param_url,param_identifier,param_indirect)

    elif mode == _MODE_CHANNELINSTALL:
        install(param_url,param_name)

    elif mode == _MODE_CHANNELVIEW:
        channelView(param_url)

    elif mode == _MODE_DISPLAYSERVERS:
        displayServers(param_url)

    elif mode == _MODE_PLAYLIBRARY_TRANSCODE:
        playLibraryMedia(param_url,override=True)

    elif mode == _MODE_CHANNELSEARCH:
        channelSearch( param_url, params.get('prompt') )

    elif mode == _MODE_CHANNELPREFS:
        channelSettings ( param_url, params.get('id') )

    elif mode == _MODE_SHARED_MOVIES:
        displaySections(filter="movies", shared=True)

    elif mode == _MODE_SHARED_SHOWS:
        displaySections(filter="tvshows", shared=True)
        
    elif mode == _MODE_SHARED_PHOTOS:
        displaySections(filter="photos", shared=True)
        
    elif mode == _MODE_SHARED_MUSIC:
        displaySections(filter="music", shared=True)

print "===== XBMB3C STOP ====="

#clear done and exit.
sys.modules.clear()
