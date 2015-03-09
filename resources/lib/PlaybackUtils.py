
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import urllib
import datetime
import time
import json as json
import inspect

from DownloadUtils import DownloadUtils
from Utils import PlayUtils
from API import API
from Database import Database

class PlaybackUtils():
    
    settings = None
    language = None 
    logLevel = 0
    
    downloadUtils = DownloadUtils()
    db = Database()    
    
    def __init__(self, *args):
    
        self.settings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        self.language = self.settings.getLocalizedString   
        
        try:
            self.logLevel = int(self.settings.getSetting('logLevel'))   
        except:
            pass    

    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            if(self.logLevel == 2):
                try:
                    xbmc.log("XBMB3C PlaybackUtils - > " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg))
                except UnicodeEncodeError:
                    xbmc.log("XBMB3C PlaybackUtils -> " + str(level) + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')))
            else:
                try:
                    xbmc.log("XBMB3C PlaybackUtils -> " + str(level) + " -> " + str(msg))
                except UnicodeEncodeError:
                    xbmc.log("XBMB3C PlaybackUtils -> " + str(level) + " -> " + str(msg.encode('utf-8')))

    def PLAY(self, url, handle):
        self.logMsg("== ENTER: PLAY ==")
        xbmcgui.Window(10000).setProperty("ThemeMediaMB3Disable", "true")
        url = urllib.unquote(url)
        
        urlParts = url.split(',;')
        self.logMsg("PLAY ACTION URL PARTS : " + str(urlParts))
        server = urlParts[0]
        id = urlParts[1]
        autoResume = 0
        if(len(urlParts) > 2):
            autoResume = int(urlParts[2])
            self.logMsg("PLAY ACTION URL AUTO RESUME : " + str(autoResume))
        
        ip,port = server.split(':')
        userid = self.downloadUtils.getUserId()
        seekTime = 0
        resume = 0
        
        id = urlParts[1]
        jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json&ImageTypeLimit=1", suppress=False, popup=1 )
        if(jsonData == ""):
            return
        result = json.loads(jsonData)
        
        # Is this a strm placeholder ?
        IsStrmPlaceholder = False    
        if result.get("Path", "").endswith(".strm"):
            IsStrmPlaceholder = True
        
        resume_result = 1
        
        if IsStrmPlaceholder == False:
            if(autoResume != 0):
              if(autoResume == -1):
                resume_result = 1
              else:
                resume_result = 0
                seekTime = (autoResume / 1000) / 10000
            else:
              userData = result.get("UserData")
              resume_result = 0
                
              if userData.get("PlaybackPositionTicks") != 0:
                reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
                seekTime = reasonableTicks / 10000
                displayTime = str(datetime.timedelta(seconds=seekTime))
                display_list = [ self.language(30106) + ' ' + displayTime, self.language(30107)]
                resumeScreen = xbmcgui.Dialog()
                resume_result = resumeScreen.select(self.language(30105), display_list)
                if resume_result == -1:
                  return

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        
        '''
        # use this to print out the current playlist info
        for x in range(0, len(playlist)):
            self.logMsg("PLAYLIST_ITEM : " + str(playlist[x].getfilename()))
        
        self.logMsg("PLAYLIST_ITEM Position : " + str(playlist.getposition()))
        if(len(playlist) > 0 and "plugin://" in playlist[playlist.getposition()].getfilename()):
            self.logMsg("PLAYLIST_ITEM Removing : " + playlist[playlist.getposition()].getfilename())
            playlist.remove(playlist[playlist.getposition()].getfilename())
        '''
        
        playlist.clear()
        # check for any intros first
        jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "/Intros?format=json&ImageTypeLimit=1", suppress=False, popup=1 )     
        self.logMsg("Intros jsonData: " + jsonData)
        if(jsonData == ""):
            return        
        result = json.loads(jsonData)
                   
         # do not add intros when resume is invoked
        if result.get("Items") != None and (seekTime == 0 or resume_result == 1):
          for item in result.get("Items"):
            id = item.get("Id")
            jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json&ImageTypeLimit=1", suppress=False, popup=1 )
            if(jsonData == ""):
                return            
            result = json.loads(jsonData)
            playurl = PlayUtils().getPlayUrl(server, id, result)
            self.logMsg("Play URL: " + playurl)    
            thumbPath = self.downloadUtils.getArtwork(item, "Primary")
            listItem = xbmcgui.ListItem(path=playurl, iconImage=thumbPath, thumbnailImage=thumbPath)
            self.setListItemProps(server, id, listItem, result)

            # Can not play virtual items
            if (result.get("LocationType") == "Virtual") or (result.get("IsPlaceHolder") == True):
                xbmcgui.Dialog().ok(self.language(30128), self.language(30129))
                return

            watchedurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id
            positionurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayingItems/' + id
            deleteurl = 'http://' + server + '/mediabrowser/Items/' + id
            
            # set the current playing info
            WINDOW = xbmcgui.Window( 10000 )
            WINDOW.setProperty(playurl+"watchedurl", watchedurl)
            WINDOW.setProperty(playurl+"positionurl", positionurl)
            WINDOW.setProperty(playurl+"deleteurl", "")
         
            WINDOW.setProperty(playurl+"runtimeticks", str(result.get("RunTimeTicks")))
            WINDOW.setProperty(playurl+"type", result.get("Type"))
            WINDOW.setProperty(playurl+"item_id", id)
            
            if PlayUtils().isDirectPlay(result) == True:
              if self.settings.getSetting('playFromStream') == "true":
                playMethod = "DirectStream"
              else:
                playMethod = "DirectPlay"
            else:
              playMethod = "Transcode"
            WINDOW.setProperty(playurl+"playmethod", playMethod)
            
            mediaSources = result.get("MediaSources")
            if(mediaSources != None):
              if mediaSources[0].get('DefaultAudioStreamIndex') != None:
                WINDOW.setProperty(playurl+"AudioStreamIndex", str(mediaSources[0].get('DefaultAudioStreamIndex')))  
              if mediaSources[0].get('DefaultSubtitleStreamIndex') != None:
                WINDOW.setProperty(playurl+"SubtitleStreamIndex", str(mediaSources[0].get('DefaultSubtitleStreamIndex')))
            
            playlist.add(playurl, listItem)
       
        id = urlParts[1]
        jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json&ImageTypeLimit=1", suppress=False, popup=1 )   
        if(jsonData == ""):
            return    
        self.logMsg("Play jsonData: " + jsonData)
        result = json.loads(jsonData)
        playurl = PlayUtils().getPlayUrl(server, id, result)
        self.logMsg("Play URL: " + playurl)    
        thumbPath = self.downloadUtils.getArtwork(result, "Primary")
        listItem = xbmcgui.ListItem(path=playurl, iconImage=thumbPath, thumbnailImage=thumbPath)
        self.setListItemProps(server, id, listItem, result)

        # Can not play virtual items
        if (result.get("LocationType") == "Virtual"):
          xbmcgui.Dialog().ok(self.language(30128), self.language(30129))
          return

        watchedurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id
        positionurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayingItems/' + id
        deleteurl = 'http://' + server + '/mediabrowser/Items/' + id

        # set the current playing info
        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.setProperty(playurl+"watchedurl", watchedurl)
        WINDOW.setProperty(playurl+"positionurl", positionurl)
        WINDOW.setProperty(playurl+"deleteurl", "")
        if result.get("Type")=="Episode" and self.settings.getSetting("offerDelete")=="true":
          WINDOW.setProperty(playurl+"deleteurl", deleteurl)
        
        if result.get("Type")=="Episode":
            WINDOW.setProperty(playurl+"refresh_id", result.get("SeriesId"))
        else:
            WINDOW.setProperty(playurl+"refresh_id", id)
            
        WINDOW.setProperty(playurl+"runtimeticks", str(result.get("RunTimeTicks")))
        WINDOW.setProperty(playurl+"type", result.get("Type"))
        WINDOW.setProperty(playurl+"item_id", id)
        
        if PlayUtils().isDirectPlay(result) == True:
          if self.settings.getSetting('playFromStream') == "true":
            playMethod = "DirectStream"
          else:
            playMethod = "DirectPlay"
        else:
          playMethod = "Transcode"
        if IsStrmPlaceholder == True:
            playMethod = "DirectStream"
          
        WINDOW.setProperty(playurl+"playmethod", playMethod)
            
        mediaSources = result.get("MediaSources")
        if(mediaSources != None):
          if mediaSources[0].get('DefaultAudioStreamIndex') != None:
            WINDOW.setProperty(playurl+"AudioStreamIndex", str(mediaSources[0].get('DefaultAudioStreamIndex')))  
          if mediaSources[0].get('DefaultSubtitleStreamIndex') != None:
            WINDOW.setProperty(playurl+"SubtitleStreamIndex", str(mediaSources[0].get('DefaultSubtitleStreamIndex')))
        
        playlist.add(playurl, listItem)
        
        if self.settings.getSetting("autoPlaySeason")=="true" and result.get("Type")=="Episode":
            # add remaining unplayed episodes if applicable
            seasonId = result.get("SeasonId")
            jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items?ParentId=" + seasonId + "&ImageTypeLimit=1&StartIndex=1&SortBy=SortName&SortOrder=Ascending&Filters=IsUnPlayed&IncludeItemTypes=Episode&IsVirtualUnaired=false&Recursive=true&IsMissing=False&format=json", suppress=False, popup=1 )     
            if(jsonData == ""):
                return
            result = json.loads(jsonData)
            if result.get("Items") != None:
              for item in result.get("Items"):
                id = item.get("Id")
                jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json&ImageTypeLimit=1", suppress=False, popup=1 )
                if(jsonData == ""):
                    return
                result = json.loads(jsonData)
                playurl = PlayUtils().getPlayUrl(server, id, result)
                self.logMsg("Play URL: " + playurl)    
                thumbPath = self.downloadUtils.getArtwork(item, "Primary")
                listItem = xbmcgui.ListItem(path=playurl, iconImage=thumbPath, thumbnailImage=thumbPath)
                self.setListItemProps(server, id, listItem, result)
        
                watchedurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id
                positionurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayingItems/' + id
                deleteurl = 'http://' + server + '/mediabrowser/Items/' + id
                
                # set the current playing info
                WINDOW = xbmcgui.Window( 10000 )
                WINDOW.setProperty(playurl+"watchedurl", watchedurl)
                WINDOW.setProperty(playurl+"positionurl", positionurl)
                WINDOW.setProperty(playurl+"deleteurl", "")
             
                WINDOW.setProperty(playurl+"runtimeticks", str(result.get("RunTimeTicks")))
                WINDOW.setProperty(playurl+"type", result.get("Type"))
                WINDOW.setProperty(playurl+"item_id", id)
                WINDOW.setProperty(playurl+"refresh_id", result.get("SeriesId"))
                
                if PlayUtils().isDirectPlay(result) == True:
                  if self.settings.getSetting('playFromStream') == "true":
                    playMethod = "DirectStream"
                  else:
                    playMethod = "DirectPlay"
                else:
                  playMethod = "Transcode"
                WINDOW.setProperty(playurl+"playmethod", playMethod)
                
                mediaSources = result.get("MediaSources")
                if(mediaSources != None):
                  if mediaSources[0].get('DefaultAudioStreamIndex') != None:
                    WINDOW.setProperty(playurl+"AudioStreamIndex", str(mediaSources[0].get('DefaultAudioStreamIndex')))  
                  if mediaSources[0].get('DefaultSubtitleStreamIndex') != None:
                    WINDOW.setProperty(playurl+"SubtitleStreamIndex", str(mediaSources[0].get('DefaultSubtitleStreamIndex')))
                
                playlist.add(playurl, listItem)
        
        xbmc.Player().play(playlist)
        
        #If resuming then wait for playback to start and then
        #seek to position
        if resume_result == 0:
            self.seekToPosition(seekTime)

    def seekToPosition(self, seekTo):
    
        #Set a loop to wait for positive confirmation of playback
        count = 0
        while not xbmc.Player().isPlaying():
            self.logMsg( "Not playing yet...sleep for 1 sec")
            count = count + 1
            if count >= 10:
                return
            else:
                time.sleep(1)
            
        #Jump to resume point
        jumpBackSec = int(self.settings.getSetting("resumeJumpBack"))
        seekToTime = seekTo - jumpBackSec
        count = 0
        while xbmc.Player().getTime() < (seekToTime - 5) and count < 11: # only try 10 times
            count = count + 1
            xbmc.Player().pause
            xbmc.sleep(100)
            xbmc.Player().seekTime(seekToTime)
            xbmc.sleep(100)
            xbmc.Player().play()
    
    def PLAYAllItems(self, items, startPositionTicks):
        self.logMsg("== ENTER: PLAYAllItems ==")
        self.logMsg("Items : " + str(items))
        userid = self.downloadUtils.getUserId()
        server = self.downloadUtils.getServer()
        
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()        
        started = False
        
        for itemID in items:
        
            self.logMsg("Adding Item to Playlist : " + itemID)
            item_url = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + itemID + "?format=json"
            jsonData = self.downloadUtils.downloadUrl(item_url, suppress=False, popup=1 )
            
            item_data = json.loads(jsonData)
            added = self.addPlaylistItem(playlist, item_data, server, userid)
            if(added and started == False):
                started = True
                self.logMsg("Starting Playback Pre")
                xbmc.Player().play(playlist)
        
        if(started == False):
            self.logMsg("Starting Playback Post")
            xbmc.Player().play(playlist)
        
        #seek to position
        seekTime = 0
        if(startPositionTicks != None):
            seekTime = (startPositionTicks / 1000) / 10000
            
        if seekTime > 0:
            self.seekToPosition(seekTime)
    
    def AddToPlaylist(self, itemIds):
        self.logMsg("== ENTER: PLAYAllItems ==")
        userid = self.downloadUtils.getUserId()
        server = self.downloadUtils.getServer()
        
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)     
        
        for itemID in itemIds:
        
            self.logMsg("Adding Item to Playlist : " + itemID)
            item_url = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + itemID + "?format=json"
            jsonData = self.downloadUtils.downloadUrl(item_url, suppress=False, popup=1 )
            
            item_data = json.loads(jsonData)
            self.addPlaylistItem(playlist, item_data, server, userid)
    
        return playlist
    
    def PLAYAllFromHere(self, startId):
        WINDOW = xbmcgui.Window( 10000 )
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        jsonData = self.downloadUtils.downloadUrl(WINDOW.getProperty("currenturl"))
        result = json.loads(jsonData)
        result = result.get("Items")
        found = False
        
        userid = self.downloadUtils.getUserId()
        server = self.downloadUtils.getServer()
        
        for item in result:
        
            if str(item.get('Id')) == startId:
                found = True
                
            if found:
                if(item.get('RecursiveItemCount') != 0):
                    self.addPlaylistItem(playlist, item, server, userid)
                    
        xbmc.Player().play(playlist)

            
    def PLAYPlaylist(self, url, handle):
        self.logMsg("== ENTER: PLAY Playlist ==")
        url = urllib.unquote(url)
        
        urlParts = url.split(',;')
        self.logMsg("PLAY Playlist ACTION URL PARTS : " + str(urlParts))
        server = urlParts[0]
        id = urlParts[1]
        userid = self.downloadUtils.getUserId()

        jsonData = self.downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Playlists/" + id + "/Items/?fields=path&format=json", suppress=False, popup=1 )     
        self.logMsg("Playlist jsonData: " + jsonData)
        result = json.loads(jsonData)
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
            
        for item in result.get("Items"):
        
            id = item.get("Id")
            item_url = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json"
            jsonData = self.downloadUtils.downloadUrl(item_url, suppress=False, popup=1 )
            item_data = json.loads(jsonData)
            self.addPlaylistItem(playlist, item_data, server, userid)
            
        xbmc.Player().play(playlist)
    
    def addPlaylistItem(self, playlist, item, server, userid):

        id = item.get("Id")
        
        playurl = PlayUtils().getPlayUrl(server, id, item)
        self.logMsg("Play URL: " + playurl)    
        thumbPath = self.downloadUtils.getArtwork(item, "Primary")
        listItem = xbmcgui.ListItem(path=playurl, iconImage=thumbPath, thumbnailImage=thumbPath)
        self.setListItemProps(server, id, listItem, item)

        # Can not play virtual items
        if (item.get("LocationType") == "Virtual") or (item.get("IsPlaceHolder") == True):
        
            xbmcgui.Dialog().ok(self.language(30128), self.language(30129))
            return False
            
        else:
        
            watchedurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id
            positionurl = 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayingItems/' + id
            deleteurl = 'http://' + server + '/mediabrowser/Items/' + id

            # set the current playing info
            WINDOW = xbmcgui.Window( 10000 )
            WINDOW.setProperty(playurl + "watchedurl", watchedurl)
            WINDOW.setProperty(playurl + "positionurl", positionurl)
            WINDOW.setProperty(playurl + "deleteurl", "")
            
            if item.get("Type") == "Episode" and self.settings.getSetting("offerDelete")=="true":
               WINDOW.setProperty(playurl + "deleteurl", deleteurl)
        
            WINDOW.setProperty(playurl + "runtimeticks", str(item.get("RunTimeTicks")))
            WINDOW.setProperty(playurl+"type", item.get("Type"))
            WINDOW.setProperty(playurl + "item_id", id)
            
            if (item.get("Type") == "Episode"):
                WINDOW.setProperty(playurl + "refresh_id", item.get("SeriesId"))
            else:
                WINDOW.setProperty(playurl + "refresh_id", id)            
            
            self.logMsg( "PlayList Item Url : " + str(playurl))
            
            playlist.add(playurl, listItem)
            
            return True
    
    def setArt(self, list,name,path):
        if name=='thumb' or name=='fanart_image' or name=='small_poster' or name=='tiny_poster'  or name == "medium_landscape" or name=='medium_poster' or name=='small_fanartimage' or name=='medium_fanartimage' or name=='fanart_noindicators':
            list.setProperty(name, path)
        else:#elif xbmcVersionNum >= 13:
            list.setArt({name:path})
        return list
    
    def setListItemProps(self, server, id, listItem, result):
        # set up item and item info
        userid = self.downloadUtils.getUserId()
        thumbID = id
        eppNum = -1
        seasonNum = -1
        tvshowTitle = ""
        
        if(result.get("Type") == "Episode"):
            thumbID = result.get("SeriesId")
            seasonNum = result.get("ParentIndexNumber")
            eppNum = result.get("IndexNumber")
            tvshowTitle = result.get("SeriesName")
            
        self.setArt(listItem,'poster', self.downloadUtils.getArtwork(result, "Primary"))
        self.setArt(listItem,'tvshow.poster', self.downloadUtils.getArtwork(result, "SeriesPrimary"))
        self.setArt(listItem,'clearart', self.downloadUtils.getArtwork(result, "Art"))
        self.setArt(listItem,'tvshow.clearart', self.downloadUtils.getArtwork(result, "Art"))    
        self.setArt(listItem,'clearlogo', self.downloadUtils.getArtwork(result, "Logo"))
        self.setArt(listItem,'tvshow.clearlogo', self.downloadUtils.getArtwork(result, "Logo"))    
        self.setArt(listItem,'discart', self.downloadUtils.getArtwork(result, "Disc"))  
        self.setArt(listItem,'fanart_image', self.downloadUtils.getArtwork(result, "Backdrop"))
        self.setArt(listItem,'landscape', self.downloadUtils.getArtwork(result, "Thumb"))   
        
        listItem.setProperty('IsPlayable', 'true')
        listItem.setProperty('IsFolder', 'false')
        
        # Process Studios
        studio = API().getStudio(result) 
        listItem.setInfo('video', {'studio' : studio})    

        # play info
        playinformation = ''
        if PlayUtils().isDirectPlay(result) == True:
            if self.settings.getSetting('playFromStream') == "true":
                playinformation = self.language(30164)
            else:
                playinformation = self.language(30165)
        else:
            playinformation = self.language(30166)
            
        details = {
                 'title'        : result.get("Name", "Missing Name") + ' - ' + playinformation,
                 'plot'         : result.get("Overview")
                 }
                 
        if(eppNum > -1):
            details["episode"] = str(eppNum)
            
        if(seasonNum > -1):
            details["season"] = str(seasonNum)  

        if tvshowTitle != None:
            details["TVShowTitle"] = tvshowTitle	
        
        listItem.setInfo( "Video", infoLabels=details )

        people = API().getPeople(result)

        # Process Genres
        genre = API().getGenre(result)
        
        listItem.setInfo('video', {'director' : people.get('Director')})
        listItem.setInfo('video', {'writer' : people.get('Writer')})
        listItem.setInfo('video', {'mpaa': self.db.get(thumbID + ".OfficialRating")})
        listItem.setInfo('video', {'genre': genre})
