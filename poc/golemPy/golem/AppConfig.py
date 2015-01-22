import sys
sys.path.append('core')
import os
import logging

from golem.core.simpleconfig import SimpleConfig, ConfigEntry
from golem.core.simpleenv import SimpleEnv
from golem.core.prochelper import ProcessService
from ClientConfigDescriptor import  ClientConfigDescriptor

CONFIG_FILENAME = "app_cfg.ini"
ESTM_FILENAME = "minilight.ini"
MANAGER_PORT = 20301
MANAGER_ADDRESS = "127.0.0.1"
ESTIMATED_DEFAULT = 2220.0
START_PORT = 40102
END_PORT = 60102
OPTIMAL_PEER_NUM = 10
DEFAULT_ROOT_PATH = "C:\\Sources\\golem\\poc\\golemPy\\examples\\gnr"
MAX_RESOURCE_SIZE = 250 * 1024
MAX_MEMORY_SIZE = 250 * 1024
APP_NAME = "Golem LAN Renderer"
APP_VERSION = "1.021"


class CommonConfig:

    ##############################
    def __init__( self,
                  section = "Common",
                  rootPath = DEFAULT_ROOT_PATH,
                  managerAddress = MANAGER_ADDRESS,
                  managerPort = MANAGER_PORT,
                  startPort = START_PORT,
                  endPort = END_PORT,
                  optimalPeerNum = OPTIMAL_PEER_NUM,
                  appName = APP_NAME,
                  appVersion = APP_VERSION ):

        self._section = section

        ConfigEntry.createProperty( section, "optimal peer num",    optimalPeerNum,    self, "OptimalPeerNum" )
        ConfigEntry.createProperty( section, "start port",          startPort, self, "StartPort" )
        ConfigEntry.createProperty( section, "end port",            endPort, self, "EndPort" )
        ConfigEntry.createProperty( section, "manager address", managerAddress, self, "ManagerAddress" )
        ConfigEntry.createProperty( section, "manager listen port", managerPort, self, "ManagerListenPort" )
        ConfigEntry.createProperty( section, "resource root path", rootPath, self, "RootPath")
        ConfigEntry.createProperty( section, "application name", appName, self, "AppName" )
        ConfigEntry.createProperty( section, "application version", appVersion, self, "AppVersion" )

    ##############################
    def section( self ):
        return self._section


