def pluginTranscodeMonitor( sessionID, server ):
    printDebug("== ENTER: pluginTranscodeMonitor ==", False)

    #Logic may appear backward, but this does allow for a failed start to be detected
    #First while loop waiting for start

    count=0
    while not xbmc.Player().isPlaying():
        printDebug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 40:
            #Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        else:
            time.sleep(2)

    while xbmc.Player().isPlaying():
        printDebug("Waiting for playback to finish")
        time.sleep(4)

    printDebug("Playback Stopped")
    printDebug("Stopping PMS transcode job with session: " + sessionID)
    stopURL='http://'+server+'/video/:/transcode/segmented/stop?session='+sessionID

    html=getURL(stopURL)

    return


    def selectMedia( data, server ):
    printDebug("== ENTER: selectMedia ==", False)
    #if we have two or more files for the same movie, then present a screen
    result=0
    dvdplayback=False

    count=data['partsCount']
    options=data['parts']
    details=data['details']
    
    if count > 1:

        dialogOptions=[]
        dvdIndex=[]
        indexCount=0
        for items in options:

            if items[1]:
                name=items[1].split('/')[-1]
                #name="%s %s %sMbps" % (items[1].split('/')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
            else:
                name="%s %s %sMbps" % (items[0].split('.')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
                
            if g_forcedvd == "true":
                if '.ifo' in name.lower():
                    printDebug( "Found IFO DVD file in " + name )
                    name="DVD Image"
                    dvdIndex.append(indexCount)

            dialogOptions.append(name)
            indexCount+=1

        printDebug("Create selection dialog box - we have a decision to make!")
        startTime = xbmcgui.Dialog()
        result = startTime.select('Select media to play',dialogOptions)
        if result == -1:
            return None

        if result in dvdIndex:
            printDebug( "DVD Media selected")
            dvdplayback=True

    else:
        if g_forcedvd == "true":
            if '.ifo' in options[result]:
                dvdplayback=True

    newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server,dvdplayback)

    printDebug("We have selected media at " + newurl)
    return newurl

    def setAudioSubtitles( stream ):
    '''
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    '''

    printDebug("== ENTER: setAudioSubtitles ==", False)

    #If we have decided not to collect any sub data then do not set subs
    if stream['contents'] == "type":
        printDebug ("No audio or subtitle streams to process.")

        #If we have decided to force off all subs, then turn them off now and return
        if g_streamControl == _SUB_AUDIO_NEVER_SHOW :
            xbmc.Player().showSubtitles(False)
            printDebug ("All subs disabled")

        return True

    #Set the AUDIO component
    if ( g_streamControl == _SUB_AUDIO_PLEX_CONTROL ):
        printDebug("Attempting to set Audio Stream")

        audio = stream['audio']
        
        if stream['audioCount'] == 1:
            printDebug ("Only one audio stream present - will leave as default")

        elif audio:
            printDebug ("Attempting to use selected language setting: %s" % audio.get('language',audio.get('languageCode','Unknown')).encode('utf8'))
            printDebug ("Found preferred language at index " + str(stream['audioOffset']))
            try:
                xbmc.Player().setAudioStream(stream['audioOffset'])
                printDebug ("Audio set")
            except:
                printDebug ("Error setting audio, will use embedded default stream")

    #Set the SUBTITLE component
    if g_streamControl == _SUB_AUDIO_PLEX_CONTROL:
        printDebug("Attempting to set preferred subtitle Stream", True)
        subtitle=stream['subtitle']
        if subtitle:
            printDebug ("Found preferred subtitle stream" )
            try:
                xbmc.Player().showSubtitles(False)
                if subtitle.get('key'):
                    xbmc.Player().setSubtitles(subtitle['key']+getAuthDetails({'token':_PARAM_TOKEN},prefix="?"))                
                    xbmc.Player().showSubtitles(False)
                else:
                    printDebug ("Enabling embedded subtitles at index %s" % stream['subOffset'])
                    xbmc.Player().setSubtitleStream(int(stream['subOffset']))
                    
                return True
            except:
                printDebug ("Error setting subtitle")
                
        else:
            printDebug ("No preferred subtitles to set")

    xbmc.Player().showSubtitles(False)
    return False



def getAudioSubtitlesMedia( server, id, full=False ):
    '''
        Cycle through the Parts sections to find all "selected" audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    '''
    printDebug("== ENTER: getAudioSubtitlesMedia ==", False)
    printDebug("Gather media stream info" )

    #get metadata for audio and subtitle
    suburl="http://"+server+"/library/metadata/"+id

    html=getURL(suburl)
    tree=etree.fromstring(html)

    parts=[]
    partsCount=0
    subtitle={}
    subCount=0
    audio={}
    audioCount=0
    media={}
    subOffset=-1
    audioOffset=-1
    selectedSubOffset=-1
    selectedAudioOffset=-1
    full_data={}
    contents="type"

    timings = tree.find('Video')
    
    media['viewOffset']=timings.get('viewOffset',0)
    media['duration']=timings.get('duration',12*60*60)

    if full:
        full_data={ 'plot'      : timings.get('summary','').encode('utf-8') ,
                    'title'     : timings.get('title','Unknown').encode('utf-8') ,
                    'sorttitle' : timings.get('titleSort', timings.get('title','Unknown')).encode('utf-8') ,
                    'rating'    : float(timings.get('rating',0)) ,
                    'studio'    : timings.get('studio','').encode('utf-8') ,
                    'mpaa'      : "Rated " + timings.get('contentRating', 'unknown') ,
                    'year'      : int(timings.get('year',0)) ,
                    'tagline'   : timings.get('tagline','') ,
                    'thumbnailImage': getThumb(timings,server) }
                    
        if timings.get('type') == "episode":
            full_data['episode']     = int(timings.get('index',0)) 
            full_data['aired']       = timings.get('originallyAvailableAt','') 
            full_data['tvshowtitle'] = timings.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') 
            full_data['season']      = int(timings.get('parentIndex',tree.get('parentIndex',0))) 


    details = timings.findall('Media')
        
    media_details_list=[]
    for media_details in details:
                
        resolution=""        
        try:       
            if media_details.get('videoResolution') == "sd":
                resolution="SD"
            elif int(media_details.get('videoResolution',0)) >= 1080:
                resolution="HD 1080"
            elif int(media_details.get('videoResolution',0)) >= 720:
                resolution="HD 720"
            elif int(media_details.get('videoResolution',0)) < 720:
                resolution="SD"
        except:
            pass
        
        media_details_temp = { 'bitrate'          : round(float(media_details.get('bitrate',0))/1000,1) ,
                               'videoResolution'  : resolution ,
                               'container'        : media_details.get('container','unknown') }
                                                  
        options = media_details.findall('Part')
        
        #Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits=stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                partsCount += 1
            except: pass

    #if we are deciding internally or forcing an external subs file, then collect the data
    if g_streamControl == _SUB_AUDIO_PLEX_CONTROL:

        contents="all"
        tags=tree.getiterator('Stream')

        for bits in tags:
            stream=dict(bits.items())
            
            #Audio Streams
            if stream['streamType'] == '2':
                audioCount += 1
                audioOffset += 1
                if stream.get('selected') == "1":
                    printDebug("Found preferred audio id: " + str(stream['id']) )
                    audio=stream
                    selectedAudioOffset=audioOffset
            
            #Subtitle Streams
            elif stream['streamType'] == '3':
            
                if subOffset == -1:
                    subOffset = int(stream.get('index',-1))
                elif stream.get('index',-1) > 0 and stream.get('index',-1) < subOffset:
                    subOffset = int(stream.get('index',-1))
                    
                if stream.get('selected') == "1":
                    printDebug( "Found preferred subtitles id : " + str(stream['id']))
                    subCount += 1
                    subtitle=stream
                    if stream.get('key'):
                        subtitle['key'] = 'http://'+server+stream['key']
                    else:
                        selectedSubOffset=int( stream.get('index') ) - subOffset
                    
    else:
            printDebug( "Stream selection is set OFF")

    streamData={'contents'   : contents ,                #What type of data we are holding
                'audio'      : audio ,                   #Audio data held in a dict
                'audioCount' : audioCount ,              #Number of audio streams
                'subtitle'   : subtitle ,                #Subtitle data (embedded) held as a dict
                'subCount'   : subCount ,                #Number of subtitle streams
                'parts'      : parts ,                   #The differet media locations
                'partsCount' : partsCount ,              #Number of media locations
                'media'      : media ,                   #Resume/duration data for media
                'details'    : media_details_list ,      #Bitrate, resolution and container for each part
                'subOffset'  : selectedSubOffset ,       #Stream index for selected subs
                'audioOffset': selectedAudioOffset ,     #STream index for select audio
                'full_data'  : full_data }               #Full metadata extract if requested

    printDebug ( str(streamData) )
    return streamData
