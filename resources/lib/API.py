# API.py
# This class helps translate more complex cases from the MediaBrowser API to the XBMC API

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


logLevel = 1
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')

CP_ADD_URL = 'XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?title=%s)'

__cwd__ = __settings__.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath( os.path.join( __cwd__) )
__language__     = __addon__.getLocalizedString

class API():
    
    def getPeople(self, item):
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
        return director, writer, cast

    def getDuration(self, item):
        resumeTime = 0
        userData = item.get("UserData")
        PlaybackPositionTicks = '100'
        if userData.get("PlaybackPositionTicks") != None:
            PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            resumeTime = reasonableTicks / 10000    

        try:
            tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
        except TypeError:
            try:
                tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
            except TypeError:
                tempDuration = "0"
        cappedPercentage = None
        if (resumeTime != "" and int(resumeTime) > 0):
            duration = float(tempDuration)
            if(duration > 0):
                resume = float(resumeTime) / 60.0
                percentage = int((resume / duration) * 100.0)
                cappedPercentage = percentage - (percentage % 10)
                if(cappedPercentage == 0):
                    cappedPercentage = 10
                if(cappedPercentage == 100):
                    cappedPercentage = 90
        return tempDuration, str(cappedPercentage)

    def getStudio(self, item):
        # Process Studio
        studio = "" 
        if item.get("SeriesStudio") != None and item.get("SeriesStudio") != '':
            studio = item.get("SeriesStudio")
        if studio == "":        
            studios = item.get("Studios")
            if(studios != None):
                for studio_string in studios:
                    if studio=="": #Just take the first one
                        temp=studio_string.get("Name")
                        studio=temp.encode('utf-8')
        return studio

    def getMediaStreams(self, item, mediaSources=False):    
        # Process MediaStreams
        channels = ''
        videocodec = ''
        audiocodec = ''
        height = ''
        width = ''
        aspectratio = '1:1'
        aspectfloat = 1.85

        if mediaSources == True:
            mediaSources = item.get("MediaSources")
            if(mediaSources != None):
                MediaStreams = mediaSources[0].get("MediaStreams")
            else:
                MediaStreams = None
        else:
            MediaStreams = item.get("MediaStreams")
        if(MediaStreams != None):
            #mediaStreams = MediaStreams[0].get("MediaStreams")
            if(MediaStreams != None):
                for mediaStream in MediaStreams:
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
        return {'channels'      : str(channels), 
                'videocodec'    : videocodec, 
                'audiocodec'    : audiocodec, 
                'height'        : height,
                'width'         : width,
                'aspectratio'   : str(aspectfloat)
                }