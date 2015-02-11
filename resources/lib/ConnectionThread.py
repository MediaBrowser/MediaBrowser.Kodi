import xbmc
import xbmcgui
import xbmcaddon

import threading
import urllib
import urllib2
import httplib
import hashlib
import StringIO
import gzip
import encodings

'''
            connManager = ConnectionThread()
            connManager.server = server
            connManager.url = urlPath
            connManager.type = type
            connManager.body = postBody                
            connManager.headers = head
            
            connManager.start()
            
            while (connManager.finished == False):
                xbmc.sleep(50)
                if(xbmc.abortRequested == True):
                    connManager.close()
                
            link = connManager.data
            
            if(connManager.statusCode != 200):
                self.logMsg("Error connecting to server : " + str(connManager.statusCode))
                xbmc.executebuiltin("XBMC.Notification(Connection Error: Unable to connect to server:" + str(connManager.statusCode) + ",)")
             
            del connManager   
'''            



class ConnectionThread(threading.Thread):

    headers = None
    type = None
    server = None
    url = None
    body = None
    finished = False
    data = ""
    statusCode = -1
    conn = None

    def __init__(self, *args):
        
        threading.Thread.__init__(self, *args)
     
    def close(self):
        xbmc.log("Connection Manager: Closing Connection")
        self.finished = True
        if(self.conn != None):
            self.conn.close()
    
    def run(self):
        
        try:
            '''
            xbmc.log("Connection Manager Thread Started")
            
            xbmc.log("type    : " + str(self.type))
            xbmc.log("server  : " + str(self.server))
            xbmc.log("url     : " + str(self.url))
            xbmc.log("headers : " + str(self.headers))
            '''
            
            self.conn = httplib.HTTPConnection(self.server, timeout=2)
            
            if(self.body != None):
                self.headers["Content-Type"] = "application/x-www-form-urlencoded"
                self.headers["Content-Length"] = str(len(self.body))
                xbmc.log("ConnectionThread -> POST DATA : " + self.body)
                self.conn.request(method=self.type, url=self.url, body=self.body, headers=self.headers)
            else:
                self.conn.request(method=self.type, url=self.url, headers=self.headers)
            
            responce = self.conn.getresponse()
            
            self.statusCode = int(responce.status)
            
            xbmc.log("ConnectionThread -> Response Code : " + str(self.statusCode))
            
            if (self.statusCode == 200):
                retData = responce.read()
                contentType = responce.getheader('content-encoding')
                xbmc.log("ConnectionThread -> Data Len Before : " + str(len(retData)))
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    self.data = gzipper.read()
                else:
                    self.data = retData
                    
            self.conn.close()
                
        except Exception, msg:
            xbmc.log("Unable to connect to " + str(server) + " : " + str(msg))
            xbmc.log(str(Exception))
            
        self.finished = True

        
                
                