def getNewMyPlexToken( suppress=True , title="Error" ):
    '''
        Get a new myplex token from myplex API
        @input: nothing
        @return: myplex token
    '''

    printDebug("== ENTER: getNewMyPlexToken ==", False)

    printDebug("Getting New token")
    myplex_username = __settings__.getSetting('myplex_user')
    myplex_password = __settings__.getSetting('myplex_pass')

    if ( myplex_username or myplex_password ) == "":
        printDebug("No myplex details in config..")
        return ""

    base64string = base64.encodestring('%s:%s' % (myplex_username, myplex_password)).replace('\n', '')
    txdata=""
    token=False

    myplex_headers={'X-Plex-Platform': "XBMC",
                    'X-Plex-Platform-Version': "12.00/Frodo",
                    'X-Plex-Provides': "player",
                    'X-Plex-Product': "PleXBMC",
                    'X-Plex-Version': PLEXBMC_VERSION,
                    'X-Plex-Device': PLEXBMC_PLATFORM,
                    'X-Plex-Client-Identifier': "PleXBMC",
                    'Authorization': "Basic %s" % base64string }

    try:
        conn = httplib.HTTPSConnection(MYPLEX_SERVER)
        conn.request("POST", "/users/sign_in.xml", txdata, myplex_headers)
        data = conn.getresponse()

        if int(data.status) == 201:
            link=data.read()
            printDebug("====== XML returned =======")

            try:
                token=etree.fromstring(link).findtext('authentication-token')
                __settings__.setSetting('myplex_token',myplex_username+"|"+token)
            except:
                printDebug(link)

            printDebug("====== XML finished ======")
        else:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title,error)
            print error
            return ""
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return ""
    except socket.error, msg :
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return ""

    return token
def getMyPlexToken( renew=False ):
    '''
        Get the myplex token.  If the user ID stored with the token
        does not match the current userid, then get new token.  This stops old token
        being used if plex ID is changed. If token is unavailable, then get a new one
        @input: whether to get new token
        @return: myplex token
    '''
    printDebug("== ENTER: getMyPlexToken ==", False)

    try:
        user,token=(__settings__.getSetting('myplex_token')).split('|')
    except:
        token=""

    if ( token == "" ) or (renew) or (user != __settings__.getSetting('myplex_user')):
        token = getNewMyPlexToken()

    printDebug("Using token: " + str(token) + "[Renew: " + str(renew) + "]")
    return token
    
def getMyPlexURL( url_path, renew=False, suppress=True ):
    '''
        Connect to the my.plexapp.com service and get an XML pages
        A seperate function is required as interfacing into myplex
        is slightly different than getting a standard URL
        @input: url to get, whether we need a new token, whether to display on screen err
        @return: an xml page as string or false
    '''
    printDebug("== ENTER: getMyPlexURL ==", False)
    printDebug("url = "+MYPLEX_SERVER+url_path)

    try:
        conn = httplib.HTTPSConnection(MYPLEX_SERVER)#, timeout=5)
        conn.request("GET", url_path+"?X-Plex-Token="+getMyPlexToken(renew))
        data = conn.getresponse()
        if ( int(data.status) == 401 )  and not ( renew ):
            try: conn.close()
            except: pass
            return getMyPlexURL(url_path,True)

        if int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            try: conn.close()
            except: pass
            return False
        elif int(data.status) == 301 and type == "HEAD":
            try: conn.close()
            except: pass
            return str(data.status)+"@"+data.getheader('Location')
        else:
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")
    except socket.gaierror :
        error = 'Unable to lookup host: ' + MYPLEX_SERVER + "\nCheck host name is correct"
        if suppress is False:
            xbmcgui.Dialog().ok("Error",error)
        print error
        return False
    except socket.error, msg :
        error="Unable to connect to " + MYPLEX_SERVER +"\nReason: " + str(msg)
        if suppress is False:
            xbmcgui.Dialog().ok("Error",error)
        print error
        return False
    else:
        try: conn.close()
        except: pass

    if link:
        return link
    else:
        return False

def getAuthDetails( details, url_format=True, prefix="&" ):
    '''
        Takes the token and creates the required arguments to allow
        authentication.  This is really just a formatting tools
        @input: token as dict, style of output [opt] and prefix style [opt]
        @return: header string or header dict
    '''
    token = details.get('token', None)

    if url_format:
        if token:
            return prefix+"X-Plex-Token="+str(token)
        else:
            return "happy"
    else:
        if token:
            return {'X-Plex-Token' : token }
        else:
            return {}

