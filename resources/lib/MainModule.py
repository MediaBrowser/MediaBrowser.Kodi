'''
    @document   : MainModule.py
    @package    : XBMB3C add-on
    @authors    : xnappo, null_pointer, im85288
    @copyleft   : 2013, xnappo

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

import struct
import urllib
import glob
import re
import hashlib
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import httplib
import socket
import sys
import os
import time
import inspect
import base64
import random
import datetime
import cProfile
import pstats
import threading
import hashlib
import StringIO
import gzip
import xml.etree.ElementTree as etree
import json as json

__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 
__language__     = __addon__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

from PlaybackUtils import PlaybackUtils
from DownloadUtils import DownloadUtils
from Database import Database
from ItemInfo import ItemInfo
from Utils import PlayUtils
from ClientInformation import ClientInformation
from PersonInfo import PersonInfo
from SearchDialog import SearchDialog
from DataManager import DataManager
from ConnectionManager import ConnectionManager
from List import List
from API import API
from BackgroundData import BackgroundDataUpdaterThread

XBMB3C_VERSION = ClientInformation().getVersion()
addonName = xbmcaddon.Addon(id='plugin.video.xbmb3c').getAddonInfo('name').upper()

xbmc.log ("===== %s START =====" % addonName)

xbmc.log ("%s -> running Python: %s" % (addonName, str(sys.version_info)))
xbmc.log ("%s -> running XBMB3C: %s" % (addonName, str(XBMB3C_VERSION)))
xbmc.log (xbmc.getInfoLabel( "System.BuildVersion" ))

#Get the setting from the appropriate file.
CP_ADD_URL = 'XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?title=%s)'
_MODE_GETCONTENT=0
_MODE_MOVIES=0
_MODE_SEARCH=2
_MODE_SETVIEWS=3
_MODE_SHOW_SECTIONS=4
_MODE_BASICPLAY=12
_MODE_PLAYLISTPLAY=13
_MODE_CAST_LIST=14
_MODE_PERSON_DETAILS=15
_MODE_WIDGET_CONTENT=16
_MODE_ITEM_DETAILS=17
_MODE_SHOW_SEARCH=18
_MODE_SHOW_PARENT_CONTENT=21

#Check debug first...
logLevel = 0
try:
    logLevel = int(__settings__.getSetting('logLevel'))   
except:
    pass
   
#define our global download utils
downloadUtils = DownloadUtils()
db=Database()
clientInfo = ClientInformation()
dataManager = DataManager()

def printDebug( msg, level = 1):
    if(logLevel >= level):
        if(logLevel == 2):
            try:
                xbmc.log("XBMB3C " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg))
            except UnicodeEncodeError:
                xbmc.log("XBMB3C " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')))
        else:
            try:
                xbmc.log("XBMB3C " + str(level) + " -> " + str(msg))
            except UnicodeEncodeError:
                xbmc.log("XBMB3C " + str(level) + " -> " + str(msg.encode('utf-8')))


def getAuthHeader():
    txt_mac = clientInfo.getMachineId()
    version = clientInfo.getVersion()
    userid = xbmcgui.Window( 10000 ).getProperty("userid")
    deviceName = __settings__.getSetting('deviceName')
    deviceName = deviceName.replace("\"", "_")
    authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"Kodi\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
    headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}
    xbmc.log("XBMB3C Authentication Header : " + str(headers))
    return headers 
            

XBMB3C_PLATFORM = ClientInformation().getPlatform()
xbmc.log ("XBMB3C -> Platform: " + str(XBMB3C_PLATFORM))

g_flatten = __settings__.getSetting('flatten')
printDebug("XBMB3C -> Flatten is: " + g_flatten)

xbmc.log ("XBMB3C -> LogLevel:  " + str(logLevel))

g_contextReplace=True

g_loc = "special://home/addons/plugin.video.XBMB3C"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)',
              }

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None

genreList=[__language__(30069),__language__(30070),__language__(30071),__language__(30072),__language__(30073),__language__(30074),__language__(30075),__language__(30076),__language__(30077),__language__(30078),__language__(30079),__language__(30080),__language__(30081),__language__(30082),__language__(30083),__language__(30084),__language__(30085),__language__(30086),__language__(30087),__language__(30088),__language__(30089)]
sortbyList=[__language__(30059),__language__(30060),__language__(30061),__language__(30062),__language__(30063),__language__(30064),__language__(30065),__language__(30066),__language__(30067)]
   
def getCollections():
    printDebug("== ENTER: getCollections ==")
    __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    MB_server = __settings__.getSetting('ipaddress')+":"+__settings__.getSetting('port')
    userid = downloadUtils.getUserId()
    
    if(userid == None or len(userid) == 0):
        return []
    
    try:
        jsonData = downloadUtils.downloadUrl("http://" + MB_server + "/mediabrowser/Users/" + userid + "/Items/Root?format=json")
    except Exception, msg:
        error = "Get connect : " + str(msg)
        xbmc.log (error)
        return []
    
    printDebug("jsonData : " + jsonData, level=2)
    
    if(jsonData == ""):
        printDebug("No Json data")
        return []
        
    result = json.loads(jsonData)
    
    parentid = result.get("Id")
    printDebug("parentid : " + parentid)
       
    htmlpath = ("http://%s/mediabrowser/Users/" % MB_server)
    jsonData = downloadUtils.downloadUrl(htmlpath + userid + "/items?ParentId=" + parentid + "&Sortby=SortName&format=json")
    printDebug("jsonData : " + jsonData, level=2)
    collections=[]

    if(jsonData == ""):
        printDebug("No Json data")
        return []

    result = json.loads(jsonData)
    result = result.get("Items")
    
    for item in result:
        if(item.get("RecursiveItemCount") != 0):
            Temp = item.get("Name")
            Name = Temp.encode('utf-8')
            if __settings__.getSetting(urllib.quote('sortbyfor'+Name)) == '':
                __settings__.setSetting(urllib.quote('sortbyfor'+Name),'SortName')
                __settings__.setSetting(urllib.quote('sortorderfor'+Name),'Ascending')
            
            total = str(item.get("RecursiveItemCount"))
            section = item.get("CollectionType")
            if section == None:
                section = "movies"
            if section == "movies" or section == "tvshows":
                detailsString=getDetailsString(fast=True)
            else:
                detailsString=getDetailsString(fast=False)
            if section == "movies":
                itemDetailsString=getDetailsString(fast=True)
            elif section == "tvshows":
                itemDetailsString="IncludeItemTypes=Episode" + getDetailsString(fast=False)                
            else:
                itemDetailsString=getDetailsString(fast=False)                
            
            
            collections.append( {'title'      : Name,
                    'address'           : MB_server ,
                    'thumb'             : downloadUtils.getArtwork(item,"Primary") ,
                    'fanart_image'      : downloadUtils.getArtwork(item, "Backdrop") ,
                    'poster'            : downloadUtils.getArtwork(item,"Primary") ,
                    'sectype'           : section,
                    'section'           : section,
                    'guiid'             : item.get("Id"),
                    'path'              : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&IsVirtualUnaired=false&IsMissing=False&Fields=' + detailsString + '&SortOrder='+__settings__.getSetting('sortorderfor'+urllib.quote(Name))+'&SortBy='+__settings__.getSetting('sortbyfor'+urllib.quote(Name))+'&Genres=&format=json&ImageTypeLimit=1'),
                    'collapsed_path'    : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&IsVirtualUnaired=false&IsMissing=False&Fields=' + detailsString + '&SortOrder='+__settings__.getSetting('sortorderfor'+urllib.quote(Name))+'&SortBy='+__settings__.getSetting('sortbyfor'+urllib.quote(Name))+'&Genres=&format=json&CollapseBoxSetItems=true&ImageTypeLimit=1'),
                    'recent_path'       : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&Limit=' + __settings__.getSetting("numRecentMovies") +'&Recursive=true&SortBy=DateCreated&Fields=' + itemDetailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsUnplayed&ExcludeLocationTypes=Virtual&format=json&ImageTypeLimit=1'),
                    'inprogress_path'   : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") +'&Recursive=true&SortBy=DatePlayed&Fields=' + itemDetailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsResumable&Filters=IsNotFolder,IsUnplayed&IsVirtualUnaired=false&IsMissing=False&ExcludeLocationTypes=Virtual&format=json&ImageTypeLimit=1'),
                    'genre_path'        : ('/mediabrowser/Genres?Userid=' + userid + '&parentId=' + item.get("Id") +'&SortBy=SortName&Fields=' + itemDetailsString + '&SortOrder=Ascending&Recursive=true&format=json&ImageTypeLimit=1'),
                    'nextepisodes_path' : ('/mediabrowser/Shows/NextUp/?Userid=' + userid + '&parentId=' + item.get("Id") +'&Recursive=true&SortBy=DateCreated&Fields=' + itemDetailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsUnplayed&IsVirtualUnaired=false&IsMissing=False&ExcludeLocationTypes=Virtual&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1'),
                    'unwatched_path'    : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") +'&Recursive=true&SortBy=SortName&Fields=' + itemDetailsString + '&SortOrder=Ascending&Filters=IsNotFolder,IsUnplayed&ExcludeLocationTypes=Virtual&format=json&ImageTypeLimit=1')})

            printDebug("Title " + Name)    
    
    # Add standard nodes
    detailsString=getDetailsString()
    collections.append({'title':__language__(30170), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + getDetailsString(fast=True) + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30171), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + getDetailsString(fast=True) + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Series&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'' , 'guiid':''})
    collections.append({'title':__language__(30172), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=MusicArtist&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })   
    collections.append({'title':__language__(30173), 'sectype' : 'std.channels', 'section' : 'channels' , 'address' : MB_server , 'path' : '/mediabrowser/Channels?' + userid +'&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })   
    collections.append({'title':__language__(30174), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMovies") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30175), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentTV") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30176), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMusic") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed&IncludeItemTypes=MusicAlbum&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30177), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30178), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Episode&Filters=IsNotFolder,IsResumable&Filters=IsNotFolder,IsUnplayed&IsVirtualUnaired=false&IsMissing=False&ExcludeLocationTypes=Virtual&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30179), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Shows/NextUp/?Userid=' + userid + '&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30180), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=sortName&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsFavorite,IsNotFolder&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30181), 'sectype' : 'std.tvshows', 'section' : 'tvshows'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=sortName&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsFavorite&IncludeItemTypes=Series&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})    
    collections.append({'title':__language__(30182), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsFavorite&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30183), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMusic") + '&Recursive=true&SortBy=PlayCount&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsPlayed&IncludeItemTypes=MusicAlbum&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30184), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=PremiereDate&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsUnplayed&IsVirtualUnaired=true&IsNotFolder&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30185), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&IncludeItemTypes=BoxSet&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30187), 'sectype' : 'std.music', 'section' : 'musicvideos'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&IncludeItemTypes=MusicVideo&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30188), 'sectype' : 'std.photo', 'section' : 'photos'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&IncludeItemTypes=Photo&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30189), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&Filters=IsUnplayed&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30190), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Genres?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30191), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Studios?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30192), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Persons?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Movie&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30193), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=50&Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsUnplayed&IncludeItemTypes=Episode&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30194), 'sectype' : 'std.tvshows', 'section' : 'tvshows'  , 'address' : MB_server , 'path' : '/mediabrowser/Genres?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Series&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30195), 'sectype' : 'std.tvshows', 'section' : 'tvshows'  , 'address' : MB_server , 'path' : '/mediabrowser/Studios?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Series&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30196), 'sectype' : 'std.tvshows', 'section' : 'tvshows'  , 'address' : MB_server , 'path' : '/mediabrowser/Persons?Userid=' + userid + '&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&IncludeItemTypes=Series&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30197), 'sectype' : 'std.playlists', 'section' : 'playlists'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Playlist&mediatype=video&format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30207), 'sectype' : 'std.music', 'section' : 'music'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=Album,SortName&Fields=AudioInfo&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Audio&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })
    collections.append({'title':__language__(30208), 'sectype' : 'std.music', 'section' : 'music'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=AlbumArtist,SortName&Fields=AudioInfo&Recursive=true&SortOrder=Ascending&IncludeItemTypes=MusicAlbum&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })
    collections.append({'title':__language__(30209), 'sectype' : 'std.music', 'section' : 'music'  , 'address' : MB_server , 'path' : '/mediabrowser/Artists/AlbumArtists?SortBy=SortName&Fields=AudioInfo&Recursive=true&SortOrder=Ascending&userid=' + userid + '&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })
    collections.append({'title':__language__(30210), 'sectype' : 'std.music', 'section' : 'music'  , 'address' : MB_server , 'path' : '/mediabrowser/Artists?SortBy=SortName&Fields=AudioInfo&Recursive=true&SortOrder=Ascending&userid=' + userid + '&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })
    collections.append({'title':__language__(30211), 'sectype' : 'std.music', 'section' : 'music'  , 'address' : MB_server , 'path' : '/mediabrowser/MusicGenres?SortBy=SortName&Fields=AudioInfo&Recursive=true&IncludeItemTypes=Audio,MusicVideo&SortOrder=Ascending&userid=' + userid + '&format=json&ImageTypeLimit=1','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })
    collections.append({'title':__language__(30223), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Views?format=json&ImageTypeLimit=1' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    
    collections.append({'title':__language__(30198)                 , 'sectype' : 'std.search', 'section' : 'search'  , 'address' : MB_server , 'path' : '/mediabrowser/Search/Hints?' + userid,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    
    collections.append({'title':__language__(30199)                 , 'sectype' : 'std.setviews', 'section' : 'setviews'  , 'address' : 'SETVIEWS', 'path': 'SETVIEWS', 'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
        
    return collections

def getViewCollections():
    printDebug("== ENTER: getViewCollections ==")
    __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    MB_server = __settings__.getSetting('ipaddress')+":"+__settings__.getSetting('port')
    userid = downloadUtils.getUserId()
    
    if(userid == None or len(userid) == 0):
        return []
    
    try:
        jsonData = downloadUtils.downloadUrl("http://" + MB_server + "/mediabrowser/Users/" + userid + "/Views?format=json&ImageTypeLimit=1")
    except Exception, msg:
        error = "Get connect : " + str(msg)
        xbmc.log (error)
        return []
    
    printDebug("getViewCollections jsonData : " + jsonData, level=2)
    result = json.loads(jsonData)
    
    collections=[]
    result = result.get("Items")
    
    for item in result:
        if(item.get("ChildCount") != 0):
            Name =(item.get("Name")).encode('utf-8')
            if __settings__.getSetting(urllib.quote('sortbyfor'+Name)) == '':
                __settings__.setSetting(urllib.quote('sortbyfor'+Name),'SortName')
                __settings__.setSetting(urllib.quote('sortorderfor'+Name),'Ascending')
            
            total = str(item.get("ChildCount"))
            section = item.get("CollectionType")
            if section == None:
                section = "movies"

            collections.append( {'title'      : Name,
                    'address'           : MB_server ,
                    'thumb'             : downloadUtils.getArtwork(item,"Primary") ,
                    'fanart_image'      : downloadUtils.getArtwork(item, "Backdrop") ,
                    'poster'            : downloadUtils.getArtwork(item,"Primary") ,
                    'sectype'           : section,
                    'section'           : section,
                    'id'             : item.get("Id")})
   
         
    return collections

def markWatched (url):
    downloadUtils.downloadUrl(url, postBody="", type="POST")  
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")  
    id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
    BackgroundDataUpdaterThread().updateItem(id)
    xbmc.executebuiltin("Container.Refresh")
    
def markUnwatched (url):
    downloadUtils.downloadUrl(url, type="DELETE")
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true") 
    id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
    BackgroundDataUpdaterThread().updateItem(id)     
    xbmc.executebuiltin("Container.Refresh")

def markFavorite (url):
    downloadUtils.downloadUrl(url, postBody="", type="POST")
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")
    id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
    BackgroundDataUpdaterThread().updateItem(id)    
    xbmc.executebuiltin("Container.Refresh")
    
def unmarkFavorite (url):
    downloadUtils.downloadUrl(url, type="DELETE")
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")
    id = xbmc.getInfoLabel('ListItem.Property(ItemGUID)')
    BackgroundDataUpdaterThread().updateItem(id)    
    xbmc.executebuiltin("Container.Refresh")

def sortby ():
    sortOptions=["", "SortName","ProductionYear,SortName","PremiereDate,SortName","DateCreated,SortName","CriticRating,SortName","CommunityRating,SortName","PlayCount,SortName","Budget,SortName"]
    sortOptionsText=sortbyList
    return_value=xbmcgui.Dialog().select(__language__(30068),sortOptionsText)
    WINDOW = xbmcgui.Window( 10000 )
    __settings__.setSetting('sortbyfor'+urllib.quote(WINDOW.getProperty("heading")),sortOptions[return_value]+',SortName')
    newurl=re.sub("SortBy.*?&","SortBy="+ sortOptions[return_value] + "&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.xbmb3c/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

def genrefilter ():
    WINDOW = xbmcgui.Window( 10000 )
    genreFilters=["","Action","Adventure","Animation","Crime","Comedy","Documentary","Drama","Fantasy","Foreign","History","Horror","Music","Musical","Mystery","Romance","Science%20Fiction","Short","Suspense","Thriller","Western"]
    genreFiltersText=genreList#["None","Action","Adventure","Animation","Crime","Comedy","Documentary","Drama","Fantasy","Foreign","History","Horror","Music","Musical","Mystery","Romance","Science Fiction","Short","Suspense","Thriller","Western"]
    return_value=xbmcgui.Dialog().select(__language__(30090),genreFiltersText)
    newurl=re.sub("Genres.*?&","Genres="+ genreFilters[return_value] + "&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.xbmb3c/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

    
def sortorder ():
    WINDOW = xbmcgui.Window( 10000 )
    if(__settings__.getSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")))=="Ascending"):
        __settings__.setSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")),'Descending')
        newurl=re.sub("SortOrder.*?&","SortOrder=Descending&",WINDOW.getProperty("currenturl"))
    else:
        __settings__.setSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")),'Ascending')
        newurl=re.sub("SortOrder.*?&","SortOrder=Ascending&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.xbmb3c/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

    
def delete (url):
    return_value = xbmcgui.Dialog().yesno(__language__(30091),__language__(30092))
    if return_value:
        printDebug('Deleting via URL: ' + url)
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30052), __language__(30053))
        downloadUtils.downloadUrl(url, type="DELETE")
        progress.close()
        xbmc.executebuiltin("Container.Refresh")
               
    
def getDetailsString(fast=False):
    if fast==False or __settings__.getSetting('useBackgroundData') != 'true':
        detailsString = "EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks,Metascore,SeriesStudio,AirTime,DateCreated,SeasonUserData"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"       
    else:
        detailsString = "&EnableImages=false&IsFast=true"
    return (detailsString)
    
def displaySections(pluginhandle):
    printDebug("== ENTER: displaySections() ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    dirItems = []
    userid = downloadUtils.getUserId()  
    extraData = { 'fanart_image' : '' ,
                  'type'         : "Video" ,
                  'thumb'        : '' }
    
    # Add collections
    collections = getCollections()
    for collection in collections:
        title=collection.get('title', 'Unknown')
        details = {'title' : title }
        path = collection['path']
        extraData['mode'] = _MODE_MOVIES
        extraData['thumb'] = collection['thumb']
        extraData['poster'] = collection['poster']
        extraData['fanart_image'] = collection['fanart_image']
        extraData['guiid'] = collection['guiid']
        s_url = 'http://%s%s' % ( collection['address'], path)
        printDebug("addGUIItem:" + str(s_url) + str(details) + str(extraData))
        dirItems.append(List().addGUIItem(s_url, details, extraData))
        if collection.get('recent_path') != None:
            details = {'title' : __language__(30220).encode('utf-8') + title }
            s_url = 'http://%s%s' % ( collection['address'], collection['recent_path'])
            printDebug("addGUIItem:" + str(s_url) + str(details) + str(extraData))
            dirItems.append(List().addGUIItem(s_url, details, extraData))

            details = {'title' : __language__(30221).encode('utf-8') + title }
            s_url = 'http://%s%s' % ( collection['address'], collection['inprogress_path'])
            printDebug("addGUIItem:" + str(s_url) + str(details) + str(extraData))
            dirItems.append(List().addGUIItem(s_url, details, extraData))
            if collection.get('section') == "tvshows":
                details = {'title' : __language__(30222).encode('utf-8') + title }
                s_url = 'http://%s%s' % ( collection['address'], collection['nextepisodes_path'])
                printDebug("addGUIItem:" + str(s_url) + str(details) + str(extraData))
                dirItems.append(List().addGUIItem(s_url, details, extraData))            
        
    #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
    xbmcplugin.addDirectoryItems(pluginhandle, dirItems)
    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
        

# function to set the current view permanent in the xbmb3c addon
def setView(containerType,viewId):

    if viewId=="00":
        win = xbmcgui.Window( 10000 )
        curView = xbmc.getInfoLabel("Container.Viewmode")
        
        # get all views from views-file
        skin_view_file = os.path.join(xbmc.translatePath('special://skin'), "views.xml")
        skin_view_file_alt = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
        if xbmcvfs.exists(skin_view_file_alt):
            skin_view_file = skin_view_file_alt
        try:
            tree = etree.parse(skin_view_file)
        except:           
            sys.exit()
        
        root = tree.getroot()
        
        for view in root.findall('view'):
            if curView == view.attrib['id']:
                viewId=view.attrib['value']
    else:
        viewId=viewId    

    if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW_' + containerType) != "disabled":
            __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' + containerType, viewId)
        
def setRecommendedMBSettings(skin):
    if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        if skin == "titan":
            addonSettings.setSetting('includePeople', 'false')
            addonSettings.setSetting('showIndicators', 'false')
            addonSettings.setSetting('showArtIndicators', 'false')
            addonSettings.setSetting('useMenuLoader', 'false')       
            addonSettings.setSetting('selectAction', '0')
        elif skin == "1080XF":
            addonSettings.setSetting('includePeople', 'false')
            addonSettings.setSetting('showArtIndicators', 'true')
            addonSettings.setSetting('includeOverview', 'true')
            addonSettings.setSetting('selectAction', '1') 

def skin( filter=None, shared=False ):
    printDebug("== ENTER: skin() ==")
    
    ConnectionManager().checkServer()
    
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )
    sectionCount=0
    usrMoviesCount=0
    usrMusicCount=0
    usrTVshowsCount=0
    stdMoviesCount=0
    stdTVshowsCount=0
    stdMusicCount=0
    stdPhotoCount=0
    stdChannelsCount=0
    stdPlaylistsCount=0
    stdSearchCount=0
    dirItems = []
    
    allSections = getCollections()
    
    for section in allSections:
    
        details={'title' : section.get('title', 'Unknown') }

        extraData={ 'fanart_image' : '' ,
                    'type'         : "Video" ,
                    'thumb'        : '' ,
                    'token'        : section.get('token',None) }

        mode=_MODE_MOVIES
        window="VideoLibrary"

        extraData['mode']=mode
        modeurl="&mode=0"
        s_url='http://%s%s' % (section['address'], section['path'])
        murl= "?url="+urllib.quote(s_url)+modeurl
        searchurl = "?url="+urllib.quote(s_url)+"&mode=2"

        #Build that listing..
        total = section.get('total')
        if (total == None):
            total = 0
        WINDOW.setProperty("xbmb3c.%d.title"               % (sectionCount) , section.get('title', 'Unknown'))
        WINDOW.setProperty("xbmb3c.%d.path"                % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
        WINDOW.setProperty("xbmb3c.%d.collapsed.path"      % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('collapsed_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.type"                % (sectionCount) , section.get('section'))
        WINDOW.setProperty("xbmb3c.%d.fanart"              % (sectionCount) , section.get('fanart_image'))
        WINDOW.setProperty("xbmb3c.%d.recent.path"         % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.unwatched.path"      % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.inprogress.path"     % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.genre.path"          % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.nextepisodes.path"   % (sectionCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl + ",return)")
        WINDOW.setProperty("xbmb3c.%d.total" % (sectionCount) , str(total))
        if section.get('sectype')=='movies':
            WINDOW.setProperty("xbmb3c.usr.movies.%d.title"         % (usrMoviesCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.usr.movies.%d.path"          % (usrMoviesCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.usr.movies.%d.type"          % (usrMoviesCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.usr.movies.%d.content"       % (usrMoviesCount) , "plugin://plugin.video.xbmb3c/" + murl)
            WINDOW.setProperty("xbmb3c.usr.movies.%d.recent.path"         % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.movies.%d.unwatched.path"      % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.movies.%d.inprogress.path"     % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.movies.%d.genre.path"          % (usrMoviesCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
            printDebug("xbmb3c.usr.movies.%d.title"  % (usrMoviesCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.usr.movies.%d.type"  % (usrMoviesCount) + "section is:" + section.get('section'))   
            usrMoviesCount += 1
        elif section.get('sectype')=='tvshows':
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.title"        % (usrTVshowsCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.path"         % (usrTVshowsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.type"         % (usrTVshowsCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.content"       % (usrTVshowsCount) , "plugin://plugin.video.xbmb3c/" + murl)
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.recent.path"         % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('recent_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.unwatched.path"      % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('unwatched_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.inprogress.path"     % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('inprogress_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.genre.path"          % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('genre_path', '')) + modeurl + ",return)")
            WINDOW.setProperty("xbmb3c.usr.tvshows.%d.nextepisodes.path"   % (usrTVshowsCount) , "ActivateWindow(" + window + ",plugin://plugin.video.xbmb3c/?url=http://" + urllib.quote(section['address'] + section.get('nextepisodes_path', '')) + modeurl + ",return)")
        
            printDebug("xbmb3c.usr.tvshows.%d.title"  % (usrTVshowsCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.usr.tvshows.%d.type"  % (usrTVshowsCount) + "section is:" + section.get('section'))     
            usrTVshowsCount +=1
        elif section.get('sectype')=='music':
            WINDOW.setProperty("xbmb3c.usr.music.%d.title"        % (usrMusicCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.usr.music.%d.path"         % (usrMusicCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.usr.music.%d.type"         % (usrMusicCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.usr.music.%d.content"       % (usrMusicCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.usr.music.%d.title"  % (usrMusicCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.usr.music.%d.type"  % (usrMusicCount) + "section is:" + section.get('section'))
            usrMusicCount +=1   
        elif section.get('sectype')=='std.movies':
            WINDOW.setProperty("xbmb3c.std.movies.%d.title"         % (stdMoviesCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.movies.%d.path"          % (stdMoviesCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.movies.%d.type"          % (stdMoviesCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.movies.%d.content"       % (stdMoviesCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.movies.%d.title"  % (stdMoviesCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.movies.%d.type"  % (stdMoviesCount) + "section is:" + section.get('section'))
            stdMoviesCount +=1
        elif section.get('sectype')=='std.tvshows':
            WINDOW.setProperty("xbmb3c.std.tvshows.%d.title"        % (stdTVshowsCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.tvshows.%d.path"         % (stdTVshowsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.tvshows.%d.type"         % (stdTVshowsCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.tvshows.%d.content"       % (stdTVshowsCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.tvshows.%d.title"  % (stdTVshowsCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.tvshows.%d.type"  % (stdTVshowsCount) + "section is:" + section.get('section'))
            stdTVshowsCount +=1    
        elif section.get('sectype')=='std.music':
            WINDOW.setProperty("xbmb3c.std.music.%d.title"        % (stdMusicCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.music.%d.path"         % (stdMusicCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.music.%d.type"         % (stdMusicCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.music.%d.content"       % (stdMusicCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.music.%d.title"  % (stdMusicCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.music.%d.type"  % (stdMusicCount) + "section is:" + section.get('section'))      
            stdMusicCount +=1     
        elif section.get('sectype')=='std.photo':
            WINDOW.setProperty("xbmb3c.std.photo.%d.title"        % (stdPhotoCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.photo.%d.path"         % (stdPhotoCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.photo.%d.type"         % (stdPhotoCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.photo.%d.content"       % (stdPhotoCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.photo.%d.title"  % (stdPhotoCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.photo.%d.type"  % (stdPhotoCount) + "section is:" + section.get('section'))    
            stdPhotoCount +=1
        elif section.get('sectype')=='std.channels':
            WINDOW.setProperty("xbmb3c.std.channels.%d.title"        % (stdChannelsCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.channels.%d.path"         % (stdChannelsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.channels.%d.type"         % (stdChannelsCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.channels.%d.content"       % (stdChannelsCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.channels.%d.title"  % (stdChannelsCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.channels.%d.type"  % (stdChannelsCount) + "section is:" + section.get('section'))    
            stdChannelsCount +=1
        elif section.get('sectype')=='std.playlists':
            WINDOW.setProperty("xbmb3c.std.playlists.%d.title"        % (stdPlaylistsCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.playlists.%d.path"         % (stdPlaylistsCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
            WINDOW.setProperty("xbmb3c.std.playlists.%d.type"         % (stdPlaylistsCount) , section.get('section'))
            WINDOW.setProperty("xbmb3c.std.playlists.%d.content"       % (stdPlaylistsCount) , "plugin://plugin.video.xbmb3c/" + murl)
            printDebug("xbmb3c.std.playlists.%d.title"  % (stdPlaylistsCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.playlists.%d.type"  % (stdPlaylistsCount) + "section is:" + section.get('section'))    
            stdPlaylistsCount +=1
        elif section.get('sectype')=='std.search':
            WINDOW.setProperty("xbmb3c.std.search.%d.title"        % (stdSearchCount) , section.get('title', 'Unknown'))
            WINDOW.setProperty("xbmb3c.std.search.%d.path"         % (stdSearchCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + searchurl+",return)")
            WINDOW.setProperty("xbmb3c.std.search.%d.type"         % (stdSearchCount) , section.get('section'))
            printDebug("xbmb3c.std.search.%d.title"  % (stdSearchCount) + "title is:" + section.get('title', 'Unknown'))
            printDebug("xbmb3c.std.search.%d.type"  % (stdSearchCount) + "section is:" + section.get('section'))    
            stdSearchCount +=1           #printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + section.get('title').encode('utf-8') + " section - " + section.get('section') + " total - " + str(total) + "]")
        printDebug("PATH in use is: ActivateWindow("+window+",plugin://plugin.video.xbmb3c/" + murl+",return)")
        sectionCount += 1
    
def get_params( paramstring ):
    printDebug("Parameter string: " + paramstring, level=2)
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
    printDebug("XBMB3C -> Detected parameters: " + str(param), level=2)
    return param

def getContent( url, pluginhandle ):
    '''
        This function takes the URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    '''
    global viewType
    printDebug("== ENTER: getContent ==")
    printDebug("URL: " + str(url))    
    userid = downloadUtils.getUserId()
    db.set("userid", userid)
    db.set("mb3Host", __settings__.getSetting('ipaddress'))
    db.set("mb3Port", __settings__.getSetting('port'))
    
    if "NextUp" in url and __settings__.getSetting('sortNextUp') == "true":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TITLE)
        db.set("allowSort","false")
    elif "SortBy=DateCreated" in url:
        db.set("allowSort","false")
    else:
        db.set("allowSort","true")
    result = None
    
    progress = None
    if(__settings__.getSetting('showLoadProgress') == "true" and not xbmc.getCondVisibility("Window.IsActive(Home)")):
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30121))
        progress.update(0, __language__(30122))    

    result = dataManager.GetContent(url)
  
    if(result == None or len(result) == 0):
        if(progress != None):
            progress.close()
        return
    printDebug("JSON DATA: " + str(result), level=2)
    if "Search" in url:
        dirItems = List().processSearch(url, result, progress, pluginhandle)
    elif "Channel" in url:
        dirItems = List().processChannels(url, result, progress, pluginhandle)
    elif "&IncludeItemTypes=Playlist" in url:
        dirItems = List().processPlaylists(url, result, progress, pluginhandle)
    elif "/mediabrowser/Genres?" in url and "&IncludeItemTypes=Movie" in url and "&parentId" not in url:
        dirItems = List().processGenres(url, result, progress, "Movie", pluginhandle)
    elif "/mediabrowser/Genres?" in url and "&IncludeItemTypes=Series" in url and "&parentId" not in url:
        dirItems = List().processGenres(url, result, progress, "Series", pluginhandle)
    elif "/mediabrowser/Genres?" in url and "&parentId" in url:
        dirItems = List().processGenres(url, result, progress, "Movie", pluginhandle)
    elif "/mediabrowser/MusicGenres?" in url:
        dirItems = List().processGenres(url, result, progress, "MusicAlbum", pluginhandle)
    elif "/mediabrowser/Artists?SortBy" in url:
        dirItems = List().processArtists(url,result,progress,pluginhandle)
    elif "/mediabrowser/Studios?" in url and "&IncludeItemTypes=Movie" in url:
        dirItems = List().processStudios(url, result, progress, "Movie", pluginhandle)
    elif "/mediabrowser/Studios?" in url and "&IncludeItemTypes=Series" in url:
        dirItems = List().processStudios(url, result, progress, "Series", pluginhandle)
    elif "/mediabrowser/Persons?" in url and "&IncludeItemTypes=Movie" in url:
        dirItems = List().processPeople(url, result, progress, "Movie", pluginhandle)
    elif "/mediabrowser/Persons?" in url and "&IncludeItemTypes=Series" in url:
        dirItems = List().processPeople(url, result, progress, "Series", pluginhandle)
    else:
        dirItems = List().processDirectory(url, result, progress, pluginhandle)
    xbmcplugin.addDirectoryItems(pluginhandle, dirItems)
    
    if(db.get("viewType") != ""):
        viewId = __settings__.getSetting(xbmc.getSkinDir()+ "_VIEW" + db.get("viewType"))
        if(viewId != "" and viewId != "disabled"):
            viewIdInt = int(viewId)
            xbmc.executebuiltin("Container.SetViewMode(%s)" % viewIdInt)
            
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
    
    if(progress != None):
        progress.update(100, __language__(30125))
        progress.close()
    
    return

def loadJasonData(jsonData):
    return json.loads(jsonData)

    
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
        
def getXbmcVersion():
    version = 0.0
    jsonData = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }') 
    
    result = {}
    if(jsonData != ""):
        result = json.loads(jsonData)
    
    try:
        result = result.get("result")
        versionData = result.get("version")
        version = float(str(versionData.get("major")) + "." + str(versionData.get("minor")))
        printDebug("Version : " + str(version) + " - " + str(versionData), level=0)
    except:
        version = 0.0
        printDebug("Version Error : RAW Version Data : " + str(result), level=0)

    return version        
    
def getCastList(pluginName, handle, params):

    printDebug ("XBMB3C Returning Cast List")
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port
    userid = downloadUtils.getUserId()
    seekTime = 0
    resume = 0
    
    # get the cast list for an item
    jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + params.get("id") + "?format=json", suppress=False, popup=1 )    
    printDebug("CastList(Items) jsonData: " + jsonData, 2)
    
    result = {}
    if(jsonData != ""):
        result = json.loads(jsonData)

    people = result.get("People")
    
    if(people == None):
        return
    
    listItems = []

    for person in people:

        displayName = person.get("Name")
        if(person.get("Role") != None):
            displayName = displayName + " (" + person.get("Role") + ")"
            
        tag = person.get("PrimaryImageTag")
        id = person.get("Id")
        
        baseName = person.get("Name")
        #urllib.quote(baseName)
        baseName = baseName.replace(" ", "+")
        baseName = baseName.replace("&", "_")
        baseName = baseName.replace("?", "_")
        baseName = baseName.replace("=", "_")
            
        if(tag != None):
            thumbPath = downloadUtils.imageUrl(id, "Primary", 0, 400, 400)
            item = xbmcgui.ListItem(label=displayName, iconImage=thumbPath, thumbnailImage=thumbPath)
        else:
            item = xbmcgui.ListItem(label=displayName)
            
        actionUrl = "plugin://plugin.video.xbmb3c?mode=" + str(_MODE_PERSON_DETAILS) +"&name=" + baseName
        
        item.setProperty('IsPlayable', 'false')
        item.setProperty('IsFolder', 'false')
        
        commands = []
        detailsString = getDetailsString()
        url = "http://" + host + ":" + port + "/mediabrowser/Users/" + userid + "/Items/?Recursive=True&Person=PERSON_NAME&Fields=" + detailsString + "&format=json"
        url = urllib.quote(url)
        url = url.replace("PERSON_NAME", baseName)
        pluginCastLink = "XBMC.Container.Update(plugin://plugin.video.xbmb3c?mode=" + str(_MODE_GETCONTENT) + "&url=" + url + ")"
        commands.append(( "Show Other Library Items", pluginCastLink))
        item.addContextMenuItems( commands, g_contextReplace )
        
        itemTupple = (actionUrl, item, False)
        listItems.append(itemTupple)
        
        
    #listItems.sort()
    xbmcplugin.addDirectoryItems(handle, listItems)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

def showItemInfo(pluginName, handle, params):    
    printDebug("showItemInfo Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    
    infoPage = ItemInfo("ItemInfo.xml", __cwd__, "default", "720p")
    
    infoPage.setId(params.get("id"))
    infoPage.doModal()
    WINDOW = xbmcgui.Window( 10025 )
    WINDOW.clearProperty('ItemGUID')
    
    del infoPage
    
def showSearch(pluginName, handle, params):    
    printDebug("showSearch Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    
    searchDialog = SearchDialog("SearchDialog.xml", __cwd__, "default", "720p")

    searchDialog.doModal()
    
    del searchDialog
    
def showPersonInfo(pluginName, handle, params):
    printDebug("showPersonInfo Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

    infoPage = PersonInfo("PersonInfo.xml", __cwd__, "default", "720p")
    
    infoPage.setPersonName(params.get("name"))
    infoPage.doModal()
    
    if(infoPage.showMovies == True):
        xbmc.log("RUNNING_PLUGIN: " + infoPage.pluginCastLink)
        xbmc.executebuiltin(infoPage.pluginCastLink)    
    
    del infoPage
        
def getWigetContent(pluginName, handle, params):
    printDebug("getWigetContent Called" + str(params))
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port    
    
    collectionType = params.get("CollectionType")
    type = params.get("type")
    parentId = params.get("ParentId")
    
    if(type == None):
        printDebug("getWigetContent No Type")
        return
    
    userid = downloadUtils.getUserId()
    
    if(type == "recent"):
        itemsUrl = ("http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId +
            "&Limit=10"
            "&SortBy=DateCreated"
            "&Fields=Path"
            "&SortOrder=Descending"
            "&Filters=IsNotFolder,IsUnplayed"
            "&IncludeItemTypes=Movie,Episode"
            "&CollapseBoxSetItems=false"
            "&IsVirtualUnaired=false"
            "&Recursive=true"
            "&IsMissing=False"
            "&format=json")
    elif(type == "active"):
        itemsUrl = ("http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId +
            "&Limit=10"
            "&SortBy=DatePlayed"
            "&Fields=Path"
            "&SortOrder=Descending"
            "&Filters=IsResumable,IsNotFolder"
            "&IncludeItemTypes=Movie,Episode"
            "&CollapseBoxSetItems=false"
            "&IsVirtualUnaired=false"
            "&Recursive=true"
            "&IsMissing=False"
            "&format=json")
            
    printDebug("WIDGET_DATE_URL: " + itemsUrl, 2)
    
    # get the recent items
    jsonData = downloadUtils.downloadUrl(itemsUrl, suppress=True, popup=1 )
    printDebug("Recent(Items) jsonData: " + jsonData, 2)
    
    result = {}
    if(jsonData != ""):
        result = json.loads(jsonData)
    
    result = result.get("Items")
    if(result == None):
        result = []   

    itemCount = 1
    listItems = []
    for item in result:
        item_id = item.get("Id")

        image_id = item_id
        if item.get("Type") == "Episode":
            image = downloadUtils.getArtwork(item, "Primary")
            fanart = downloadUtils.getArtwork(item, "Primary")        
        else:
            image = downloadUtils.getArtwork(item, "Backdrop")
            fanart = downloadUtils.getArtwork(item, "Backdrop")        
        
        Duration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
        
        name = item.get("Name")
        episodeDetails = ""
        printDebug("WIDGET_DATE_NAME: " + name, 2)
        
        seriesName = ''
        if(item.get("Type") == "Episode" and item.get("SeriesName") != None):

            eppNumber = "X"
            tempEpisodeNumber = "00"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                #if eppNumber < 10:
                #  tempEpisodeNumber = "0" + str(eppNumber)
                #else:
                tempEpisodeNumber = str(eppNumber)     

            seasonNumber = item.get("ParentIndexNumber")
            #if seasonNumber < 10:
            #  tempSeasonNumber = "0" + str(seasonNumber)
            #else:
            tempSeasonNumber = str(seasonNumber)                  
                  
            episodeDetails =  "s" + tempSeasonNumber + "e" + tempEpisodeNumber + " " + name
            name = item.get("SeriesName")
        
        list_item = xbmcgui.ListItem(label=name, iconImage=image, thumbnailImage=image)
        list_item.setLabel2(episodeDetails)
        list_item.setInfo( type="Video", infoLabels={ "year":item.get("ProductionYear"), "duration":str(Duration), "plot":item.get("Overview"), "tvshowtitle":str(seriesName), "premiered":item.get("PremiereDate"), "rating":item.get("CommunityRating") } )
        list_item.setProperty('fanart_image',fanart)
        
        # add count
        list_item.setProperty("item_index", str(itemCount))
        itemCount = itemCount + 1

        # add progress percent
        
        userData = item.get("UserData")
        PlaybackPositionTicks = '100'
        overlay = "0"
        favorite = "false"
        seekTime = 0
        if(userData != None):
            playBackTicks = float(userData.get("PlaybackPositionTicks"))
            if(playBackTicks != None and playBackTicks > 0):
                runTimeTicks = float(item.get("RunTimeTicks", "0"))
                if(runTimeTicks > 0):
                    percentage = int((playBackTicks / runTimeTicks) * 100.0)
                    cappedPercentage = percentage - (percentage % 10)
                    if(cappedPercentage == 0):
                        cappedPercentage = 10
                    if(cappedPercentage == 100):
                        cappedPercentage = 90
                    list_item.setProperty("complete_percentage", str(cappedPercentage))
                
        selectAction = __settings__.getSetting('selectAction')
        if(selectAction == "1"):
            playUrl = "plugin://plugin.video.xbmb3c/?id=" + item_id + '&mode=' + str(_MODE_ITEM_DETAILS)
        else:
            url =  server + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
        
        itemTupple = (playUrl, list_item, False)
        listItems.append(itemTupple)
    
    xbmcplugin.addDirectoryItems(handle, listItems)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    
def showParentContent(pluginName, handle, params):
    printDebug("showParentContent Called" + str(params), 1)
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port
    
    parentId = params.get("ParentId")
    name = params.get("Name")
    useFast = params.get("useFast")
    
    isFast = True
    if(useFast != None and useFast == "false"):
        isFast = False
    
    detailsString = getDetailsString(fast=isFast)
    userid = downloadUtils.getUserId()
    
    contentUrl = (
        "http://" + server +
        "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId +
        "&IsVirtualUnaired=false" +
        "&IsMissing=False" +
        "&Fields=" + detailsString +
        "&format=json")
    
    printDebug("showParentContent Content Url : " + str(contentUrl), 1)
    
    getContent(contentUrl, handle)
    
def showViewList(url, pluginhandle):
    viewCats=[__language__(30302), __language__(30303), __language__(30312), __language__(30305), __language__(30306), __language__(30307), __language__(30308), __language__(30309), __language__(30310), __language__(30311)]
    viewTypes=['_MOVIES', '_BOXSETS', '_CHANNELS', '_SERIES', '_SEASONS', '_EPISODES', '_MUSICARTISTS', '_MUSICALBUMS', '_MUSICVIDEOS', '_MUSICTRACKS']
    if "SETVIEWS" in url:
        for viewCat in viewCats:
            xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.xbmb3c/?url=_SHOWVIEWS' + viewTypes[viewCats.index(viewCat)] + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(viewCat, ''), isFolder=True)
    elif "_SETVIEW_" in url:
        category=url.split('_')[2]
        viewNum=url.split('_')[3]
        __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' +category,viewNum)
        xbmc.executebuiltin("Container.Refresh")    
    else:
        
        skin_view_file = os.path.join(xbmc.translatePath('special://skin'), "views.xml")
        skin_view_file_alt = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
        if xbmcvfs.exists(skin_view_file_alt):
            skin_view_file = skin_view_file_alt
        try:
            tree = etree.parse(skin_view_file)
        except:
            xbmcgui.Dialog().ok(__language__(30135), __language__(30150))            
            sys.exit()
        root = tree.getroot()
        xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.xbmb3c?url=_SETVIEW_'+ url.split('_')[2] + '_' + '' + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(__language__(30301), 'test'))
        
        #disable forced view
        disableForcedViewLabel = __language__(30214)
        if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW_'+ url.split('_')[2]) == "disabled":
            disableForcedViewLabel = disableForcedViewLabel + " (" + __language__(30300) + ")"
        xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.xbmb3c?url=_SETVIEW_'+ url.split('_')[2] + '_' + 'disabled' + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(disableForcedViewLabel, 'test'))

        for view in root.findall('view'):
            if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW_'+ url.split('_')[2]) == view.attrib['value']:
                name=view.attrib['id'] + " (" + __language__(30300) + ")"
            else:
                name=view.attrib['id']
            xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.xbmb3c?url=_SETVIEW_'+ url.split('_')[2] + '_' + view.attrib['value'] + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(name, 'test'))
    
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
    
def checkService():

    timeStamp = xbmcgui.Window(10000).getProperty("XBMB3C_Service_Timestamp")
    loops = 0
    while(timeStamp == ""):
        timeStamp = xbmcgui.Window(10000).getProperty("XBMB3C_Service_Timestamp")
        loops = loops + 1
        if(loops == 40):
            printDebug("XBMB3C Service Not Running, no time stamp, exiting", 0)
            xbmcgui.Dialog().ok(__language__(30135), __language__(30136), __language__(30137))
            sys.exit()
        xbmc.sleep(200)
        
    printDebug ("XBMB3C Service Timestamp: " + timeStamp)
    printDebug ("XBMB3C Current Timestamp: " + str(int(time.time())))
    
    if((int(timeStamp) + 240) < int(time.time())):
        printDebug("XBMB3C Service Not Running, time stamp to old, exiting", 0)
        xbmcgui.Dialog().ok(__language__(30135), __language__(30136), __language__(30137))
        sys.exit()
        

    ###########################################################################  
    ##Start of Main
    ###########################################################################
    
def MainEntryPoint():
    if(logLevel == 2):
        xbmcgui.Dialog().ok(__language__(30132), __language__(30133), __language__(30134))

    printDebug( "XBMB3C -> Script argument date " + str(sys.argv))
    xbmcVersionNum = getXbmcVersion()
    try:
        params=get_params(sys.argv[2])
    except:
        params={}
    printDebug( "XBMB3C -> Script params is " + str(params))
        #Check to see if XBMC is playing - we don't want to do anything if so
    #if xbmc.Player().isPlaying():
    #    printDebug ('Already Playing! Exiting...')
    #    sys.exit()
    #Now try and assign some data to them
    param_url=params.get('url',None)

    if param_url and ( param_url.startswith('http') or param_url.startswith('file') ):
        param_url = urllib.unquote(param_url)

    param_name = urllib.unquote_plus(params.get('name',""))
    mode = int(params.get('mode',-1))
    param_transcodeOverride = int(params.get('transcode',0))
    param_identifier = params.get('identifier',None)
    param_indirect = params.get('indirect',None)
    force = params.get('force')
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("addshowname","false")
    
    try:
        argument1 = str(sys.argv[2])
    except: 
        pass
    
    try:
        argument2 = str(sys.argv[3])
    except: 
        pass
    
    if str(sys.argv[1]) == "skin":
         skin()
    elif sys.argv[1] == "SETVIEW":
         setView(argument1, argument2)
    elif sys.argv[1] == "SETRECOMMENDEDMB3SETTINGS":
         setRecommendedMBSettings(argument1)
    elif sys.argv[1] == "check_server":
         ConnectionManager().checkServer()
    elif sys.argv[1] == "update":
        url=sys.argv[2]
        libraryRefresh(url)
    elif sys.argv[1] == "markWatched":
        url=sys.argv[2]
        markWatched(url)
    elif sys.argv[1] == "markUnwatched":
        url=sys.argv[2]
        markUnwatched(url)
    elif sys.argv[1] == "markFavorite":
        url=sys.argv[2]
        markFavorite(url)
    elif sys.argv[1] == "unmarkFavorite":
        url=sys.argv[2]
        unmarkFavorite(url)    
    elif sys.argv[1] == "setting":
        __settings__.openSettings()
        WINDOW = xbmcgui.getCurrentWindowId()
        if WINDOW == 10000:
            printDebug("Currently in home - refreshing to allow new settings to be taken")
            xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
    elif sys.argv[1] == "delete":
        url=sys.argv[2]
        delete(url)
    elif sys.argv[1] == "refresh":
        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.setProperty("force_data_reload", "true")    
        xbmc.executebuiltin("Container.Refresh")    
    elif sys.argv[1] == "sortby":
        sortby()
    elif sys.argv[1] == "sortorder":
        sortorder()
    elif sys.argv[1] == "genrefilter":
        genrefilter()
    elif sys.argv[1] == "playall":
        startId=sys.argv[2]
        PlaybackUtils().PLAYAllFromHere(startId)
    elif mode == _MODE_CAST_LIST:
        getCastList(sys.argv[0], int(sys.argv[1]), params)
    elif mode == _MODE_PERSON_DETAILS:    
        showPersonInfo(sys.argv[0], int(sys.argv[1]), params)    
    elif mode == _MODE_WIDGET_CONTENT:
        getWigetContent(sys.argv[0], int(sys.argv[1]), params)
    elif mode == _MODE_ITEM_DETAILS:
        showItemInfo(sys.argv[0], int(sys.argv[1]), params)    
    elif mode == _MODE_SHOW_SEARCH:
        showSearch(sys.argv[0], int(sys.argv[1]), params)        
    elif mode == _MODE_SHOW_PARENT_CONTENT:
        checkService()
        ConnectionManager().checkServer()
        pluginhandle = int(sys.argv[1])
        showParentContent(sys.argv[0], int(sys.argv[1]), params)
    else:
        
        checkService()
        ConnectionManager().checkServer()
        
        pluginhandle = int(sys.argv[1])

        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.clearProperty("heading")
        #mode=_MODE_BASICPLAY

        printDebug("XBMB3C -> Mode: "+str(mode))
        printDebug("XBMB3C -> URL: "+str(param_url))
        printDebug("XBMB3C -> Name: "+str(param_name))
        printDebug("XBMB3C -> identifier: " + str(param_identifier))

        #Run a function based on the mode variable that was passed in the URL
        if ( mode == None or mode == _MODE_SHOW_SECTIONS or param_url == None or len(param_url) < 1 ):
            displaySections(pluginhandle)

        elif mode == _MODE_GETCONTENT:
            if __settings__.getSetting('profile') == "true":
            
                xbmcgui.Dialog().ok(__language__(30201), __language__(30202), __language__(30203))
                
                pr = cProfile.Profile()
                pr.enable()
                getContent(param_url, pluginhandle)
                pr.disable()
                ps = pstats.Stats(pr)
                
                fileTimeStamp = time.strftime("%Y-%m-%d %H-%M-%S")
                tabFileName = __addondir__ + "profile_(" + fileTimeStamp + ").tab"
                f = open(tabFileName, 'wb')
                f.write("NumbCalls\tTotalTime\tCumulativeTime\tFunctionName\tFileName\r\n")
                for (key, value) in ps.stats.items():
                    (filename, count, func_name) = key
                    (ccalls, ncalls, total_time, cumulative_time, callers) = value
                    try:
                        f.write(str(ncalls) + "\t" + "{:10.4f}".format(total_time) + "\t" + "{:10.4f}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
                    except ValueError:
                        f.write(str(ncalls) + "\t" + "{0}".format(total_time) + "\t" + "{0}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
                f.close()
                
            else:
                getContent(param_url, pluginhandle)

        elif mode == _MODE_BASICPLAY:
            PlaybackUtils().PLAY(param_url, pluginhandle)
        elif mode == _MODE_PLAYLISTPLAY:
            PlaybackUtils().PLAYPlaylist(param_url, pluginhandle)
        elif mode == _MODE_SEARCH:
            searchString = urllib.quote(xbmcgui.Dialog().input(__language__(30138)))
            printDebug("Search String : " + searchString)
            if searchString == "":
                sys.exit()
            param_url=param_url.replace("Search/Hints?","Search/Hints?SearchTerm="+ searchString + "&UserId=")
            param_url=param_url + "&Fields=" + getDetailsString() + "&format=json"
            xbmc.log("search xml: "+param_url)
            getContent(param_url, pluginhandle)
        elif mode == _MODE_SETVIEWS:
            showViewList(param_url, pluginhandle)

    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.clearProperty("MB3.Background.Item.FanArt")

    dataManager.canRefreshNow = True

    xbmc.log ("===== XBMB3C STOP =====")

