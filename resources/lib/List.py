import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import os
import json
import threading
import sys
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils
from Database import Database
from urlparse import urlparse

_MODE_BASICPLAY=12
logLevel = 1
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
_MODE_GETCONTENT=0
_MODE_SEARCH=2
_MODE_SETVIEWS=3
_MODE_CAST_LIST=14
_MODE_SHOW_SEARCH=18

__cwd__ = __settings__.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath( os.path.join( __cwd__) )
__language__     = __addon__.getLocalizedString

#define our global download utils
downloadUtils = DownloadUtils()
db = Database()

# EXPERIMENTAL    
class List():
    addonSettings = None
    __addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
    __addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 
    __language__     = __addon__.getLocalizedString
    
    
    def printDebug(self, msg, level = 1):
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
                    
    def processFast(self, url, results, progress, pluginhandle):
        global viewType
        cast=['None']
        self.printDebug("== ENTER: processFast ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        self.printDebug("Processing secondary menus")
        xbmcplugin.setContent(pluginhandle, 'movies')
        server = self.getServerFromURL(url)
        
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            

        dirItems = []
        result = results.get("Items")

        item_count = db.get("MB3TotalMovies")
        current_item = 1;
        self.setWindowHeading(url, pluginhandle)
        
        for item in result:
            id = str(item.get("Id")).encode('utf-8')
            guiid = id
            isFolder = "false" #fix
           
            item_type = "Movie"
         
            viewType=""
            xbmcplugin.setContent(pluginhandle, 'movies')
            viewType="_MOVIES"
            
            premieredate = ""
            
            # Process MediaStreams
            channels = ''
            videocodec = ''
            audiocodec = ''
            height = ''
            width = ''
            aspectratio = '1:1'
            aspectfloat = 1.85
            tempTitle="Paco"
            if(item.get("Name") != None):
                temp = item.get("Name")
                tempTitle=temp.encode('utf-8')
            else:
                tempTitle = "Missing Title"
            details={'title'        : tempTitle, #db.get(id + ".Name"),
                     'plot'         : db.get(id + ".Overview"),
                     }
            # Populate the extraData list
            extraData={'itemtype'     : item_type}
                       

            extraData['mode'] = _MODE_GETCONTENT
            
            u = server+',;'+id
            folder=False



            
            if extraData.get('mode',None) is None:
                mode="&mode=0"
            else:
                mode="&mode=%s" % extraData['mode']
            
            # play or show info
            selectAction = __settings__.getSetting('selectAction')
            
            #Create the URL to pass to the item
            if 'mediabrowser/Videos' in url:
                if(selectAction == "1"):
                    u = sys.argv[0] + "?id=" + id + "&mode=" + str(_MODE_ITEM_DETAILS)
                else:
                    u = sys.argv[0] + "?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            elif url.startswith('http') or url.startswith('file'):
                u = sys.argv[0]+"?url="+urllib.quote(url)+mode
            else:
                if(selectAction == "1"):
                    u = sys.argv[0] + "?id=" + id + "&mode=" + str(_MODE_ITEM_DETAILS)
                else:
                    u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            
            #Create the ListItem that will be displayed
            thumbPath=db.get(id + ".Primary")
            
            addCounts = __settings__.getSetting('addCounts') == 'true'
            
            WINDOW = xbmcgui.Window( 10000 )
            if WINDOW.getProperty("addshowname") == "true":
                if db.get(id + ".LocationType") == "Virtual":
                    listItemName = extraData.get('premieredate').decode("utf-8") + u" - " + details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + details.get('season').decode("utf-8") + u"E" + details.get('title','Unknown').decode("utf-8")
                    if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                        listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
                    list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
                else:
                    if details.get('season') == None:
                        season = '0'
                    else:
                        season = details.get('season')
                    listItemName = details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + season + u"E" + details.get('title','Unknown').decode("utf-8")
                    if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                        listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
                    list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
            else:
                listItemName = details.get('title','Unknown')
                if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                    listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
                list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
            self.printDebug("Setting thumbnail as " + thumbPath, level=2)
            
            # calculate percentage
            cappedPercentage = None
            if (extraData.get('resumetime') != None and int(extraData.get('resumetime')) > 0):
                duration = float(extraData.get('duration'))
                if(duration > 0):
                    resume = float(extraData.get('resumetime')) / 60.0
                    percentage = int((resume / duration) * 100.0)
                    cappedPercentage = percentage - (percentage % 10)
                    if(cappedPercentage == 0):
                        cappedPercentage = 10
                    if(cappedPercentage == 100):
                        cappedPercentage = 90
                    list.setProperty("complete_percentage", str(cappedPercentage))          
            
            # add resume percentage text to titles
            addResumePercent = __settings__.getSetting('addResumePercent') == 'true'
            if (addResumePercent and details.get('title') != None and cappedPercentage != None):
                details['title'] = details.get('title') + " (" + str(cappedPercentage) + "%)"
            
            #Set the properties of the item, such as summary, name, season, etc
            #list.setInfo( type=extraData.get('type','Video'), infoLabels=details )
            if ( not folder):
                #list.setProperty('IsPlayable', 'true')
                if extraData.get('type','video').lower() == "video":
                    list.setProperty('TotalTime', str(extraData.get('duration')))
                    list.setProperty('ResumeTime', str(extraData.get('resumetime')))
            
            list.setArt({'poster':db.get(id + ".poster")})
            list.setArt({'tvshow.poster':db.get(id + ".tvshow.poster")})
            list.setArt({'clearlogo':db.get(id + ".Logo")})
            list.setArt({'discart':db.get(id + ".Disc")})
            list.setArt({'banner':db.get(id + ".Banner")})
            list.setArt({'clearart':db.get(id + ".Art")})
            list.setArt({'landscape':db.get(id + ".Thumb")})
            
            list.setProperty('fanart_image', db.get(id + ".Backdrop"))
            list.setProperty('small_poster', db.get(id + ".Primary2"))
            list.setProperty('tiny_poster', db.get(id + ".Primary4"))
            list.setProperty('medium_poster', db.get(id + ".Primary3"))
            list.setProperty('small_fanartimage', db.get(id + ".Backdrop2"))
            list.setProperty('medium_fanartimage', db.get(id + ".Backdrop3"))
            list.setProperty('medium_landscape', db.get(id + ".Thumb3"))
            list.setProperty('fanart_noindicators', db.get(id + ".BackdropNoIndicators"))
           
            menuItems = self.addContextMenu(details, extraData, folder)
            if(len(menuItems) > 0):
                list.addContextMenuItems( menuItems, True )
            videoInfoLabels = {}


            
            if(extraData.get('type') == None or extraData.get('type') == "Video"):
                videoInfoLabels.update(details)
            else:
                list.setInfo( type = extraData.get('type','Video'), infoLabels = details )
            
            videoInfoLabels["duration"] = extraData.get("duration")
            videoInfoLabels["playcount"] = extraData.get("playcount")
            if (extraData.get('favorite') == 'true'):
                videoInfoLabels["top250"] = "1"    
                
            videoInfoLabels["mpaa"] = db.get(id + ".OfficialRating")
            videoInfoLabels["rating"] = db.get(id + ".CommunityRating")
            videoInfoLabels["year"] = db.get(id + ".ProductionYear")
            list.setProperty('CriticRating', db.get(id + ".CriticRating"))
            list.setProperty('ItemType', item_type)


            videoInfoLabels["director"] = extraData.get('director')
            videoInfoLabels["writer"] = extraData.get('writer')
            videoInfoLabels["studio"] = extraData.get('studio')
            videoInfoLabels["genre"] = extraData.get('genre')

            if extraData.get('premieredate') != None:
                videoInfoLabels["premiered"] = extraData.get('premieredate').decode("utf-8")
            
            videoInfoLabels["episode"] = details.get('episode')
            videoInfoLabels["season"] = details.get('season') 
            list.setInfo('video', videoInfoLabels)
            list.addStreamInfo('video', {'duration': extraData.get('duration'), 'aspect': extraData.get('aspectratio'),'codec': extraData.get('videocodec'), 'width' : extraData.get('width'), 'height' : extraData.get('height')})
            list.addStreamInfo('audio', {'codec': extraData.get('audiocodec'),'channels': extraData.get('channels')})

            if extraData.get('totaltime') != None:
                list.setProperty('TotalTime', extraData.get('totaltime'))
            if extraData.get('TotalSeasons')!=None:
                list.setProperty('TotalSeasons',extraData.get('TotalSeasons'))
            if extraData.get('TotalEpisodes')!=None:  
                list.setProperty('TotalEpisodes',extraData.get('TotalEpisodes'))
            if extraData.get('WatchedEpisodes')!=None:
                list.setProperty('WatchedEpisodes',extraData.get('WatchedEpisodes'))
            if extraData.get('UnWatchedEpisodes')!=None:
                list.setProperty('UnWatchedEpisodes',extraData.get('UnWatchedEpisodes'))
            if extraData.get('NumEpisodes')!=None:
                list.setProperty('NumEpisodes',extraData.get('NumEpisodes'))
            

            
            pluginCastLink = "plugin://plugin.video.xbmb3c?mode=" + str(_MODE_CAST_LIST) + "&id=" + id
            list.setProperty('CastPluginLink', pluginCastLink)
            list.setProperty('ItemGUID', id)
            list.setProperty('id', id)
            list.setProperty('Video3DFormat', details.get('Video3DFormat'))

            dirItems.append((u, list, False))
        
        return dirItems
    # /EXPERIMENTAL
        
    def processDirectory(self, url, results, progress, pluginhandle):
        global viewType
        cast=['None']
        self.printDebug("== ENTER: processDirectory ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        self.printDebug("Processing secondary menus")
        xbmcplugin.setContent(pluginhandle, 'movies')

        server = self.getServerFromURL(url)
        
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            

        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []
        if len(result) == 1 and __settings__.getSetting('autoEnterSingle') == "true":
            if result[0].get("Type") == "Season":
                url="http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + result[0].get("Id") + '&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy=SortName&format=json'
                jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1 )
                results = json.loads(jsonData)
                result=results.get("Items")
        item_count = len(result)
        current_item = 1;
        self.setWindowHeading(url, pluginhandle)
            
        for item in result:
        
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name").encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
            id = str(item.get("Id")).encode('utf-8')
            guiid = id
            isFolder = item.get("IsFolder")
           
            item_type = str(item.get("Type")).encode('utf-8')
                  
            tempEpisode = ""
            if (item.get("IndexNumber") != None):
                episodeNum = item.get("IndexNumber")
                if episodeNum < 10:
                    tempEpisode = "0" + str(episodeNum)
                else:
                    tempEpisode = str(episodeNum)
                    
            tempSeason = ""
            if (str(item.get("ParentIndexNumber")) != None):
                tempSeason = str(item.get("ParentIndexNumber"))
                if item.get("ParentIndexNumber") < 10:
                    tempSeason = "0" + tempSeason
          
            viewType=""
            if item.get("Type") == "Movie":
                xbmcplugin.setContent(pluginhandle, 'movies')
                viewType="_MOVIES"
            elif item.get("Type") == "BoxSet":
                xbmcplugin.setContent(pluginhandle, 'movies')
                viewType="_BOXSETS"          
            elif item.get("Type") == "Series":
                xbmcplugin.setContent(pluginhandle, 'tvshows')
                viewType="_SERIES"
            elif item.get("Type") == "Season":
                xbmcplugin.setContent(pluginhandle, 'seasons')
                viewType="_SEASONS"
                guiid = item.get("SeriesId")
            elif item.get("Type") == "Episode":
                prefix=''
                if __settings__.getSetting('addSeasonNumber') == 'true':
                    prefix = "S" + str(tempSeason)
                    if __settings__.getSetting('addEpisodeNumber') == 'true':
                        prefix = prefix + "E"
                    #prefix = str(tempEpisode)
                if __settings__.getSetting('addEpisodeNumber') == 'true':
                    prefix = prefix + str(tempEpisode)
                if prefix != '':
                    tempTitle = prefix + ' - ' + tempTitle
                xbmcplugin.setContent(pluginhandle, 'episodes')
                viewType="_EPISODES"
                guiid = item.get("SeriesId")
            elif item.get("Type") == "MusicArtist":
                xbmcplugin.setContent(pluginhandle, 'artists')
                viewType='_MUSICARTISTS'
            elif item.get("Type") == "MusicAlbum":
                xbmcplugin.setContent(pluginhandle, 'albums')
                viewType='_MUSICTALBUMS'
            elif item.get("Type") == "Audio":
                xbmcplugin.setContent(pluginhandle, 'songs')
                viewType='_MUSICTRACKS'
            
            if(item.get("PremiereDate") != None):
                premieredatelist = (item.get("PremiereDate")).split("T")
                premieredate = premieredatelist[0]
            else:
                premieredate = ""
            
            # add the premiered date for Upcoming TV    
            if item.get("LocationType") == "Virtual":
                airtime = item.get("AirTime")
                tempTitle = tempTitle + ' - ' + str(premieredate) + ' - ' + str(airtime)     

            #Add show name to special TV collections RAL, NextUp etc
            WINDOW = xbmcgui.Window( 10000 )
            if (WINDOW.getProperty("addshowname") == "true" and item.get("SeriesName") != None):
                tempTitle=item.get("SeriesName").encode('utf-8') + " - " + tempTitle
            else:
                tempTitle=tempTitle

            # Process MediaStreams
            channels = ''
            videocodec = ''
            audiocodec = ''
            height = ''
            width = ''
            aspectratio = '1:1'
            aspectfloat = 1.85
            mediaStreams = item.get("MediaStreams")
            if(mediaStreams != None):
                for mediaStream in mediaStreams:
                    if(mediaStream.get("Type") == "Video"):
                        videocodec = mediaStream.get("Codec")
                        height = str(mediaStream.get("Height"))
                        width = str(mediaStream.get("Width"))
                        aspectratio = mediaStream.get("AspectRatio")
                        if aspectratio != None and len(aspectratio) >= 3:
                            try:
                                aspectwidth,aspectheight = aspectratio.split(':')
                                aspectfloat = float(aspectwidth) / float(aspectheight)
                            except:
                                aspectfloat = 1.85
                    if(mediaStream.get("Type") == "Audio"):
                        audiocodec = mediaStream.get("Codec")
                        channels = mediaStream.get("Channels")
                    
            # Process People
            director=''
            writer=''
            cast=[]
            people = item.get("People")
            if(people != None):
                for person in people:
                    if(person.get("Type") == "Director"):
                        director = director + person.get("Name") + ' ' 
                    if(person.get("Type") == "Writing"):
                        writer = person.get("Name")
                    if(person.get("Type") == "Writer"):
                        writer = person.get("Name")                 
                    if(person.get("Type") == "Actor"):
                        Name = person.get("Name")
                        Role = person.get("Role")
                        if Role == None:
                            Role = ''
                        cast.append(Name)

            # Process Studio
            studio = "" 
            if item.get("SeriesStudio") != None and item.get("SeriesStudio") != '':
                studio = item.get("SeriesStudio")
            # Process Studios old way
            if studio == "":        
              studios = item.get("Studios")
              if(studios != None):
                for studio_string in studios:
                    if studio=="": #Just take the first one
                        temp=studio_string.get("Name")
                        studio=temp.encode('utf-8')
                        
                
            # Process Genres
            genre = ""
            genres = item.get("Genres")
            if(genres != None and genres != []):
                for genre_string in genres:
                    if genre == "": #Just take the first genre
                        genre = genre_string
                    elif genre_string != None:
                        genre = genre + " / " + genre_string
                    
            # Process UserData
            userData = item.get("UserData")
            PlaybackPositionTicks = '100'
            overlay = "0"
            favorite = "false"
            seekTime = 0
            if(userData != None):
                if userData.get("Played") != True:
                    overlay = "7"
                    watched = "true"
                else:
                    overlay = "6"
                    watched = "false"
                if userData.get("IsFavorite") == True:
                    overlay = "5"
                    favorite = "true"
                else:
                    favorite = "false"
                if userData.get("PlaybackPositionTicks") != None:
                    PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
                    reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
                    seekTime = reasonableTicks / 10000
            
            playCount = 0
            if(userData != None and userData.get("Played") == True):
                playCount = 1
            # Populate the details list
            details={'title'        : tempTitle,
                     'plot'         : item.get("Overview"),
                     'episode'      : tempEpisode,
                     #'watched'      : watched,
                     'Overlay'      : overlay,
                     'playcount'    : str(playCount),
                     #'aired'       : episode.get('originallyAvailableAt','') ,
                     'TVShowTitle'  :  item.get("SeriesName"),
                     'season'       : tempSeason,
                     'Video3DFormat' : item.get("Video3DFormat"),
                     }
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"
            TotalSeasons     = 0 if item.get("ChildCount")==None else item.get("ChildCount")
            TotalEpisodes    = 0 if item.get("RecursiveItemCount")==None else item.get("RecursiveItemCount")
            WatchedEpisodes  = 0 if userData.get("UnplayedItemCount")==None else TotalEpisodes-userData.get("UnplayedItemCount")
            UnWatchedEpisodes = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")
            NumEpisodes      = TotalEpisodes
            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'medium_landscape': downloadUtils.getArtwork(item, "Thumb3") ,
                       'small_poster' : downloadUtils.getArtwork(item, "Primary2","0",True) ,
                       'tiny_poster' : downloadUtils.getArtwork(item, "Primary4","0",True) ,
                       'medium_poster': downloadUtils.getArtwork(item, "Primary3","0",True) ,
                       'small_fanartimage' : downloadUtils.getArtwork(item, "Backdrop2") ,
                       'medium_fanartimage' : downloadUtils.getArtwork(item, "Backdrop3") ,
                       'fanart_noindicators' : downloadUtils.getArtwork(item, "BackdropNoIndicators") ,                    
                       'id'           : id ,
                       'guiid'        : guiid ,
                       'mpaa'         : item.get("OfficialRating"),
                       'rating'       : item.get("CommunityRating"),
                       'criticrating' : item.get("CriticRating"), 
                       'year'         : item.get("ProductionYear"),
                       'locationtype' : item.get("LocationType"),
                       'premieredate' : premieredate,
                       'studio'       : studio,
                       'genre'        : genre,
                       'playcount'    : str(playCount),
                       'director'     : director,
                       'writer'       : writer,
                       'channels'     : channels,
                       'videocodec'   : videocodec,
                       'aspectratio'  : str(aspectfloat),
                       'audiocodec'   : audiocodec,
                       'height'       : height,
                       'width'        : width,
                       'cast'         : cast,
                       'favorite'     : favorite,
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'resumetime'   : str(seekTime),
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'RecursiveItemCount' : item.get("RecursiveItemCount"),
                       'RecursiveUnplayedItemCount' : userData.get("UnplayedItemCount"),
                       'TotalSeasons' : str(TotalSeasons),
                       'TotalEpisodes': str(TotalEpisodes),
                       'WatchedEpisodes': str(WatchedEpisodes),
                       'UnWatchedEpisodes': str(UnWatchedEpisodes),
                       'NumEpisodes'  : str(NumEpisodes),
                       'itemtype'     : item_type}
                       
                       
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            
            if isFolder == True:
                SortByTemp = __settings__.getSetting('sortby')
                if SortByTemp == '' and not (item_type == 'Series' or item_type == 'Season' or item_type == 'BoxSet' or item_type == 'MusicAlbum' or item_type == 'MusicArtist'):
                    SortByTemp = 'SortName'
                if item_type=='Series' and __settings__.getSetting('flattenSeasons')=='true':
                    u = 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&IncludeItemTypes=Episode&Recursive=true&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy=SortName'+'&format=json'
                else:
                    u = 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy='+SortByTemp+'&format=json'
                if (item.get("RecursiveItemCount") != 0):
                    dirItems.append(self.addGUIItem(u, details, extraData))
            else:
                u = server+',;'+id
                dirItems.append(self.addGUIItem(u, details, extraData, folder=False))

        return dirItems

    def processSearch(self, url, results, progress, pluginhandle):
        cast=['None']
        self.printDebug("== ENTER: processSearch ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        self.setWindowHeading(url, pluginhandle)
        
        dirItems = []
        result = results.get("SearchHints")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("ItemId")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
            if type=="Series" or type=="MusicArtist" or type=="MusicAlbum" or type=="Folder":
                isFolder = True
            else:
                isFolder = False
            item_type = str(type).encode('utf-8')
            
            tempEpisode = ""
            if (item.get("IndexNumber") != None):
                episodeNum = item.get("IndexNumber")
                if episodeNum < 10:
                    tempEpisode = "0" + str(episodeNum)
                else:
                    tempEpisode = str(episodeNum)
                    
            tempSeason = ""
            if (str(item.get("ParentIndexNumber")) != None):
                tempSeason = str(item.get("ParentIndexNumber"))
          
            if type == "Episode" and __settings__.getSetting('addEpisodeNumber') == 'true':
                tempTitle = str(tempEpisode) + ' - ' + tempTitle

            #Add show name to special TV collections RAL, NextUp etc
            WINDOW = xbmcgui.Window( 10000 )
            if type==None:
                type=''
            if item.get("Series")!=None:
                series=item.get("Series").encode('utf-8')
                tempTitle=type + ": " + series + " - " + tempTitle
            else:
                tempTitle=type + ": " +tempTitle
            # Populate the details list
            details={'title'        : tempTitle,
                     'episode'      : tempEpisode,
                     'TVShowTitle'  : item.get("Series"),
                     'season'       : tempSeason
                     }
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary")  ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "landscape") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            if isFolder == True:
                u = 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&format=json'
                dirItems.append(self.addGUIItem(u, details, extraData))
            elif tempDuration != '0':
                u = server+',;'+id
                dirItems.append(self.addGUIItem(u, details, extraData, folder=False))
        return dirItems

    def processChannels(self, url, results, progress, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processChannels ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
            if type=="ChannelFolderItem":
                isFolder = True
            else:
                isFolder = False
            item_type = str(type).encode('utf-8')
            
            if(item.get("ChannelId") != None):
               channelId = str(item.get("ChannelId")).encode('utf-8')
            
            channelName = ''   
            if(item.get("ChannelName") != None):
               channelName = item.get("ChannelName").encode('utf-8')   
               
            if(item.get("PremiereDate") != None):
                premieredatelist = (item.get("PremiereDate")).split("T")
                premieredate = premieredatelist[0]
            else:
                premieredate = ""
            
            # Process MediaStreams
            channels = ''
            videocodec = ''
            audiocodec = ''
            height = ''
            width = ''
            aspectratio = '1:1'
            aspectfloat = 1.85
            
            mediaSources = item.get("MediaSources")
            if(mediaSources != None):
                mediaStreams = mediaSources[0].get("MediaStreams")
                if(mediaStreams != None):
                    for mediaStream in mediaStreams:
                        if(mediaStream.get("Type") == "Video"):
                            videocodec = mediaStream.get("Codec")
                            height = str(mediaStream.get("Height"))
                            width = str(mediaStream.get("Width"))
                            aspectratio = mediaStream.get("AspectRatio")
                            if aspectratio != None and len(aspectratio) >= 3:
                                try:
                                    aspectwidth,aspectheight = aspectratio.split(':')
                                    aspectfloat = float(aspectwidth) / float(aspectheight)
                                except:
                                    aspectfloat = 1.85
                        if(mediaStream.get("Type") == "Audio"):
                            audiocodec = mediaStream.get("Codec")
                            channels = mediaStream.get("Channels")
                    
            # Process People
            director=''
            writer=''
            cast=[]
            people = item.get("People")
            if(people != None):
                for person in people:
                    if(person.get("Type") == "Director"):
                        director = director + person.get("Name") + ' ' 
                    if(person.get("Type") == "Writing"):
                        writer = person.get("Name")
                    if(person.get("Type") == "Writer"):
                        writer = person.get("Name")                 
                    if(person.get("Type") == "Actor"):
                        Name = person.get("Name")
                        Role = person.get("Role")
                        if Role == None:
                            Role = ''
                        cast.append(Name)

            # Process Studios
            studio = ""
            studios = item.get("Studios")
            if(studios != None):
                for studio_string in studios:
                    if studio=="": #Just take the first one
                        temp=studio_string.get("Name")
                        studio=temp.encode('utf-8')
            # Process Genres
            genre = ""
            genres = item.get("Genres")
            if(genres != None and genres != []):
                for genre_string in genres:
                    if genre == "": #Just take the first genre
                        genre = genre_string
                    elif genre_string != None:
                        genre = genre + " / " + genre_string
                    
            # Process UserData
            userData = item.get("UserData")
            PlaybackPositionTicks = '100'
            overlay = "0"
            favorite = "false"
            seekTime = 0
            if(userData != None):
                if userData.get("Played") != True:
                    overlay = "7"
                    watched = "true"
                else:
                    overlay = "6"
                    watched = "false"
                if userData.get("IsFavorite") == True:
                    overlay = "5"
                    favorite = "true"
                else:
                    favorite = "false"
                if userData.get("PlaybackPositionTicks") != None:
                    PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
                    reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
                    seekTime = reasonableTicks / 10000
            
            playCount = 0
            if(userData != None and userData.get("Played") == True):
                playCount = 1
            # Populate the details list
            details={'title'        : tempTitle,
                     'channelname'  : channelName,
                     'plot'         : item.get("Overview"),
                     'Overlay'      : overlay,
                     'playcount'    : str(playCount)}
            
            viewType=""
            if item.get("Type") == "ChannelVideoItem":
                xbmcplugin.setContent(pluginhandle, 'movies')
                viewType="_CHANNELS"
            elif item.get("Type") == "ChannelAudioItem":
                xbmcplugin.setContent(pluginhandle, 'songs')
                viewType='_MUSICTRACKS'
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary")  ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'id'           : id ,
                       'rating'       : item.get("CommunityRating"),
                       'year'         : item.get("ProductionYear"),
                       'premieredate' : premieredate,
                       'studio'       : studio,
                       'genre'        : genre,
                       'playcount'    : str(playCount),
                       'director'     : director,
                       'writer'       : writer,
                       'channels'     : channels,
                       'videocodec'   : videocodec,
                       'aspectratio'  : str(aspectfloat),
                       'audiocodec'   : audiocodec,
                       'height'       : height,
                       'width'        : width,
                       'cast'         : cast,
                       'favorite'     : favorite,   
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            if type=="Channel":
                u = 'http://' + server + '/mediabrowser/Channels/'+ id + '/Items?userid=' +userid + '&format=json'
                dirItems.append(self.addGUIItem(u, details, extraData))
            
            elif isFolder == True:
                u = 'http://' + server + '/mediabrowser/Channels/'+ channelId + '/Items?userid=' +userid + '&folderid=' + id + '&format=json'
                dirItems.append(self.addGUIItem(u, details, extraData))
            else: 
                u = server+',;'+id
                dirItems.append(self.addGUIItem(u, details, extraData, folder=False))
        return dirItems

    def processPlaylists(self, url, results, progress, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processPlaylists ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = ""          
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
            
            isFolder = False
            item_type = str(type).encode('utf-8')
            
          
            # Populate the details list
            details={'title'        : tempTitle}
            
            xbmcplugin.setContent(pluginhandle, 'movies')
            viewType="_MOVIES"
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary")  ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
          
            u = server+',;'+id+',;'+'PLAYLIST'
            dirItems.append(self.addGUIItem(u, details, extraData, folder=False))
        return dirItems

    def processGenres(self, url, results, progress, content, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processGenres ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            item_type = str(type).encode('utf-8')
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
           
            isFolder = True
       
          
            # Populate the details list
            details={'title'        : tempTitle}
            
            viewType="_MOVIES"
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
                                     
            u = 'http://' + server + '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=' + content + '&Genres=' + item.get("Name") + '&format=json'
            dirItems.append(self.addGUIItem(u, details, extraData))
          
        return dirItems

    def processArtists(self, url, results, progress, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processArtists ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            item_type = str(type).encode('utf-8')
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
           
            isFolder = True
       
          
            # Populate the details list
            details={'title'        : tempTitle}
            
            viewType="_MUSICARTISTS"
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            
            # Somehow need to handle foreign characters .. 
            title = item.get("Name").replace(" ", "+")
                                
            u = 'http://' + server + '/mediabrowser/Users/' + userid + '/Items?SortBy=SortName&Fields=AudioInfo&Recursive=true&SortOrder=Ascending&IncludeItemTypes=MusicAlbum&Artists=' + title + '&format=json'
            dirItems.append(self.addGUIItem(u, details, extraData))
          
        return dirItems

    def processStudios(self, url, results, progress, content, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processStudios ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            item_type = str(type).encode('utf-8')
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
           
            isFolder = True
       
          
            # Populate the details list
            details={'title'        : tempTitle}
            
            viewType="_MOVIES"
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            xbmc.log("XBMB3C - process studios nocode: " + tempTitle)
            tempTitle = tempTitle.replace(' ', '+')
            xbmc.log("XBMB3C - process studios nocode spaces replaced: " + tempTitle)
            tempTitle2 = unicode(tempTitle,'utf-8')          
            u = 'http://' + server + '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=' + content + '&Studios=' + tempTitle2.encode('ascii','ignore') + '&format=json'
            xbmc.log("XBMB3C - process studios: " + u)
            dirItems.append(self.addGUIItem(u, details, extraData))
          
        return dirItems

    def processPeople(self, url, results, progress, content, pluginhandle):
        global viewType
        self.printDebug("== ENTER: processPeople ==")
        parsed = urlparse(url)
        parsedserver,parsedport=parsed.netloc.split(':')
        userid = downloadUtils.getUserId()
        xbmcplugin.setContent(pluginhandle, 'movies')
        detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
        if(__settings__.getSetting('includeStreamInfo') == "true"):
            detailsString += ",MediaStreams"
        if(__settings__.getSetting('includePeople') == "true"):
            detailsString += ",People"
        if(__settings__.getSetting('includeOverview') == "true"):
            detailsString += ",Overview"            
        server = self.getServerFromURL(url)
        dirItems = []
        result = results.get("Items")
        if(result == None):
            result = []

        item_count = len(result)
        current_item = 1;
            
        for item in result:
            id=str(item.get("Id")).encode('utf-8')
            type=item.get("Type").encode('utf-8')
            item_type = str(type).encode('utf-8')
            if(progress != None):
                percentDone = (float(current_item) / float(item_count)) * 100
                progress.update(int(percentDone), __language__(30126) + str(current_item))
                current_item = current_item + 1
            
            if(item.get("Name") != None):
                tempTitle = item.get("Name")
                tempTitle=tempTitle.encode('utf-8')
            else:
                tempTitle = "Missing Title"
                
           
            isFolder = True
       
          
            # Populate the details list
            details={'title'        : tempTitle}
            
            viewType="_MOVIES"
                     
            try:
                tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
                RunTimeTicks = str(item.get("RunTimeTicks", "0"))
            except TypeError:
                try:
                    tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                    RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
                except TypeError:
                    tempDuration = "0"
                    RunTimeTicks = "0"

            # Populate the extraData list
            extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                       'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                       'poster'       : downloadUtils.getArtwork(item, "poster") , 
                       'tvshow.poster': downloadUtils.getArtwork(item, "tvshow.poster") ,
                       'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                       'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                       'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                       'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                       'landscape'    : downloadUtils.getArtwork(item, "landscape") ,
                       'id'           : id ,
                       'year'         : item.get("ProductionYear"),
                       'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                       'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                       'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                       'parenturl'    : url,
                       'totaltime'    : tempDuration,
                       'duration'     : tempDuration,
                       'itemtype'     : item_type}
                       
            if extraData['thumb'] == '':
                extraData['thumb'] = extraData['fanart_image']

            extraData['mode'] = _MODE_GETCONTENT
            xbmc.log("XBMB3C - process people nocode: " + tempTitle)
            tempTitle = tempTitle.replace(' ', '+')
            xbmc.log("XBMB3C - process people nocode spaces replaced: " + tempTitle)
            tempTitle2 = unicode(tempTitle,'utf-8')          
            u = 'http://' + server + '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=' + content + '&Person=' + tempTitle2.encode('ascii','ignore') + '&format=json'
            xbmc.log("XBMB3C - process people: " + u)
            dirItems.append(self.addGUIItem(u, details, extraData))
          
        return dirItems

    def addGUIItem(self, url, details, extraData, folder=True ):

        url = url.encode('utf-8')
    
        self.printDebug("Adding GuiItem for [%s]" % details.get('title','Unknown'), level=2)
        self.printDebug("Passed details: " + str(details), level=2)
        self.printDebug("Passed extraData: " + str(extraData), level=2)
        #self.printDebug("urladdgui:" + str(url))
        if details.get('title','') == '':
            return
    
        if extraData.get('mode',None) is None:
            mode="&mode=0"
        else:
            mode="&mode=%s" % extraData['mode']
        
        # play or show info
        selectAction = __settings__.getSetting('selectAction')
    
        #Create the URL to pass to the item
        if 'mediabrowser/Videos' in url:
            if(selectAction == "1"):
                u = sys.argv[0] + "?id=" + extraData.get('id') + "&mode=" + str(_MODE_ITEM_DETAILS)
            else:
                u = sys.argv[0] + "?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
        elif 'mediabrowser/Search' in url:
            u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_SEARCH)
        #EXPERIMENTAL
        elif 'FastMovies' in url:
            u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_GETCONTENT)        
        #/EXPERIMENTAL
        elif 'SETVIEWS' in url:
            u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_SETVIEWS)     
        elif url.startswith('http') or url.startswith('file'):
            u = sys.argv[0]+"?url="+urllib.quote(url)+mode
        elif 'PLAYLIST' in url:
            u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_PLAYLISTPLAY)
        else:
            if(selectAction == "1"):
                u = sys.argv[0] + "?id=" + extraData.get('id') + "&mode=" + str(_MODE_ITEM_DETAILS)
            else:
                u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
    
        #Create the ListItem that will be displayed
        thumbPath=str(extraData.get('thumb',''))
        
        addCounts = __settings__.getSetting('addCounts') == 'true'
        
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("addshowname") == "true":
            if extraData.get('locationtype')== "Virtual":
                listItemName = extraData.get('premieredate').decode("utf-8") + u" - " + details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + details.get('season').decode("utf-8") + u"E" + details.get('title','Unknown').decode("utf-8")
                if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                    listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
                list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
            else:
                if details.get('season') == None:
                    season = '0'
                else:
                    season = details.get('season')
                listItemName = details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + season + u"E" + details.get('title','Unknown').decode("utf-8")
                if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                    listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
                list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
        else:
            listItemName = details.get('title','Unknown')
            if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
            list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
        self.printDebug("Setting thumbnail as " + thumbPath, level=2)
        
        # calculate percentage
        cappedPercentage = None
        if (extraData.get('resumetime') != None and int(extraData.get('resumetime')) > 0):
            duration = float(extraData.get('duration'))
            if(duration > 0):
                resume = float(extraData.get('resumetime')) / 60.0
                percentage = int((resume / duration) * 100.0)
                cappedPercentage = percentage - (percentage % 10)
                if(cappedPercentage == 0):
                    cappedPercentage = 10
                if(cappedPercentage == 100):
                    cappedPercentage = 90
                list.setProperty("complete_percentage", str(cappedPercentage))          
        
        # add resume percentage text to titles
        addResumePercent = __settings__.getSetting('addResumePercent') == 'true'
        if (addResumePercent and details.get('title') != None and cappedPercentage != None):
            details['title'] = details.get('title') + " (" + str(cappedPercentage) + "%)"
        
        #Set the properties of the item, such as summary, name, season, etc
        #list.setInfo( type=extraData.get('type','Video'), infoLabels=details )
        
        #For all end items    
        if ( not folder):
            #list.setProperty('IsPlayable', 'true')
            if extraData.get('type','video').lower() == "video":
                list.setProperty('TotalTime', str(extraData.get('duration')))
                list.setProperty('ResumeTime', str(extraData.get('resumetime')))
        
        artTypes=['poster', 'tvshow.poster', 'fanart_image', 'clearlogo', 'discart', 'banner', 'clearart', 'landscape', 'small_poster', 'tiny_poster', 'medium_poster','small_fanartimage', 'medium_fanartimage', 'medium_landscape', 'fanart_noindicators']
        
        for artType in artTypes:
            imagePath=str(extraData.get(artType,''))
            list=self.setArt(list,artType, imagePath)
            self.printDebug( "Setting " + artType + " as " + imagePath, level=2)
        
        menuItems = self.addContextMenu(details, extraData, folder)
        if(len(menuItems) > 0):
            list.addContextMenuItems( menuItems, True )
    
        # new way
        videoInfoLabels = {}
        
        if(extraData.get('type') == None or extraData.get('type') == "Video"):
            videoInfoLabels.update(details)
        else:
            list.setInfo( type = extraData.get('type','Video'), infoLabels = details )
        
        videoInfoLabels["duration"] = extraData.get("duration")
        videoInfoLabels["playcount"] = extraData.get("playcount")
        if (extraData.get('favorite') == 'true'):
            videoInfoLabels["top250"] = "1"    
            
        videoInfoLabels["mpaa"] = extraData.get('mpaa')
        videoInfoLabels["rating"] = extraData.get('rating')
        videoInfoLabels["director"] = extraData.get('director')
        videoInfoLabels["writer"] = extraData.get('writer')
        videoInfoLabels["year"] = extraData.get('year')
        videoInfoLabels["studio"] = extraData.get('studio')
        videoInfoLabels["genre"] = extraData.get('genre')
        if extraData.get('premieredate') != None:
            videoInfoLabels["premiered"] = extraData.get('premieredate').decode("utf-8")
        
        videoInfoLabels["episode"] = details.get('episode')
        videoInfoLabels["season"] = details.get('season') 
        
        list.setInfo('video', videoInfoLabels)
        
        list.addStreamInfo('video', {'duration': extraData.get('duration'), 'aspect': extraData.get('aspectratio'),'codec': extraData.get('videocodec'), 'width' : extraData.get('width'), 'height' : extraData.get('height')})
        list.addStreamInfo('audio', {'codec': extraData.get('audiocodec'),'channels': extraData.get('channels')})
        
        if extraData.get('criticrating') != None:
            list.setProperty('CriticRating', str(extraData.get('criticrating')))
        if extraData.get('itemtype') != None:
            list.setProperty('ItemType', extraData.get('itemtype'))
        if extraData.get('totaltime') != None:
            list.setProperty('TotalTime', extraData.get('totaltime'))
        if extraData.get('TotalSeasons')!=None:
            list.setProperty('TotalSeasons',extraData.get('TotalSeasons'))
        if extraData.get('TotalEpisodes')!=None:  
            list.setProperty('TotalEpisodes',extraData.get('TotalEpisodes'))
        if extraData.get('WatchedEpisodes')!=None:
            list.setProperty('WatchedEpisodes',extraData.get('WatchedEpisodes'))
        if extraData.get('UnWatchedEpisodes')!=None:
            list.setProperty('UnWatchedEpisodes',extraData.get('UnWatchedEpisodes'))
        if extraData.get('NumEpisodes')!=None:
            list.setProperty('NumEpisodes',extraData.get('NumEpisodes'))
        
        
        pluginCastLink = "plugin://plugin.video.xbmb3c?mode=" + str(_MODE_CAST_LIST) + "&id=" + str(extraData.get('id'))
        list.setProperty('CastPluginLink', pluginCastLink)
        list.setProperty('ItemGUID', extraData.get('guiid'))
        list.setProperty('id', extraData.get('id'))
        list.setProperty('Video3DFormat', details.get('Video3DFormat'))
            
        return (u, list, folder)

    def addContextMenu(self, details, extraData, folder):
        self.printDebug("Building Context Menus", level=2)
        commands = []
        watched = extraData.get('watchedurl')
        WINDOW = xbmcgui.Window( 10000 )
        if watched != None:
            scriptToRun = PLUGINPATH + "/default.py"
            
            pluginCastLink = "XBMC.Container.Update(plugin://plugin.video.xbmb3c?mode=" + str(_MODE_CAST_LIST) + "&id=" + str(extraData.get('id')) + ")"
            commands.append(( __language__(30100), pluginCastLink))
            
            if extraData.get("playcount") == "0":
                argsToPass = 'markWatched,' + extraData.get('watchedurl')
                commands.append(( __language__(30093), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            else:
                argsToPass = 'markUnwatched,' + extraData.get('watchedurl')
                commands.append(( __language__(30094), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            if extraData.get('favorite') != 'true':
                argsToPass = 'markFavorite,' + extraData.get('favoriteurl')
                commands.append(( __language__(30095), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            else:
                argsToPass = 'unmarkFavorite,' + extraData.get('favoriteurl')
                commands.append(( __language__(30096), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
                
            argsToPass = 'sortby'
            commands.append(( __language__(30097), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
            if 'Ascending' in WINDOW.getProperty("currenturl"):
                argsToPass = 'sortorder'
                commands.append(( __language__(30098), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            else:
                argsToPass = 'sortorder'
                commands.append(( __language__(30099), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
                
            argsToPass = 'genrefilter'
            commands.append(( __language__(30040), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
            if not folder:
                argsToPass = 'playall,' + extraData.get('id')
                commands.append(( __language__(30041), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))  
                
            argsToPass = 'refresh'
            commands.append(( __language__(30042), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
            argsToPass = 'delete,' + extraData.get('deleteurl')
            commands.append(( __language__(30043), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
            if details.get('channelname') == 'Trailers':
                commands.append(( __language__(30046),"XBMC.RunPlugin(%s)" % CP_ADD_URL % details.get('title')))
                
        return(commands)

    def setArt (self, list, name, path): #Duplicate from main
        if name=='thumb' or name=='fanart_image' or name=='small_poster' or name=='tiny_poster'  or name == "medium_landscape" or name=='medium_poster' or name=='small_fanartimage' or name=='medium_fanartimage' or name=='fanart_noindicators':
            list.setProperty(name, path)
        else:#elif xbmcVersionNum >= 13:
            list.setArt({name:path})
        return list

    def getServerFromURL(self, url):  #Duplicate from main
        '''
        Simply split the URL up and get the server portion, sans port
        @ input: url, woth or without protocol
        @ return: the URL server
        '''
        if url[0:4] == "http":
            return url.split('/')[2]
        else:
            return url.split('/')[0]
            
    def setWindowHeading(self, url, pluginhandle) :
        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.setProperty("addshowname", "false")
        WINDOW.setProperty("currenturl", url)
        WINDOW.setProperty("currentpluginhandle", str(pluginhandle))
        if 'ParentId' in url:
            dirUrl = url.replace('items?ParentId=','Items/')
            splitUrl = dirUrl.split('&')
            dirUrl = splitUrl[0] + '?format=json'
            jsonData = downloadUtils.downloadUrl(dirUrl)
            result = json.loads(jsonData)
            for name in result:
                title = name
            WINDOW.setProperty("heading", title)
        elif 'IncludeItemTypes=Episode' in url:
            WINDOW.setProperty("addshowname", "true")        