def transcode( id, url, identifier=None ):
    printDebug("== ENTER: transcode ==", False)

    server=getServerFromURL(url)

    #Check for myplex user, which we need to alter to a master server
    if 'plexapp.com' in url:
        server=getMasterServer()

    printDebug("Using preferred transcoding server: " + server)
    printDebug ("incoming URL is: %s" % url)

    transcode_request="/video/:/transcode/segmented/start.m3u8"
    transcode_settings={ '3g' : 0 ,
                         'offset' : 0 ,
                         'quality' : g_quality ,
                         'session' : g_sessionID ,
                         'identifier' : identifier ,
                         'httpCookie' : "" ,
                         'userAgent' : "" ,
                         'ratingKey' : id ,
                         'subtitleSize' : __settings__.getSetting('subSize').split('.')[0] ,
                         'audioBoost' : __settings__.getSetting('audioSize').split('.')[0] ,
                         'key' : "" }

    if identifier:
        transcode_target=url.split('url=')[1]
        transcode_settings['webkit']=1
    else:
        transcode_settings['identifier']="com.plexapp.plugins.library"
        transcode_settings['key']=urllib.quote_plus("http://%s/library/metadata/%s" % (server, id))
        transcode_target=urllib.quote_plus("http://127.0.0.1:32400"+"/"+"/".join(url.split('/')[3:]))
        printDebug ("filestream URL is: %s" % transcode_target )

    transcode_request="%s?url=%s" % (transcode_request, transcode_target)

    for argument, value in transcode_settings.items():
                transcode_request="%s&%s=%s" % ( transcode_request, argument, value )

    printDebug("new transcode request is: %s" % transcode_request )

    now=str(int(round(time.time(),0)))

    msg = transcode_request+"@"+now
    printDebug("Message to hash is " + msg)

    #These are the DEV API keys - may need to change them on release
    publicKey="KQMIY6GATPC63AIMC4R2"
    privateKey = base64.decodestring("k3U6GLkZOoNIoSgjDshPErvqMIFdE0xMTx8kgsrhnC0=")

    import hmac
    import hashlib
    hash=hmac.new(privateKey,msg,digestmod=hashlib.sha256)

    printDebug("HMAC after hash is " + hash.hexdigest())

    #Encode the binary hash in base64 for transmission
    token=base64.b64encode(hash.digest())

    #Send as part of URL to avoid the case sensitive header issue.
    fullURL="http://"+server+transcode_request+"&X-Plex-Access-Key="+publicKey+"&X-Plex-Access-Time="+str(now)+"&X-Plex-Access-Code="+urllib.quote_plus(token)+"&"+capability

    printDebug("Transcoded media location URL " + fullURL)

    return fullURL

    def getMyPlexServers( ):
    '''
        Connect to the myplex service and get a list of all known
        servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''

    printDebug("== ENTER: getMyPlexServers ==", False)

    tempServers=[]
    url_path="/pms/servers"

    html = getMyPlexURL(url_path)

    if html is False:
        return {}

    server=etree.fromstring(html).findall('Server')
    count=0
    for servers in server:
        data=dict(servers.items())

        if data.get('owned',None) == "1":
            if count == 0:
                master=1
                count=-1
            accessToken=getMyPlexToken()
        else:
            master='0'
            accessToken=data.get('accessToken',None)

        tempServers.append({'serverName': data['name'].encode('utf-8') ,
                            'server'    : data['address'] ,
                            'port'      : data['port'] ,
                            'discovery' : 'myplex' ,
                            'token'     : accessToken ,
                            'uuid'      : data['machineIdentifier'] ,
                            'owned'     : data.get('owned',0) ,
                            'master'    : master })

    return tempServers
    
def deduplicateServers( server_list ):
    '''
      Return list of all media sections configured
      within PleXBMC
      @input: None
      @Return: unique list of media servers
    '''
    printDebug("== ENTER: deduplicateServers ==", False)

    if len(server_list) <= 1:
        return server_list

    temp_list=server_list.values()
    oneCount=0
    for onedevice in temp_list:

        twoCount=0
        for twodevice in temp_list:

            #printDebug( "["+str(oneCount)+":"+str(twoCount)+"] Checking " + onedevice['uuid'] + " and " + twodevice['uuid'])

            if oneCount == twoCount:
                #printDebug( "skip" )
                twoCount+=1
                continue

            if onedevice['uuid'] == twodevice['uuid']:
                #printDebug ( "match" )
                if onedevice['discovery'] == "auto" or onedevice['discovery'] == "local":
                    temp_list.pop(twoCount)
                else:
                    temp_list.pop(oneCount)
            #else:
            #    printDebug( "no match" )

            twoCount+=1

        oneCount+=1


    count=0
    unique_list={}
    for i in temp_list:
        unique_list[count] = i
        count = count + 1

    printDebug ("Unique server List: " + str(unique_list))

    return unique_list

def getMyplexSections ( ):
    printDebug("== ENTER: getMyplexSections ==", False)

    #html=getMyPlexURL('/pms/system/library/sections')
    html=getMyPlexURL('/pms/system/library/sections')

    if html is False:
        return {}

    #tree = etree.fromstring(html).getiterator("Directory")
    #tree = etree.fromstring(html).getiterator()
    temp_list=[]
    for sections in tree:

        temp_list.append( {'title'      : sections.get('title','Unknown').encode('utf-8'),
                'address'    : sections.get('host','Unknown')+":"+sections.get('port'),
                'serverName' : sections.get('serverName','Unknown').encode('utf-8'),
                'uuid'       : sections.get('machineIdentifier','Unknown') ,
                'path'       : sections.get('path') ,
                'token'      : sections.get('accessToken',None) ,
                'location'   : "myplex" ,
                'art'        : sections.get('art') ,
                'local'      : sections.get('local') ,
                'type'       : sections.get('type','Unknown'),
                'owned'      : sections.get('owned','0') })
    
    return temp_list            

    
May want to use this eventually for recently added etc.
            
        #if __settings__.getSetting('myplex_user') != '':
        #    addGUIItem('http://myplexqueue', {'title':'myplex Queue'},{'type':'Video' , 'mode' : _MODE_MYPLEXQUEUE})

        #for server in allservers.itervalues():

        #    #Plex plugin handling
        #    if (filter is not None) and (filter != "plugins"):
        #        continue

        #    if numOfServers > 1:
        #        prefix=server['serverName']+": "
        #    else:
        #        prefix=""

        #    details={'title' : prefix+"Channels" }
        #    extraData={'type' : "Video",
        #               'token' : server.get('token',None) }

        #    extraData['mode']=_MODE_CHANNELVIEW
        #    u="http://"+server['server']+":"+server['port']+"/system/plugins/all" 
        #    addGUIItem(u,details,extraData)

            #Create plexonline link
        #    details['title']=prefix+"Plex Online"
        #    extraData['type']="file"

        #    extraData['mode']=_MODE_PLEXONLINE

        #    u="http://"+server['server']+":"+server['port']+"/system/plexonline"
        #    addGUIItem(u,details,extraData)
        
        def videoPluginPlay( vids, prefix=None, indirect=None ):
    '''
        Plays Plugin Videos, which do not require library feedback
        but require further processing
        @input: url of video, plugin identifier
        @return: nothing. End of Script
    '''
    printDebug("== ENTER: videopluginplay with URL + " + vids + " ==", False)

    server=getServerFromURL(vids)
    if "node.plexapp.com" in server:
        server=getMasterServer()['address']

    #If we find the url lookup service, then we probably have a standard plugin, but possibly with resolution choices
    if '/services/url/lookup' in vids:
        printDebug("URL Lookup service")
        html=getURL(vids, suppress=False)
        if not html:
            return
        tree=etree.fromstring(html)

        mediaCount=0
        mediaDetails=[]
        for media in tree.getiterator('Media'):
            mediaCount+=1
            tempDict={'videoResolution' : media.get('videoResolution',"Unknown")}

            for child in media:
                tempDict['key']=child.get('key','')

            tempDict['identifier']=tree.get('identifier','')
            mediaDetails.append(tempDict)

        printDebug( str(mediaDetails) )

        #If we have options, create a dialog menu
        result=0
        if mediaCount > 1:
            printDebug ("Select from plugin video sources")
            dialogOptions=[x['videoResolution'] for x in mediaDetails ]
            videoResolution = xbmcgui.Dialog()

            result = videoResolution.select('Select resolution..',dialogOptions)

            if result == -1:
                return

        videoPluginPlay(getLinkURL('',mediaDetails[result],server))
        return

    #Check if there is a further level of XML required
    if indirect or '&indirect=1' in vids:
        printDebug("Indirect link")
        html=getURL(vids, suppress=False)
        if not html:
            return
        tree=etree.fromstring(html)

        for bits in tree.getiterator('Part'):
            videoPluginPlay(getLinkURL(vids,bits,server))
            break

        return

    #if we have a plex URL, then this is a transcoding URL
    if 'plex://' in vids:
        printDebug("found webkit video, pass to transcoder")
        getTranscodeSettings(True)
        if not (prefix):
            prefix="system"
        vids=transcode(0, vids, prefix)
        
        #Workaround for XBMC HLS request limit of 1024 byts
        if len(vids) > 1000:
            printDebug("XBMC HSL limit detected, will pre-fetch m3u8 playlist")
            
            playlist = getURL(vids)
            
            if not playlist or not "#EXTM3U" in playlist:
            
                printDebug("Unable to get valid m3u8 playlist from transcoder")
                return
            
            server=getServerFromURL(vids)
            session=playlist.split()[-1]
            vids="http://"+server+"/video/:/transcode/segmented/"+session+"?t=1"
            
    printDebug("URL to Play: " + vids)
    printDebug("Prefix is: " + str(prefix))

    #If this is an Apple movie trailer, add User Agent to allow access
    if 'trailers.apple.com' in vids:
        url=vids+"|User-Agent=QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
    elif server in vids:
        url=vids+getAuthDetails({'token': _PARAM_TOKEN})
    else:
        url=vids

    printDebug("Final URL is : " + url)

    item = xbmcgui.ListItem(path=url)
    start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    if 'transcode' in url:
        try:
            pluginTranscodeMonitor(g_sessionID,server)
        except:
            printDebug("Unable to start transcode monitor")
    else:
        printDebug("Not starting monitor")

    return

def channelSearch (url, prompt):
    '''
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    '''
    printDebug("== ENTER: channelsearch ==", False)

    if prompt:
        prompt=urllib.unquote(prompt)
    else:
        prompt="Enter Search Term..."

    kb = xbmc.Keyboard('', 'heading')
    kb.setHeading(prompt)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        printDebug("Search term input: "+ text)
        url=url+'&query='+urllib.quote(text)
        PlexPlugins( url )
    return
    
    def getMasterServer(all=False):
    printDebug("== ENTER: getmasterserver ==", False)

    possibleServers=[]
    current_master=__settings__.getSetting('masterServer')
#    for serverData in discoverAllServers().values():
#        printDebug( str(serverData) )
#        if serverData['master'] == 1:
#            possibleServers.append({'address' : serverData['server']+":"+serverData['port'] ,
#                                    'discovery' : serverData['discovery'],
#                                    'name'      : serverData['serverName'],
#                                    'token'     : serverData.get('token') })
    printDebug( "Possible master servers are " + str(possibleServers) )

    if all:
        return possibleServers

    if len(possibleServers) > 1:
        preferred="local"
        for serverData in possibleServers:
            if serverData['name'] == current_master:
                printDebug("Returning current master")
                return serverData
            if preferred == "any":
                printDebug("Returning 'any'")
                return serverData
            else:
                if serverData['discovery'] == preferred:
                    printDebug("Returning local")
                    return serverData
    elif len(possibleServers) == 0:
        return 
    
    return possibleServers[0]

def PlexPlugins( url, tree=None ):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER: PlexPlugins ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')

    tree=getXML(url,tree)
    if tree is None:
        return

    myplex_url=False
    server=getServerFromURL(url)
    if (tree.get('identifier') != "com.plexapp.plugins.myplex") and ( "node.plexapp.com" in url ) :
        myplex_url=True
        printDebug("This is a myplex URL, attempting to locate master server")
        server=getMasterServer()['address']

    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')
            
        if plugin.get('summary'):
            details['plot']=plugin.get('summary')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" ,
                   'key'          : plugin.get('key','') }

        if myplex_url:
            extraData['key']=extraData['key'].replace('node.plexapp.com:32400',server)
              
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, extraData, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":

            if plugin.get('search') == '1':
                extraData['mode']=_MODE_CHANNELSEARCH
                extraData['parameters']={'prompt' : plugin.get('prompt',"Enter Search Term").encode('utf-8') }
            else:
                extraData['mode']=_MODE_PLEXPLUGINS

            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Video":
            extraData['mode']=_MODE_VIDEOPLUGINPLAY
            
            for child in plugin:
                if child.tag == "Media":
                    extraData['parameters'] = {'indirect' : child.get('indirect','0')}            
            
            addGUIItem(p_url, details, extraData, folder=False)

        elif plugin.tag == "Setting":

            if plugin.get('option') == 'hidden':
                value="********"
            elif plugin.get('type') == "text":
                value=plugin.get('value')
            elif plugin.get('type') == "enum":
                value=plugin.get('values').split('|')[int(plugin.get('value',0))]
            else:
                value=plugin.get('value')

            details['title']= "%s - [%s]" % (plugin.get('label','Unknown').encode('utf-8'), value)
            extraData['mode']=_MODE_CHANNELPREFS
            extraData['parameters']={'id' : plugin.get('id') }
            addGUIItem(url, details, extraData)


    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
def channelSettings ( url, settingID ):
    '''
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    '''
    printDebug("== ENTER: channelSettings ==", False)
    printDebug("Setting preference for ID: %s" % settingID )

    if not settingID:
        printDebug("ID not set")
        return

    tree=getXML(url)
    if tree is None:
        return

    setWindowHeading(tree)
    setString=None
    for plugin in tree:

        if plugin.get('id') == settingID:
            printDebug("Found correct id entry for: %s" % settingID)
            id=settingID

            label=plugin.get('label',"Enter value").encode('utf-8')
            option=plugin.get('option').encode('utf-8')
            value=plugin.get('value').encode('utf-8')

            if plugin.get('type') == "text":
                printDebug("Setting up a text entry screen")
                kb = xbmc.Keyboard(value, 'heading')
                kb.setHeading(label)

                if option == "hidden":
                    kb.setHiddenInput(True)
                else:
                    kb.setHiddenInput(False)

                kb.doModal()
                if (kb.isConfirmed()):
                    value = kb.getText()
                    printDebug("Value input: "+ value)
                else:
                    printDebug("User cancelled dialog")
                    return False

            elif plugin.get('type') == "enum":
                printDebug("Setting up an enum entry screen")

                values=plugin.get('values').split('|')

                settingScreen = xbmcgui.Dialog()
                value = settingScreen.select(label,values)
                if value == -1:
                    printDebug("User cancelled dialog")
                    return False
            else:
                printDebug('Unknown option type: %s' % plugin.get('id') )

        else:
            value=plugin.get('value')
            id=plugin.get('id')

        if setString is None:
            setString='%s/set?%s=%s' % (url, id, value)
        else:
            setString='%s&%s=%s' % (setString, id, value)

    printDebug ("Settings URL: %s" % setString )
    getURL (setString)
    xbmc.executebuiltin("Container.Refresh")

    return False
def plexOnline( url ):
    printDebug("== ENTER: plexOnline ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    server=getServerFromURL(url)

    tree=getXML(url)
    if tree is None:
        return

    for plugin in tree:

        details={'title' : plugin.get('title',plugin.get('name','Unknown')).encode('utf-8') }
        extraData={'type'      : "Video" ,
                   'installed' : int(plugin.get('installed',2)) ,
                   'key'       : plugin.get('key','') ,
                   'thumb'     : getThumb(plugin,server)}

        extraData['mode']=_MODE_CHANNELINSTALL

        if extraData['installed'] == 1:
            details['title']=details['title']+" (installed)"

        elif extraData['installed'] == 2:
            extraData['mode']=_MODE_PLEXONLINE

        u=getLinkURL(url, plugin, server)

        extraData['parameters']={'name' : details['title'] }
        
        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
def channelView( url ):
    printDebug("== ENTER: channelView ==", False)
    tree=getXML(url)
    if tree is None:
        return
    server=getServerFromURL(url)
    setWindowHeading(tree)
    for channels in tree.getiterator('Directory'):

        if channels.get('local','') == "0":
            continue

        arguments=dict(channels.items())

        extraData={'fanart_image' : getFanart(channels, server) ,
                   'thumb'        : getThumb(channels, server) }

        details={'title' : channels.get('title','Unknown') }

        suffix=channels.get('path').split('/')[1]

        if channels.get('unique','')=='0':
            details['title']=details['title']+" ("+suffix+")"

        #Alter data sent into getlinkurl, as channels use path rather than key
        p_url=getLinkURL(url, {'key': channels.get('path',None), 'identifier' : channels.get('path',None)} , server)

        if suffix == "photos":
            extraData['mode']=_MODE_PHOTOS
        elif suffix == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
        elif suffix == "music":
            extraData['mode']=_MODE_MUSIC
        else:
            extraData['mode']=_MODE_GETCONTENT

        addGUIItem(p_url,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
def shelf( server_list=None ):
    #Gather some data and set the window properties
    printDebug("== ENTER: shelf() ==", False)
    
    if __settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and __settings__.getSetting('musicShelf') == "false":
        printDebug("Disabling all shelf items")
        clearShelf()
        return

    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    movieCount=1
    seasonCount=1
    musicCount=1
    added_list={}    
    direction=True
    full_count=0
    
    if server_list is None:
        server_list=discoverAllServers()

    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0,0,0)
        return
        
    if __settings__.getSetting('homeshelf') == '0':
        endpoint="/library/recentlyAdded"
    else:
        direction=False
        endpoint="/library/onDeck"

    for server_details in server_list.values():

        if not server_details['owned'] == '1':
            continue
    
        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token','')
        
        tree=getXML('http://'+server_details['server']+":"+server_details['port']+endpoint)
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearShelf()
            return

        for eachitem in tree:

            if direction:
                added_list[int(eachitem.get('addedAt',0))] = (eachitem, server_details['server']+":"+server_details['port'])
            else:
                added_list[full_count] = (eachitem, server_details['server']+":"+server_details['port'])
                full_count += 1
                
    library_filter = __settings__.getSetting('libraryfilter')
    acceptable_level = __settings__.getSetting('contentFilter')
    
    #For each of the servers we have identified
    for index in sorted(added_list, reverse=direction):
        
        media=added_list[index][0]
        server_address=added_list[index][1]
        
        if media.get('type',None) == "movie":

            printDebug("Found a recent movie entry: [%s]" % ( media.get('title','Unknown').encode('UTF-8') , ))

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("xbmb3c.LatestMovie.1.Path" )
                continue

            if not displayContent( acceptable_level , media.get('contentRating') ):
                continue

            if media.get('librarySectionID') == library_filter:
                printDebug("SKIPPING: Library Filter match: %s = %s " % (library_filter, media.get('librarySectionID')))
                continue

            m_url="plugin://plugin.video.xbmb3c?url=%s&mode=%s%s" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF)
            m_thumb=getThumb(media,server_address)

            WINDOW.setProperty("xbmb3c.LatestMovie.%s.Path" % movieCount, m_url)
            WINDOW.setProperty("xbmb3c.LatestMovie.%s.Title" % movieCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestMovie.%s.Thumb" % movieCount, m_thumb)

            movieCount += 1

            printDebug("Building Recent window title: %s" % media.get('title','Unknown').encode('UTF-8'))
            printDebug("Building Recent window url: %s" % m_url)
            printDebug("Building Recent window thumb: %s" % m_thumb)

        elif media.get('type',None) == "season":

            printDebug("Found a recent season entry [%s]" % ( media.get('parentTitle','Unknown').encode('UTF-8') , ))

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("xbmb3c.LatestEpisode.1.Path" )
                continue

            s_url="ActivateWindow(VideoLibrary, plugin://plugin.video.xbmb3c?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TVEPISODES)
            s_thumb=getThumb(media,server_address)

            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.Path" % seasonCount, s_url )
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.EpisodeTitle" % seasonCount, '')
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.ShowTitle" % seasonCount, media.get('parentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.Thumb" % seasonCount, s_thumb)
            seasonCount += 1

            printDebug("Building Recent window title: %s" % media.get('parentTitle','Unknown').encode('UTF-8'))
            printDebug("Building Recent window url: %s" % s_url)
            printDebug("Building Recent window thumb: %s" % s_thumb)

        elif media.get('type') == "album":

            if __settings__.getSetting('musicShelf') == "false":
                WINDOW.clearProperty("xbmb3c.LatestAlbum.1.Path" )
                continue
            printDebug("Found a recent album entry")

            s_url="ActivateWindow(MusicFiles, plugin://plugin.video.xbmb3c?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TRACKS)
            s_thumb=getThumb(media,server_address)

            WINDOW.setProperty("xbmb3c.LatestAlbum.%s.Path" % musicCount, s_url )
            WINDOW.setProperty("xbmb3c.LatestAlbum.%s.Title" % musicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestAlbum.%s.Artist" % musicCount, media.get('parentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestAlbum.%s.Thumb" % musicCount, s_thumb)
            musicCount += 1

            printDebug("Building Recent window title: %s" % media.get('parentTitle','Unknown').encode('UTF-8'))
            printDebug("Building Recent window url: %s" % s_url)
            printDebug("Building Recent window thumb: %s" % s_thumb)

        elif media.get('type',None) == "episode":

            printDebug("Found an onDeck episode entry [%s]" % ( media.get('title','Unknown').encode('UTF-8') , ))

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("xbmb3c.LatestEpisode.1.Path" )
                continue

            s_url="PlayMedia(plugin://plugin.video.xbmb3c?url=%s&mode=%s%s)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF)
            s_thumb="http://"+server_address+media.get('grandparentThumb','')

            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.Path" % seasonCount, s_url )
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.EpisodeTitle" % seasonCount, media.get('title','').encode('utf-8'))
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.ShowTitle" % seasonCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("xbmb3c.LatestEpisode.%s.Thumb" % seasonCount, s_thumb)
            seasonCount += 1

            printDebug("Building Recent window title: %s" % media.get('title','Unknown').encode('UTF-8'))
            printDebug("Building Recent window url: %s" % s_url)
            printDebug("Building Recent window thumb: %s" % s_thumb)
            
    clearShelf( movieCount, seasonCount, musicCount)

def clearShelf (movieCount=0, seasonCount=0, musicCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug("Clearing unused properties")

    try:
        for i in range(movieCount, 50+1):
            WINDOW.clearProperty("xbmb3c.LatestMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestMovie.%s.Thumb"  % ( i ) )
        printDebug("Done clearing movies")
    except: pass

    try:
        for i in range(seasonCount, 50+1):
            WINDOW.clearProperty("xbmb3c.LatestEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestEpisode.%s.Thumb"          % ( i ) )
        printDebug("Done clearing tv")
    except: pass

    try:
        for i in range(musicCount, 50+1):
            WINDOW.clearProperty("xbmb3c.LatestAlbum.%s.Path"   % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestAlbum.%s.Title"  % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestAlbum.%s.Artist" % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestAlbum.%s.Thumb"  % ( i ) )
        printDebug("Done clearing music")
    except: pass


    return

def shelfChannel( server_list = None):
    #Gather some data and set the window properties
    printDebug("== ENTER: shelfChannels() ==", False)
    
    if __settings__.getSetting('channelShelf') == "false":
        printDebug("Disabling channel shelf")
        clearChannelShelf()
        return
        
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    channelCount=1
    
    if server_list is None:
        server_list=discoverAllServers()
    
    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearChannelShelf()
        return
    
    for server_details in server_list.values():

        if not server_details['owned'] == '1':
            continue
        
        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token','')

        if __settings__.getSetting('channelShelf') == "false":
            WINDOW.clearProperty("xbmb3c.LatestChannel.1.Path" )
            return

        tree=getXML('http://'+server_details['server']+":"+server_details['port']+'/channels/recentlyViewed')
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearChannelShelf(0)
            return

        #For each of the servers we have identified
        for media in tree:

            if media.get('type') == "channel":

                printDebug("Found a recent channel entry")

                suffix=media.get('key').split('/')[1]

                if suffix == "photos":
                    mode=_MODE_PHOTOS
                    channel_window="Pictures"
                elif suffix == "video":
                    mode=_MODE_PLEXPLUGINS
                    channel_window="VideoLibrary"
                elif suffix == "music":
                    mode=_MODE_MUSIC
                    channel_window="MusicFiles"
                else:
                    mode=_MODE_GETCONTENT
                    channel_window="VideoLibrary"


                p_url="ActivateWindow(%s, plugin://plugin.video.xbmb3c?url=%s&mode=%s%s, return)" % ( channel_window, getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), mode)
                p_thumb=getThumb(media,server_details['server']+":"+server_details['port'])

                WINDOW.setProperty("xbmb3c.LatestChannel.%s.Path" % channelCount, p_url)
                WINDOW.setProperty("xbmb3c.LatestChannel.%s.Title" % channelCount, media.get('title','Unknown'))
                WINDOW.setProperty("xbmb3c.LatestChannel.%s.Thumb" % channelCount, p_thumb)

                channelCount += 1

                printDebug("Building Recent window title: %s" % media.get('title','Unknown'))
                printDebug("Building Recent window url: %s" % p_url)
                printDebug("Building Recent window thumb: %s" % p_thumb)

    clearChannelShelf(channelCount)        
    return
    
def clearChannelShelf (channelCount=0):
            
    WINDOW = xbmcgui.Window( 10000 )
        
    try:
        for i in range(channelCount, 30+1):
            WINDOW.clearProperty("xbmb3c.LatestChannel.%s.Path"   % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestChannel.%s.Title"  % ( i ) )
            WINDOW.clearProperty("xbmb3c.LatestChannel.%s.Thumb"  % ( i ) )
        printDebug("Done clearing channels")
    except: pass

    return

def myPlexQueue():
    printDebug("== ENTER: myplexqueue ==", False)

    if __settings__.getSetting('myplex_user') == '':
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")
        return

    html=getMyPlexURL('/pms/playlists/queue/all')
    tree=etree.fromstring(html)

    PlexPlugins('http://my.plexapp.com/playlists/queue/all', tree)
    return

def getTranscodeSettings( override=False ):
    printDebug("== ENTER: gettranscodesettings ==", False)

    global g_transcode
    g_transcode = __settings__.getSetting('transcode')

    if override is True:
            printDebug( "Transcode override.  Will play media with addon transcoding settings")
            g_transcode="true"

    if g_transcode == "true":
        #If transcode is set, ignore the stream setting for file and smb:
        global g_stream
        g_stream = "1"
        printDebug( "We are set to Transcode, overriding stream selection")
        global g_transcodefmt
        g_transcodefmt="m3u8"

        global g_quality
        g_quality = str(int(__settings__.getSetting('quality'))+3)
        printDebug( "Transcode format is " + g_transcodefmt)
        printDebug( "Transcode quality is " + g_quality)

        baseCapability="http-live-streaming,http-mp4-streaming,http-streaming-video,http-streaming-video-1080p,http-mp4-video,http-mp4-video-1080p;videoDecoders=h264{profile:high&resolution:1080&level:51};"

        g_audioOutput=__settings__.getSetting("audiotype")
        if g_audioOutput == "0":
            audio="mp3,aac{bitrate:160000}"
        elif g_audioOutput == "1":
            audio="ac3{channels:6}"
        elif g_audioOutput == "2":
            audio="dts{channels:6}"

        global capability
        capability="X-Plex-Client-Capabilities="+urllib.quote_plus("protocols="+baseCapability+"audioDecoders="+audio)
        printDebug("Plex Client Capability = " + capability)

        import uuid
        global g_sessionID
        g_sessionID=str(uuid.uuid4())

def alterSubs ( url ):
    '''
        Display a list of available Subtitle streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug("== ENTER: alterSubs ==", False)
    html=getURL(url)

    tree=etree.fromstring(html)

    sub_list=['']
    display_list=["None"]
    fl_select=False
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "3":

                stream_id=streams.get('id')
                lang=streams.get('languageCode',"Unknown").encode('utf-8')
                printDebug("Detected Subtitle stream [%s] [%s]" % ( stream_id, lang ) )

                if streams.get('format',streams.get('codec')) == "idx":
                    printDebug("Stream: %s - Ignoring idx file for now" % stream_id)
                    continue
                else:
                    sub_list.append(stream_id)

                    if streams.get('selected',None) == '1':
                        fl_select=True
                        language=streams.get('language','Unknown')+"*"
                    else:
                        language=streams.get('language','Unknown')

                    display_list.append(language)
        break

    if not fl_select:
        display_list[0]=display_list[0]+"*"

    subScreen = xbmcgui.Dialog()
    result = subScreen.select('Select subtitle',display_list)
    if result == -1:
        return False

    authtoken=getAuthTokenFromURL(url)
    sub_select_URL="http://%s/library/parts/%s?subtitleStreamID=%s" % ( getServerFromURL(url), part_id, sub_list[result] ) +getAuthDetails({'token':authtoken})

    printDebug("User has selected stream %s" % sub_list[result])
    printDebug("Setting via URL: %s" % sub_select_URL )
    outcome=getURL(sub_select_URL, type="PUT")

    printDebug( sub_select_URL )

    return True

