import logging
import time
import os
import struct

from golem.resource.ResourceConnState import ResourceConnState
from golem.Message import MessageHasResource, MessageWantResource, MessagePushResource, MessageDisconnect,\
    MessagePullResource, MessagePullAnswer, MessageSendResource

logger = logging.getLogger(__name__)

class ResourceSession:

    ConnectionStateType = ResourceConnState

    DCRBadProtocol      = "Bad protocol"
    DCRDuplicatePeers   = "Duplicate peers"

    ##########################
    def __init__( self, conn ):
        self.conn = conn
        pp = conn.transport.getPeer()
        self.address = pp.host
        self.port = pp.port
        self.lastDisconnectTime = None
        self.resourceServer = None
        self.fileSize = -1
        self.fileName = None
        self.recvSize = 0
        self.confirmation = False

    ##########################
    def interpret( self, msg ):

        if msg is None:
            return

        type = msg.getType()

        if type == MessagePushResource.Type:
            if self.resourceServer.checkResource( msg.resource ):
                self.sendHasResource( msg.resource )
            else:
                self.sendWantResource( msg.resource )
                self.fileName = msg.resource
                self.conn.fileMode = True
                self.confirmation = True
        elif type == MessageHasResource.Type:
            self.resourceServer.hasResource( msg.resource, self.address, self.port )
            self.dropped()
        elif type == MessageWantResource.Type:
            file_ = self.resourceServer.prepareResource( msg.resource )
            size = os.path.getsize( file_ )
            with open( file_, 'rb') as fh:
                data = struct.pack( "!L", size ) + fh.read( 1024 )
                while data:
                    self.conn.transport.write( data )
                    data = fh.read( 1024 )
        elif type == MessageDisconnect.Type:
            logger.info( "Disconnecting {}:{}".format( self.address, self.port ) )
            self.dropped()
        elif type == MessagePullResource.Type:
            self.sendPullAnswer( msg.resource, self.resourceServer.checkResource( msg.resource) )
        elif type == MessagePullAnswer.Type:
            self.resourceServer.pullAnswer( msg.resource, msg.hasResource, self )
        else:
            self.__disconnect( ResourceSession.DCRBadProtocol )

    ##########################
    def fileDataReceived( self, data ):
        locData = data
        if self.fileSize == -1:
            (self.fileSize, ) = struct.unpack( "!L", data[0:4] )
            locData = data[ 4: ]
            self.fh = open( self.resourceServer.prepareResource( self.fileName ), 'wb' )

        assert self.fh
        self.recvSize += len( locData )
        self.fh.write( locData )

        if self.recvSize == self.fileSize:
            self.conn.fileMode = False
            self.fh.close()
            self.fh = None
            self.fileSize = -1
            self.recvSize = 0
            if self.confirmation:
                self.__send( MessageHasResource( self.fileName ) )
                self.confirmation = False
            else:
                self.resourceServer.resourceDownloaded( self.fileName, self.address, self.port )
                self.dropped()
            self.fileName = None


    ##########################
    def dropped( self ):
        self.conn.close()

    ##########################
    def sendHasResource( self, resource ):
        self.__send( MessageHasResource( resource ) )

    ##########################
    def sendWantResource( self, resource ):
        self.__send( MessageWantResource( resource ) )

    ##########################
    def sendPushResource( self, resource ):
         self.__send( MessagePushResource( resource ) )

    ##########################
    def sendPullResource( self, resource ):
         self.__send( MessagePullResource( resource ) )

    ##########################
    def sendPullAnswer( self, resource, hasResource ):
        self.__send( MessagePullAnswer( resource, hasResource ) )

    ##########################
    def sendSendResource( self, resource ):
        self.__send( MessageSendResource( resource) )
        self.conn.fileMode = True

    ##########################
    def __sendDisconnect(self, reason):
        self.__send( MessageDisconnect( reason ) )


    ##########################
    def __send( self, msg ):
        if not self.conn.sendMessage( msg ):
            self.dropped()

    ##########################
    def __disconnect(self, reason):
        logger.info( "Disconnecting {} : {} reason: {}".format( self.address, self.port, reason ) )
        if self.conn.isOpen():
            if self.lastDisconnectTime:
                self.dropped()
            else:
                self.__sendDisconnect(reason)
                self.lastDisconnectTime = time.time()
