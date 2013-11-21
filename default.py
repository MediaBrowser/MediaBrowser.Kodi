'''
    @document   : default.py
    @package    : XBMB3C add-on
    @author     : xnappo
    @copyleft   : 2013, xnappo
    @version    : 0.2 (frodo)

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
import re
import xbmcplugin
import xbmcgui
import xbmcaddon
import httplib
import socket
import sys
import os
import time
import inspect
import base64
import random
from urlparse import urlparse

__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )

sDto='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}'
sEntities='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Entities}'
sArrays='{http://schemas.microsoft.com/2003/10/Serialization/Arrays}'

sys.path.append(BASE_RESOURCE_PATH)
XBMB3C_VERSION="0.2"
import httplib2
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
    
#Get the setting from the appropriate file.
DEFAULT_PORT="32400"
_MODE_GETCONTENT=0
_MODE_TVSHOWS=1
_MODE_MOVIES=0
_MODE_ARTISTS=3
_MODE_TVSEASONS=4
_MODE_PLAYLIBRARY=5
_MODE_TVEPISODES=6
_MODE_PROCESSXML=8
_MODE_PLAYSHELF=11
_MODE_BASICPLAY=12
_MODE_ALBUMS=14
_MODE_TRACKS=15
_MODE_PHOTOS=16
_MODE_MUSIC=17
_MODE_VIDEOPLUGINPLAY=18
_MODE_CHANNELINSTALL=20
_MODE_CHANNELVIEW=21
_MODE_DISPLAYSERVERS=22

_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_NEVER_SHOW="2"

#Check debug first...
g_debug = __settings__.getSetting('debug')
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

g_flatten = __settings__.getSetting('flatten')
printDebug("XBMB3C -> Flatten is: "+ g_flatten, False)

if g_debug == "true":
    print "XBMB3C -> Setting debug to " + g_debug
else:
    print "XBMB3C -> Debug is turned off.  Running silent"

g_contextReplace=True

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

    return das_servers
def getUserId( ip_address, port ):
    html = getURL(ip_address+":"+port+"/mediabrowser/Users?format=xml")
    printDebug("userhtml:" + html)
    tree= etree.fromstring(html).getiterator(sDto + 'UserDto')
    for UserDto in tree:
        userid=str(UserDto.find(sDto + 'Id').text)
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
    tree= etree.fromstring(html).getiterator(sDto + 'BaseItemDto')
    for BaseItemDto in tree:
        parentid=str(BaseItemDto.find(sDto + 'Id').text)
    htmlpath=("http://%s:%s/mediabrowser/Users/" % ( ip_address, port))
    html=getURL(htmlpath + userid + "/items?ParentId=" + parentid + "&format=xml")

    if html is False:
        return {}

    
    tree = etree.fromstring(html).getiterator(sDto + "BaseItemDto")
    temp_list=[]
    for BaseItemDto in tree:
        if(str(BaseItemDto.find(sDto + 'RecursiveItemCount').text)!='0'):
            temp_list.append( {'title'      : (str(BaseItemDto.find(sDto + 'Name').text)).encode('utf-8'),
                    'address'    : ip_address+":"+port ,
                    'serverName' : name ,
                    'uuid'       : uuid ,
                    'path'       : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + str(BaseItemDto.find(sDto + 'Id').text) + '&IsVirtualUnaired=false&IsMissing=False&Fields=Path,Overview,Genres,People,MediaStreams&SortBy=Name&format=xml') ,
                    'token'      : str(BaseItemDto.find(sDto + 'Id').text)  ,
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
        
        printDebug("cachetime = "+__settings__.getSetting("cachetime"))
        if XBMB3C_PLATFORM=="Windows":
            conn = httplib2.Http("c:\\temp\\" +".cache", timeout=20)
        else:
            conn = httplib2.Http(__addondir__ +".cache", timeout=20)
        headers={'Accept-encoding': 'gzip', 'Cache-Control' : 'max-age=' + (__settings__.getSetting("cachetime"))}
        resp, link = conn.request("http://"+server+urlPath, "GET",headers=headers)
    except:
        error = "HTTP response error"
    printDebug("Headers: " + str(resp))
    printDebug("====== getURL finished ======")
    return link

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
            u=sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            u=u.replace("\\\\","smb://")
            u=u.replace("\\","/")
        
        #Create the ListItem that will be displayed
        thumb=str(extraData.get('thumb',''))
        if thumb.startswith('http'):
            if '?' in thumb:
                thumbPath=thumb
            else:
                thumbPath=thumb.encode('utf-8') 
        else:
            thumbPath=thumb
        list=xbmcgui.ListItem(details.get('title','Unknown'), iconImage=thumbPath, thumbnailImage=thumbPath)
        printDebug("Setting thumbnail as " + thumbPath)
        #Set the properties of the item, such as summary, name, season, etc
        list.setInfo( type=extraData.get('type','Video'), infoLabels=details )

        #For all end items    
        if ( not folder):
            list.setProperty('IsPlayable', 'true')

            if extraData.get('type','video').lower() == "video":
                list.setProperty('TotalTime', str(extraData.get('duration')))
                list.setProperty('ResumeTime', str(extraData.get('resume')))
            

                
        #try:
            #Then set the number of watched and unwatched, which will be displayed per season
            #list.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
            #list.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
            
            #Hack to show partial flag for TV shows and seasons
            #if extraData.get('partialTV') == 1:            
            #    list.setProperty('TotalTime', '100')
            #    list.setProperty('ResumeTime', '50')
                
        #except: pass

        #Set the fanart image if it has been enabled
        fanart=str(extraData.get('fanart_image',''))
        if '?' in fanart:
            list.setProperty('fanart_image', fanart)
        else:
            list.setProperty('fanart_image', fanart)

        printDebug( "Setting fan art as " + fanart )

        if extraData.get('banner'):
            list.setProperty('banner', extraData.get('banner'))
            printDebug( "Setting banner as " + extraData.get('banner'))

        if context is not None:
            printDebug("Building Context Menus")
            printDebug("Building Context Menus")
            list.addContextMenuItems( context, g_contextReplace )
        mycast=['paco','posta']
        context=[]
        context.append(('Rescan library section', 'displaySections' , ))
        list.addContextMenuItems(context,g_contextReplace)
        list.setInfo('video', {'duration' : extraData.get('duration')})
        #list.setInfo('video', {'playcount' : extraData.get('playcount')})
        #list.setProperty('playcount','1')
        #list.setProperty('ResumeTime',"18")
        #list.setProperty('TotalTime',"18")
        list.setInfo('video', {'director' : extraData.get('director')})
        list.setInfo('video', {'writer' : extraData.get('writer')})
        list.setInfo('video', {'year' : extraData.get('year')})
        list.setInfo('video', {'genre' : extraData.get('genre')})
        #list.setProperty('overlay','8')
        list.setInfo('video', {'cast' : mycast})
        list.setInfo('video', {'credits' : extraData.get('writer')})
        list.setInfo('video', {'episode': details.get('episode')})
        list.setInfo('video', {'season': details.get('season')})        
        list.setInfo('video', {'mpaa': extraData.get('mpaa')})
        list.setInfo('video', {'rating': extraData.get('rating')})
        list.addStreamInfo('video', {'duration': extraData.get('duration'), 'aspect': extraData.get('aspectratio'),'codec': extraData.get('videocodec'), 'width' : extraData.get('width'), 'height' : extraData.get('height')})
        list.addStreamInfo('audio', {'codec': extraData.get('audiocodec'),'channels': extraData.get('channels')})
        return xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=list,isFolder=folder)

def displaySections( filter=None, shared=False ):
        printDebug("== ENTER: displaySections() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')
        #xbmcplugin.setContent(pluginhandle, 'video')

        ds_servers=discoverAllServers()
        numOfServers=len(ds_servers)
        printDebug( "Using list of "+str(numOfServers)+" servers: " +  str(ds_servers))
        
        for section in getAllSections(ds_servers):
        
            if shared and section.get('owned') == '1':
                continue
                
        
            details={'title' : section.get('title', 'Unknown') }

            if len(ds_servers) > 1:
                details['title']=section.get('serverName')+": "+details['title']

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

            path=path+'/all'

            extraData['mode']=mode
            s_url='http://%s%s' % ( section['address'], path)

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

    printDebug("Using context menus " + str(context))

    return context

def remove_html_tags( data ):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

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
        #while xbmc.Player().isPlaying():
                #time.sleep(1)
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
    tree = etree.fromstring(html).getiterator(sDto + "BaseItemDto")

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
    #xbmcplugin.setContent(pluginhandle, 'video')

    server=getServerFromURL(url)
    setWindowHeading(tree)
    for directory in tree:
        try:
            tempTitle=((directory.find(sDto + 'Name').text)).encode('utf-8')
        except TypeError:
            tempTitle="Missing Title"
        id=str(directory.find(sDto + 'Id').text).encode('utf-8')
        isFolder=str(directory.find(sDto + 'IsFolder').text).encode('utf-8')
        type=str(directory.find(sDto + 'Type').text).encode('utf-8')
        try:
            tempEpisode=int(directory.find(sDto + "IndexNumber").text)
            tempSeason=int(directory.find(sDto + "ParentIndexNumber").text)
        except TypeError:
            tempEpisode=0
            tempSeason=0
# Process MediaStreams
        channels=''
        videocodec=''
        audiocodec=''
        height=''
        width=''
        aspectratio='1:1'
        aspectfloat=1.85
        MediaStreams=directory.find(sDto+'MediaStreams')
        for MediaStream in MediaStreams.findall(sEntities + 'MediaStream'):
            if(MediaStream.find(sEntities + 'Type').text=='Video'):
                videocodec=MediaStream.find(sEntities + 'Codec').text
                height=MediaStream.find(sEntities + 'Height').text
                width=MediaStream.find(sEntities + 'Width').text
                aspectratio=MediaStream.find(sEntities + 'AspectRatio').text
                if aspectratio != None:
                    aspectwidth,aspectheight=aspectratio.split(':')
                    aspectfloat=float(aspectwidth)/float(aspectheight)
            if(MediaStream.find(sEntities + 'Type').text=='Audio'):
                audiocodec=MediaStream.find(sEntities + 'Codec').text
                channels=MediaStream.find(sEntities + 'Channels').text
# Process People
        director=''
        writer=''
        cast=list()
        People=directory.find(sDto+'People')
        for BaseItemPerson in People.findall(sDto+'BaseItemPerson'):
            if(BaseItemPerson.find(sDto+'Type').text=='Director'):
                director=director + BaseItemPerson.find(sDto + 'Name').text + ' ' 
            if(BaseItemPerson.find(sDto+'Type').text=='Writing'):
                writer=(BaseItemPerson.find(sDto + 'Name').text)                
            if(BaseItemPerson.find(sDto+'Type').text=='Actor'):
                cast.append(BaseItemPerson.find(sDto + 'Name').text)
# Process Genres
        genre=''
        Genres=directory.find(sDto+'Genres')
        for string in Genres.findall(sArrays+'string'):
            if genre=="": #Just take the first genre
                genre=string.text
            else:
                genre=genre+" / "+string.text
                
# Process UserData
        UserData=directory.find(sDto+'UserData')
        if UserData.find(sDto + "PlayCount") != 0:
            overlay=7
            watched='true'
        else:
            overlay=0
            watched='false'

# Populate the details list
        details={'title'        : tempTitle,
                 'plot'         : directory.find(sDto + "Overview").text ,
                 #'episode'      : tempEpisode ,
                 'watched'      : watched,
                 'overlay'      : overlay,
                 #'playcount'    : UserData.find(sDto + "PlayCount")
                 #'aired'       : episode.get('originallyAvailableAt','') ,
                 #'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') ,
                 #'season'       : tempSeason
                 }
        try:
            tempDuration=str(int(directory.find(sDto + "RunTimeTicks").text)/(10000000*60))
        except TypeError:
            tempDuration='100'

# Populate the extraData list
        extraData={'thumb'        : getThumb(directory, server) ,
                   'fanart_image' : getFanart(directory, server) ,
                   'mpaa'         : directory.find(sDto + "OfficialRating").text ,
                   'rating'       : directory.find(sDto + "CommunityRating").text,
                   'year'         : directory.find(sDto + "ProductionYear").text,
                   'genre'        : genre,
                   'playcount'    : UserData.find(sDto + "PlayCount").text,
                   'director'     : director,
                   'writer'       : writer,
                   'channels'     : channels,
                   'videocodec'   : videocodec,
                   'aspectratio'  : aspectfloat,
                   'audiocodec'   : audiocodec,
                   'height'       : height,
                   'width'        : width,
                   'cast'         : cast,
                   'duration'     : tempDuration}
        if extraData['thumb'] == '':
            extraData['thumb']=extraData['fanart_image']

        extraData['mode']=_MODE_GETCONTENT
        
        if isFolder=='true':
            if type=='Season':
                u= 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&Fields=Path,Overview,Genres,People,MediaStreams&SortBy=SortName&format=xml'
                if (str(directory.find(sDto + 'RecursiveItemCount').text).encode('utf-8')!='0'):
                    addGUIItem(u,details,extraData)
            else:
                u= 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&Fields=Path,Overview,Genres,People,MediaStreams&SortBy=SortName&format=xml'
                if (str(directory.find(sDto + 'RecursiveItemCount').text).encode('utf-8')!='0'):
                    addGUIItem(u,details,extraData)

        else:
            u= directory.find(sDto + "Path").text
            if u == None:
                printDebug('NotReallyThere')
                u=""
            else:
                addGUIItem(u,details,extraData)
        
    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getThumb( data, server, transcode=False, width=None, height=None ):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''
    
    printDebug('getThumb server:' + server)
    id=data.find(sDto + 'Id').text
    thumbnail=('http://'+server+'/mediabrowser/Items/'+str(id)+'/Images/Primary?Format=png')
    printDebug('The temp path is:' + __addondir__)
    from urllib import urlretrieve
    try:
      with open(__addondir__ + id + '.png'):
         printDebug('Already there')
    except IOError:
         urlretrieve(thumbnail, (__addondir__ + id+ '.png'))
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
    id=data.find(sDto + 'Id').text
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

print "===== XBMB3C STOP ====="

#clear done and exit.
sys.modules.clear()