class NodeConfig:

    @classmethod
    def readEstimatedPerformance(cls):
        estmFile = SimpleEnv.envFileName(ESTM_FILENAME)
        res = 0
        if os.path.isfile(estmFile):
            try:
                file = open(estmFile, 'r')
                res = "{0:.1f}".format(float(file.read()))
                file.close()
            except:
                return 0
        return res

    SEND_PINGS = 1
    PINGS_INTERVALS = 120
    GETTING_PEERS_INTERVAL = 4.0
    GETTING_TASKS_INTERVAL = 4.0
    TASK_REQUEST_INTERVAL = 5.0
    USE_WAITING_FOR_TASK_TIMEOUT = 0
    WAITING_FOR_TASK_TIMEOUT = 36000
    NODE_SNAPSHOT_INTERVAL = 4.0
    ADD_TASKS = 0
    MAX_SENDING_DELAY = 360
    USE_DISTRIBUTED_RESOURCE_MANAGEMENT = 1

    ##############################
    def __init__( self, nodeId, seedHost = "", seedPort = 0, numCores = 4, maxResourceSize = MAX_RESOURCE_SIZE,
                  maxMemorySize = MAX_MEMORY_SIZE, sendPings = SEND_PINGS, pingsInterval = PINGS_INTERVALS,
                  gettingPeersInterval = GETTING_PEERS_INTERVAL, gettingTasksInterval = GETTING_TASKS_INTERVAL,
                  taskRequestInterval = TASK_REQUEST_INTERVAL, useWaitingForTaskTimeout = USE_WAITING_FOR_TASK_TIMEOUT,
                  waitingForTaskTimeout = WAITING_FOR_TASK_TIMEOUT, nodesSnapshotInterval = NODE_SNAPSHOT_INTERVAL,
                  addTasks = ADD_TASKS, maxSendingDelay = MAX_SENDING_DELAY,
                  useDistributedResourceManagement = USE_DISTRIBUTED_RESOURCE_MANAGEMENT):
        self._section = "Node {}".format( nodeId )

        estimated = NodeConfig.readEstimatedPerformance()
        if estimated == 0:
            estimated = ESTIMATED_DEFAULT

        ConfigEntry.createProperty( self.section(), "seed host", seedHost, self, "SeedHost" )
        ConfigEntry.createProperty( self.section(), "seed host port", seedPort, self, "SeedHostPort")
        ConfigEntry.createProperty( self.section(), "send pings", sendPings, self, "SendPings" )
        ConfigEntry.createProperty( self.section(), "pings interval", pingsInterval, self, "PingsInterval" )
        ConfigEntry.createProperty( self.section(), "client UUID", u"",   self, "ClientUid" )
        ConfigEntry.createProperty( self.section(), "getting peers interval",gettingPeersInterval, self, "GettingPeersInterval" )
        ConfigEntry.createProperty( self.section(), "getting tasks interval", gettingTasksInterval, self, "GettingTasksInterval" )
        ConfigEntry.createProperty( self.section(), "task request interval", taskRequestInterval, self, "TaskRequestInterval" )
        ConfigEntry.createProperty( self.section(), "use waiting for task timeout", useWaitingForTaskTimeout, self, "UseWaitingForTaskTimeout" )
        ConfigEntry.createProperty( self.section(), "waiting for task timeout", waitingForTaskTimeout, self, "WaitingForTaskTimeout" )
        ConfigEntry.createProperty( self.section(), "estimated perfomance", estimated,  self, "EstimatedPerformance" )
        ConfigEntry.createProperty( self.section(), "node snapshot interval", nodesSnapshotInterval,  self, "NodeSnapshotInterval" )
        ConfigEntry.createProperty( self.section(), "add tasks", addTasks, self, "AddTasks" )
        ConfigEntry.createProperty( self.section(), "maximum delay for sending task results", maxSendingDelay,  self, "MaxResultsSendingDelay" )
        ConfigEntry.createProperty( self.section(), "number of cores", numCores, self, "NumCores")
        ConfigEntry.createProperty( self.section(), "maximum resource size", maxResourceSize, self, "MaxResourceSize" )
        ConfigEntry.createProperty( self.section(), "maximum memory usage", maxMemorySize, self, "MaxMemorySize" )
        ConfigEntry.createProperty( self.section(), "use distributed resource management", useDistributedResourceManagement, self, "UseDistributedResourceManagement")


    ##############################
    def section( self ):
        return self._section

