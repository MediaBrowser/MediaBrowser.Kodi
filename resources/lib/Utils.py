#################################################################################################
# utils class
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
from DownloadUtils import DownloadUtils
import urllib
import sys

#define our global download utils
downloadUtils = DownloadUtils()

###########################################################################
class PlayUtils():

    def getPlayUrl(self, server, id, result):
    
      addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
      # if the path is local and depending on the video quality play we can direct play it do so-
      xbmc.log("XBMB3C getPlayUrl")
      if self.isDirectPlay(result) == True:
          xbmc.log("XBMB3C getPlayUrl -> Direct Play")
          playurl = result.get("Path")
          if playurl != None:
            #We have a path to play so play it
            USER_AGENT = 'QuickTime/7.7.4'

            # If the file it is not a media stub
            if (result.get("IsPlaceHolder") != True):
              if (result.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
              elif (result.get("VideoType") == "BluRay"):
                playurl = playurl + "/BDMV/index.bdmv"
            if addonSettings.getSetting('smbusername') == '':
              playurl = playurl.replace("\\\\", "smb://")
            else:
              playurl = playurl.replace("\\\\", "smb://" + addonSettings.getSetting('smbusername') + ':' + addonSettings.getSetting('smbpassword') + '@')
            playurl = playurl.replace("\\", "/")
        
            if ("apple.com" in playurl):
              playurl += '?|User-Agent=%s' % USER_AGENT
            if addonSettings.getSetting('playFromStream') == "true":
              playurl = 'http://' + server + '/mediabrowser/Videos/' + id + '/stream?static=true' 
  
            
     # elif self.isNetworkQualitySufficient(result) == True:
      #   xbmc.log("XBMB3C getPlayUrl -> Stream")
          #No direct path but sufficient network so static stream   
       #  if result.get("Type") == "Audio":
        #    playurl = 'http://' + server + '/mediabrowser/Audio/' + id + '/stream?static=true&mediaSourceId=' + id
         #else:
          #  playurl = 'http://' + server + '/mediabrowser/Videos/' + id + '/stream?static=true&mediaSourceId=' + id   
      else:
          #No path or has a path but not sufficient network so transcode
          xbmc.log("XBMB3C getPlayUrl -> Transcode")
          if result.get("Type") == "Audio":
            playurl = 'http://' + server + '/mediabrowser/Audio/' + id + '/stream.mp3'
          else:
            txt_mac = downloadUtils.getMachineId()
            playurl = 'http://' + server + '/mediabrowser/Videos/' + id + '/master.m3u8?mediaSourceId=' + id
            playurl = playurl + '&videoCodec=h264'
            playurl = playurl + '&AudioCodec=aac,ac3'
            playurl = playurl + '&deviceId=' + txt_mac
            playurl = playurl + '&VideoBitrate=' + str(int(self.getVideoBitRate()) * 1000)
            mediaSources = result.get("MediaSources")
            if(mediaSources != None):
              if mediaSources[0].get('DefaultAudioStreamIndex') != None:
                 playurl = playurl + "&AudioStreamIndex=" +str(mediaSources[0].get('DefaultAudioStreamIndex'))
              if mediaSources[0].get('DefaultSubtitleStreamIndex') != None:
                 playurl = playurl + "&SubtitleStreamIndex=" + str(mediaSources[0].get('DefaultAudioStreamIndex'))
      return playurl.encode('utf-8')

    # Works out if we are direct playing or not
    def isDirectPlay(self, result):
        if result.get("LocationType") == "FileSystem" and self.isNetworkQualitySufficient(result) == True and self.isLocalPath(result) == False:
            return True
        else:
            return False
        

    # Works out if the network quality can play directly or if transcoding is needed
    def isNetworkQualitySufficient(self, result):
        settingsVideoBitRate = self.getVideoBitRate()
        settingsVideoBitRate = int(settingsVideoBitRate) * 1000
        mediaSources = result.get("MediaSources")
        if(mediaSources != None):
          if mediaSources[0].get('Bitrate') != None:
             if settingsVideoBitRate < int(mediaSources[0].get('Bitrate')):
               xbmc.log("XBMB3C isNetworkQualitySufficient -> FALSE bit rate - settingsVideoBitRate: " + str(settingsVideoBitRate) + " mediasource bitrate: " + str(mediaSources[0].get('Bitrate')))   
               return False
             else:
               xbmc.log("XBMB3C isNetworkQualitySufficient -> TRUE bit rate")   
               return True
           
        # Any thing else is ok
        xbmc.log("XBMB3C isNetworkQualitySufficient -> TRUE default")
        return True
      
       
    # get the addon video quality
    def getVideoBitRate(self):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        videoQuality = addonSettings.getSetting('videoBitRate')  
        if (videoQuality == "0"):
            return '664'
        elif (videoQuality == "1"):
           return '996'
        elif (videoQuality == "2"):
           return '1320'
        elif (videoQuality == "3"):
           return '2000'
        elif (videoQuality == "4"):
           return '3200'
        elif (videoQuality == "5"):
           return '4700'
        elif (videoQuality == "6"):
           return '6200'
        elif (videoQuality == "7"):
           return '7700'
        elif (videoQuality == "8"):
           return '9200'
        elif (videoQuality == "9"):
           return '10700'
        elif (videoQuality == "10"):
           return '12200'
        elif (videoQuality == "11"):
           return '13700'
        elif (videoQuality == "12"):
           return '15200'
        elif (videoQuality == "13"):
           return '16700'
        elif (videoQuality == "14"):
           return '18200'
        elif (videoQuality == "15"):
           return '20000'
        elif (videoQuality == "16"):
           return '40000'
        elif (videoQuality == "17"):
           return '100000'
        elif (videoQuality == "18"):
           return '1000000'
       
    # Works out if the network quality can play directly or if transcoding is needed
    def isLocalPath(self, result):
        playurl = result.get("Path")
        if playurl != None:
            #We have a path to play so play it
            if ":\\" in playurl:
              return True
            else:
              return False
           
        # default to not local 
        return False
      