def alterAudio ( url ):
    '''
        Display a list of available audio streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug("== ENTER: alterAudio ==", False)

    html=getURL(url)
    tree=etree.fromstring(html)

    audio_list=[]
    display_list=[]
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "2":

                stream_id=streams.get('id')
                audio_list.append(stream_id)
                lang=streams.get('languageCode', "Unknown")

                printDebug("Detected Audio stream [%s] [%s] " % ( stream_id, lang))

                if streams.get('channels','Unknown') == '6':
                    channels="5.1"
                elif streams.get('channels','Unknown') == '7':
                    channels="6.1"
                elif streams.get('channels','Unknown') == '2':
                    channels="Stereo"
                else:
                    channels=streams.get('channels','Unknown')

                if streams.get('codec','Unknown') == "ac3":
                    codec="AC3"
                elif streams.get('codec','Unknown') == "dca":
                    codec="DTS"
                else:
                    codec=streams.get('codec','Unknown')

                language="%s (%s %s)" % ( streams.get('language','Unknown').encode('utf-8') , codec, channels )

                if streams.get('selected') == '1':
                    language=language+"*"

                display_list.append(language)
        break

    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select audio',display_list)
    if result == -1:
        return False

    authtoken=getAuthTokenFromURL(url)        
    audio_select_URL="http://%s/library/parts/%s?audioStreamID=%s" % ( getServerFromURL(url), part_id, audio_list[result] ) +getAuthDetails({'token':authtoken})
    printDebug("User has selected stream %s" % audio_list[result])
    printDebug("Setting via URL: %s" % audio_select_URL )

    outcome=getURL(audio_select_URL, type="PUT")

    return True

def getAuthTokenFromURL( url ):
    if "X-Plex-Token=" in url:
        return url.split('X-Plex-Token=')[1]
    else:
        return ""
        
def displayContent( acceptable_level, content_level ):

    '''
        Takes a content Rating and decides whether it is an allowable
        level, as defined by the content filter
        @input: content rating
        @output: boolean
    '''

    printDebug ("Checking rating flag [%s] against [%s]" % (content_level, acceptable_level))

    if acceptable_level == "Adults":
        printDebug ("OK to display")
        return True

    content_map = { 'Kids' : 0 ,
                    'Teens' : 1 ,
                    'Adults' : 2 }

    rating_map= { 'G' : 0 ,       # MPAA Kids
                  'PG' : 0 ,      # MPAA Kids
                  'PG-13' : 1 ,   # MPAA Teens
                  'R' : 2 ,       # MPAA Adults
                  'NC-17' : 2 ,   # MPAA Adults
                  'NR' : 2 ,      # MPAA Adults
                  'Unrated' : 2 , # MPAA Adults

                  'U' : 0 ,       # BBFC Kids
                  'PG' : 0 ,      # BBFC Kids
                  '12' : 1 ,      # BBFC Teens
                  '12A' : 1 ,     # BBFC Teens
                  '15' : 1 ,      # BBFC Teens
                  '18' : 2 ,      # BBFC Adults
                  'R18' : 2 ,     # BBFC Adults

                  'E' : 0 ,       #ACB Kids (hopefully)
                  'G' : 0 ,       #ACB Kids
                  'PG' : 0 ,      #ACB Kids
                  'M' : 1 ,       #ACB Teens
                  'MA15+' : 2 ,   #ADC Adults
                  'R18+' : 2 ,    #ACB Adults
                  'X18+' : 2 ,    #ACB Adults

                  'TV-Y'  : 0 ,   # US TV - Kids
                  'TV-Y7' : 0 ,   # US TV - Kids
                  'TV -G' : 0 ,   # Us TV - kids
                  'TV-PG' : 1 ,   # US TV - Teens
                  'TV-14' : 1 ,   # US TV - Teens
                  'TV-MA' : 2 ,   # US TV - Adults

                  'G' :  0 ,      # CAN - kids
                  'PG' : 0 ,      # CAN - kids
                  '14A' : 1 ,     # CAN - teens
                  '18A' : 2 ,     # CAN - Adults
                  'R' : 2 ,       # CAN - Adults
                  'A' : 2 }       # CAN - Adults

    if content_level is None or content_level == "None":
        printDebug("Setting [None] rating as %s" % ( __settings__.getSetting('contentNone') , ))
        if content_map[__settings__.getSetting('contentNone')] <= content_map[acceptable_level]:
            printDebug ("OK to display")
            return True
    else:
        try:
            if rating_map[content_level] <= content_map[acceptable_level]:
                printDebug ("OK to display")
                return True
        except:
            print "Unknown rating flag [%s] whilst lookuing for [%s] - will filter for now, but needs to be added" % (content_level, acceptable_level)

    printDebug ("NOT OK to display")
    return False
def skin( server_list=None):
    #Gather some data and set the window properties
    printDebug("== ENTER: skin() ==", False)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    shared_flag={}
    hide_shared = __settings__.getSetting('hide_shared')
    
    if server_list is None:
        server_list = discoverAllServers()
    
    #For each of the servers we have identified
    for section in getAllSections(server_list):

        extraData={ 'fanart_image' : getFanart(section, section['address']) ,
                    'thumb'        : getFanart(section, section['address'], False) }

        #Determine what we are going to do process after a link is selected by the user, based on the content we find

        path=section['path']

        if section['type'] == 'show':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['show']=True
                continue
            window="VideoLibrary"
            mode=_MODE_TVSHOWS
        if  section['type'] == 'movie':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['movie']=True
                continue
            window="VideoLibrary"
            mode=_MODE_MOVIES
        if  section['type'] == 'artist':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['artist']=True
                continue
            window="MusicFiles"
            mode=_MODE_ARTISTS
        if  section['type'] == 'photo':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['photo']=True
                continue
            window="Pictures"
            mode=_MODE_PHOTOS

        if g_secondary == "true":
            mode=_MODE_GETCONTENT
        else:
            path=path+'/all'

        s_url='http://%s%s&mode=%s%s' % ( section['address'], path, mode)

        #Build that listing..
        WINDOW.setProperty("xbmb3c.%d.title"    % (sectionCount) , section['title'])
        WINDOW.setProperty("xbmb3c.%d.subtitle" % (sectionCount) , section['serverName'])
        WINDOW.setProperty("xbmb3c.%d.path"     % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/?url="+s_url+",return)")
        WINDOW.setProperty("xbmb3c.%d.art"      % (sectionCount) , extraData['fanart_image'])
        WINDOW.setProperty("xbmb3c.%d.type"     % (sectionCount) , section['type'])
        WINDOW.setProperty("xbmb3c.%d.icon"     % (sectionCount) , extraData['thumb'])
        WINDOW.setProperty("xbmb3c.%d.thumb"    % (sectionCount) , extraData['thumb'])
        WINDOW.setProperty("xbmb3c.%d.partialpath" % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.xbmb3c/?url=http://"+section['address']+section['path'])

        printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + section['title'] + "]")
        printDebug("PATH in use is: ActivateWindow("+window+",plugin://plugin.video.xbmb3c/?url="+s_url+",return)")
        sectionCount += 1

    if shared_flag.get('movie'):
        WINDOW.setProperty("xbmb3c.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("xbmb3c.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("xbmb3c.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.xbmb3c/?url=/&mode="+str(_MODE_SHARED_MOVIES)+",return)")
        WINDOW.setProperty("xbmb3c.%d.type"     % (sectionCount) , "movie")
        sectionCount += 1

    if shared_flag.get('show'):
        WINDOW.setProperty("xbmb3c.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("xbmb3c.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("xbmb3c.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.xbmb3c/?url=/&mode="+str(_MODE_SHARED_SHOWS)+",return)")
        WINDOW.setProperty("xbmb3c.%d.type"     % (sectionCount) , "show")
        sectionCount += 1
        
    if shared_flag.get('artist'):
        WINDOW.setProperty("xbmb3c.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("xbmb3c.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("xbmb3c.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.xbmb3c/?url=/&mode="+str(_MODE_SHARED_MUSIC)+",return)")
        WINDOW.setProperty("xbmb3c.%d.type"     % (sectionCount) , "artist")
        sectionCount += 1
        
    if shared_flag.get('photo'):
        WINDOW.setProperty("xbmb3c.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("xbmb3c.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("xbmb3c.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.xbmb3c/?url=/&mode="+str(_MODE_SHARED_PHOTOS)+",return)")
        WINDOW.setProperty("xbmb3c.%d.type"     % (sectionCount) , "photo")
        sectionCount += 1
        
        
    #For each of the servers we have identified
    numOfServers=len(server_list)

    for server in server_list.values():
    
        if g_channelview == "true":
            WINDOW.setProperty("xbmb3c.channel", "1")
            WINDOW.setProperty("xbmb3c.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.xbmb3c/?url=http://"+server['server']+":"+server['port']+"/system/plugins/all&mode=21"+",return)")
        else:
            WINDOW.clearProperty("xbmb3c.channel")
            WINDOW.setProperty("xbmb3c.%d.server.video" % (serverCount) , "http://"+server['server']+":"+server['port']+"/video&mode=7")
            WINDOW.setProperty("xbmb3c.%d.server.music" % (serverCount) , "http://"+server['server']+":"+server['port']+"/music&mode=17")
            WINDOW.setProperty("xbmb3c.%d.server.photo" % (serverCount) , "http://"+server['server']+":"+server['port']+"/photos&mode=16")

        WINDOW.setProperty("xbmb3c.%d.server.online" % (serverCount) , "http://"+server['server']+":"+server['port']+"/system/plexonline&mode=19")

        WINDOW.setProperty("xbmb3c.%d.server" % (serverCount) , server['serverName'])
        printDebug ("Name mapping is :" + server['serverName'])

        serverCount+=1

    #Clear out old data
    try:
        printDebug("Clearing properties from [" + str(sectionCount) + "] to [" + WINDOW.getProperty("xbmb3c.sectionCount") + "]")

        for i in range(sectionCount, int(WINDOW.getProperty("xbmb3c.sectionCount"))+1):
            WINDOW.clearProperty("xbmb3c.%d.title"    % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.url"      % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.path"     % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.window"   % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.art"      % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.type"     % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.icon"     % ( i ) )
            WINDOW.clearProperty("xbmb3c.%d.thumb"    % ( i ) )
    except:
        pass

    printDebug("Total number of skin sections is [" + str(sectionCount) + "]")
    printDebug("Total number of servers is ["+str(numOfServers)+"]")
    WINDOW.setProperty("xbmb3c.sectionCount", str(sectionCount))
    WINDOW.setProperty("xbmb3c.numServers", str(numOfServers))
    if __settings__.getSetting('myplex_user') != '':
        WINDOW.setProperty("xbmb3c.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.xbmb3c/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("xbmb3c.myplex",  "1" )
    else:
        WINDOW.clearProperty("xbmb3c.myplex")

    return
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

def photoTranscode( server, url, width=1280, height=720 ):
        return 'http://%s/photo/:/transcode?url=%s&width=%s&height=%s' % (server, urllib.quote_plus(url), width, height)

def libraryRefresh( url ):
    printDebug("== ENTER: libraryRefresh ==", False)
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\",Library Refresh started,100)")
    return