##############################
##############################
class AppConfig:

    CONFIG_LOADED = False

    ##############################
    @classmethod
    def managerPort( cls ):
        return MANAGER_PORT

    ##############################
    @classmethod
    def loadConfig( cls, cfgFile = CONFIG_FILENAME ):

        logger = logging.getLogger(__name__)

        if cls.CONFIG_LOADED:
            logger.warning("Application already configured")
            return None


        logger.info("Starting generic process service...")
        ps = ProcessService()
        logger.info("Generic process service started")

        logger.info("Trying to register current process")
        localId = ps.registerSelf()

        if localId < 0:
            logger.error("Failed to register current process - bailing out")
            return None

        cfg  = SimpleConfig( CommonConfig(), NodeConfig( localId ), cfgFile )

        cls.CONFIG_LOADED = True

        return AppConfig( cfg )

    ##############################
    def __init__( self, cfg ):
        self._cfg = cfg

    ##############################
    def getRootPath( self ):
        return self._cfg.getCommonConfig().getRootPath()

    def getOptimalPeerNum( self ):
        return self._cfg.getCommonConfig().getOptimalPeerNum()

    def getStartPort( self ):
        return self._cfg.getCommonConfig().getStartPort()

    def getEndPort( self ):
        return self._cfg.getCommonConfig().getEndPort()

    def getManagerAddress( self ):
        return self._cfg.getCommonConfig().getManagerAddress()

    def getManagerListenPort( self ):
        return self._cfg.getCommonConfig().getManagerListenPort()

    def getAppName( self ):
        return self._cfg.getCommonConfig().getAppName()

    def getAppVersion( self ):
        return self._cfg.getCommonConfig().getAppVersion()

    def getSeedHost( self ):
        return self._cfg.getNodeConfig().getSeedHost()

    def getSeedHostPort( self ):
        return self._cfg.getNodeConfig().getSeedHostPort()

    def getSendPings( self ):
        return self._cfg.getNodeConfig().getSendPings()

    def getPingsInterval( self ):
        return self._cfg.getNodeConfig().getPingsInterval()

    def getClientUid( self ):
        return self._cfg.getNodeConfig().getClientUid()

    def getGettingPeersInterval( self ):
        return self._cfg.getNodeConfig().getGettingPeersInterval()

    def getGettingTasksInterval( self ):
        return self._cfg.getNodeConfig().getGettingTasksInterval()

    def getTaskRequestInterval( self ):
        return self._cfg.getNodeConfig().getTaskRequestInterval()

    def getWaitingForTaskTimeout( self ):
        return self._cfg.getNodeConfig().getWaitingForTaskTimeout()

    def getUseWaitingForTaskTimeout( self ):
        return self._cfg.getNodeConfig().getUseWaitingForTaskTimeout()

    def getEstimatedPerformance( self ):
        try:
            return float( self._cfg.getNodeConfig().getEstimatedPerformance() )
        except:
            return float( ESTIMATED_DEFAULT )

    def getNodeSnapshotInterval( self ):
        return self._cfg.getNodeConfig().getNodeSnapshotInterval()

    def getAddTasks( self ):
        return self._cfg.getNodeConfig().getAddTasks()

    def getMaxResultsSendingDelay( self ):
        return self._cfg.getNodeConfig().getMaxResultsSendingDelay()

    def getNumCores ( self ):
        return self._cfg.getNodeConfig().getNumCores()

    def getMaxResourceSize ( self ):
        return self._cfg.getNodeConfig().getMaxResourceSize()

    def getMaxMemorySize ( self ):
        return self._cfg.getNodeConfig().getMaxMemorySize()

    def getUseDistributedResourceManagement( self ):
        return self._cfg.getNodeConfig().getUseDistributedResourceManagement()

    ##############################
    def changeConfig( self, cfgDesc , cfgFile = CONFIG_FILENAME, ):
        assert isinstance( cfgDesc, ClientConfigDescriptor )

        self._cfg.getNodeConfig().setSeedHost( cfgDesc.seedHost )
        self._cfg.getNodeConfig().setSeedHostPort( cfgDesc.seedHostPort )
        self._cfg.getNodeConfig().setNumCores( cfgDesc.numCores )
        self._cfg.getNodeConfig().setEstimatedPerformance( cfgDesc.estimatedPerformance )
        self._cfg.getNodeConfig().setMaxResourceSize( cfgDesc.maxResourceSize )
        self._cfg.getNodeConfig().setMaxMemorySize( cfgDesc.maxMemorySize )
        self._cfg.getCommonConfig().setRootPath( cfgDesc.rootPath )
        self._cfg.getCommonConfig().setManagerAddress( cfgDesc.managerAddress )
        self._cfg.getCommonConfig().setManagerListenPort( cfgDesc.managerPort )
        SimpleConfig( self._cfg.getCommonConfig(), self._cfg.getNodeConfig(), cfgFile, True )

    def __str__( self ):
        return str( self._cfg )

if __name__ == "__main__":

    c = AppConfig( 0 )
    print c
    c = AppConfig( 1 )
    print c
    c = AppConfig( 2 )
    print c
