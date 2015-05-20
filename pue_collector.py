from pysnmp.entity.rfc3413.oneliner import cmdgen
import time
import datetime as dt
import os
import sys
import ConfigParser
import logging

#Generic machineClass that will hold all the related information of the category of SNMP Host
class machineClass:
    def __init__(self,rootdir,filename,error_msg):
        if(checkIOError(rootdir,filename,error_msg)==0):
            Config=ConfigParser.ConfigParser()
            Config.read(rootdir+'/'+filename)
            self.ip_list=Config.items('hostname')
            self.oid_list=Config.items('oid')

#Generic snmpHost class. Every instance of this class will be individual SNMP Host.
class snmpHost:
    #initialize the instance with given parameters
    def __init__(self,ip_host,oid,stor_rootdir):
        self.ip=ip_host[0]
        self.hostname=ip_host[1]
        self.oid=list()
        self.desc=list()
        for oid_pair in oid:
            self.oid.append(oid_pair[0])
            self.desc.append(oid_pair[1])
        self.stor_rootdir=stor_rootdir

    #Listener function that fetches SNMP value for the host and write it into file.
    #Calling this function will trigger the data collection for the instance.
    def snmpListen(self):
        filename=self.getFileName()
        snmp_response=self.snmpGet()
        i=0
        while i<len(snmp_response):
            self.dataWrite(filename,snmp_response[i],i)
            i=i+1

    #Function that asks SNMP get from the instance.
    def snmpGet(self):
        cmdGen = cmdgen.CommandGenerator()
        errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData('public'),
        cmdgen.UdpTransportTarget((self.ip, 161)),
            *self.oid
            )
        #If there is an error in the response write log it and continue.
        if errorIndication:
            logging.debug('For IP address '+self.ip+': '+str(errorIndication))
        else:
            if errorStatus:
                print errorStatus
                logging.debug(errorStatus)
                a='%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex) - 1] or '?'
                    )
                sys.exit(a)
            else:
                return varBinds

    #Since each host will have separate file for data collection this function defines in which to save the collected result.
    def getFileName(self):
        current_date=dt.datetime.timetuple(dt.datetime.today())
        storage_path=self.stor_rootdir+'/'+str(current_date[0])+'/'+str(current_date[1])+'/'+str(current_date[2])
        if(os.path.exists(storage_path)==False):
            os.makedirs(storage_path)
        filename=str(current_date[0]) + str(current_date[1]) + str(current_date[2]) + ':' + self.hostname + ':' + 'SNMP' + '.txt'
        return storage_path + '/' + filename

    #Get the timestamp to be written in file with respect to SNMP response. It is measured in milliseconds and returned as string
    def getTimeStamp(self):
        now = time.time()
        localtime = time.localtime(now)
        milliseconds = '%03d' % int((now - int(now)) * 1000)
        return time.strftime('%Y%m%d%H%M%S', localtime) + milliseconds

    #Write the meaning of the SNMP query and SNMP response as well as timestamp when the response arrived
    def dataWrite(self, filename, snmp_response,i):
        f=open(filename,'a+')
        if(os.stat(filename).st_size == 0):
            f.write(self.desc[i] + ', ' + self.getTimeStamp() + ', ' + str(snmp_response[1]))
        else:
            f.write('\n' + self.desc[i] + ', ' + self.getTimeStamp() + ', ' + str(snmp_response[1]))
        f.close()

#The class that is designated for old model of APC rack PDU that does lack some of the features of new model.
#It inherits from snmpHost class but there are few discrepancies from generic snmpHost class.
#Each instance of this class is old model rPDU.
class oldPdu(snmpHost):

    #Old rack PDU's does not provide power information through SNMP.
    #We have to calculate the power provided using the amper load.
    #But it seems like below calculation is wrong and we have to calculate it through vector addition method.
    def snmpListen(self):
        #We are writing amps collected as well as the watts that we've calculated. Collected amps would be stored in file
        #created by getFileName2 whereas calculated Watts will be stored in file created by getFileName() function of snmpHost class.
        filename_amps=self.getFileName2()
        filename_watts=self.getFileName()
        ampers=list()
        i=0
        for oid in self.oid:
            snmp_response=self.snmpGet(oid)
            ampers.append(snmp_response[0][1])
            #We are writing amps collected as well as the watts that we've calculated
            self.dataWrite(filename_amps,snmp_response[0],i)
            i=i+1
        #This calculation turns out to be wrong. When calculating delta shaped 3 phase power it has to follow vector addition method
        #which I couldn't figure out during my implementation.
        watts=float(ampers[0])/10*117+float(ampers[1])/10*117+float(ampers[2])/10*117
        self.dataWrite2(filename_watts,watts)

    #Since there will be 3 amp value for 3 phase PDU this function has to be called 3 times which differs from dataWrite() of snmpHost class.
    def dataWrite2(self, filename, watts):
        f=open(filename,'a+')
        if(os.stat(filename).st_size == 0):
            f.write('EnergyInKWatts' + ', ' + self.getTimeStamp() + ', ' + str(watts))
        else:
            f.write('\n' + 'EnergyInKWatts' + ', ' + self.getTimeStamp() + ', ' + str(watts))
        f.close()

    #Create filename to store collected amp value.
    def getFileName2(self):
        current_date=dt.datetime.timetuple(dt.datetime.today())
        storage_path=self.stor_rootdir+'/'+str(current_date[0])+'/'+str(current_date[1])+'/'+str(current_date[2])+'/current'
        if(os.path.exists(storage_path)==False):
            os.makedirs(storage_path)
        filename=str(current_date[0]) + str(current_date[1]) + str(current_date[2]) + ':' + self.hostname + ':' + 'SNMP' + '.txt'
        return storage_path + '/' + filename

    #Old PDU supports only SNMP version 1, hence snmpGet() function needs to be different than any other hosts.
    def snmpGet(self,oid):
        cmdGen = cmdgen.CommandGenerator()
        errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData('public',mpModel=0),
        cmdgen.UdpTransportTarget((self.ip, 161)),
        cmdgen.MibVariable(oid),
            )
        if errorIndication:
            logging.debug('For IP address '+self.ip+': '+str(errorIndication))
        else:
            if errorStatus:
                a='%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex) - 1] or '?'
                    )
                sys.exit(a)
            else:
                return varBinds

#Global function to check if the requested IO path is possible.
def checkIOError(file_path,file_name,error_msg):
    try:
        f=open(file_path+'/'+file_name,'r')
    except IOError as (errno, strerror):
        logging.debug(error_msg)
        raise Exception, "%s"%sys.exc_info()[1],None
    f.close()
    return 0

#Function to retrieve the parameters from admin configuration file
def getAdminConfig():
    filename='admin_config.ini'
    error_msg='Admin config file not found'
    if(checkIOError(os.getcwd(),filename,error_msg)==0):
        Config=ConfigParser.ConfigParser()
        Config.read('admin_config.ini')
        config_rootdir=Config.get('rootdir','config_rootdir')
        stor_rootdir=Config.get('rootdir','stor_rootdir')
        ion_config=Config.get('config','ion')
        old_pdu_config=Config.get('config','pdu_old')
        new_pdu_config=Config.get('config','pdu_new')
        zone_pdu_config=Config.get('config','pdu_zone')
        zone3_pdu_config=Config.get('config','zone3_pdu')
    return config_rootdir,stor_rootdir,ion_config,old_pdu_config,new_pdu_config,zone_pdu_config,zone3_pdu_config

#Main caller function that runs the collection per each SNMP Host.
def getData():
    #Get admin config such as where to get related config files, where to store collected data and hostnames of collection objects
    config_rootdir,stor_rootdir,ion_config,old_pdu_config,new_pdu_config,zone_pdu_config,zone3PDU_config=getAdminConfig()

    #Create instance of generic machineClass that holds all the config informations related to old rack PDUs
    oldrPDUClass=machineClass(config_rootdir,old_pdu_config,'old pdu config not found')
    oldrPDUs=list()
    #Create instance of oldPdu per each old PDU according to the config in oldrPDUClass and save it in list oldrPDUs
    for ip_host_pair in oldrPDUClass.ip_list:
        oldrPDUs.append(oldPdu(ip_host_pair,oldrPDUClass.oid_list,stor_rootdir))

    #Create instance of generic machineClass that holds all the config informations related to zone PDUs
    zonePDUClass=machineClass(config_rootdir,zone_pdu_config,'zone pdu config not found')
    zonePDUs=list()
    #Create instance of snmpHost per each zone PDU according to the config in zonePDUClass and save it in list zonePDUs
    for ip_host_pair in zonePDUClass.ip_list:
        zonePDUs.append(snmpHost(ip_host_pair,zonePDUClass.oid_list,stor_rootdir))

    #Create instance of generic machineClass that holds all the config informations related to new PDUs
    newrPDUClass=machineClass(config_rootdir,new_pdu_config,'new pdu config not found')
    newrPDUs=list()
    #Create instance of snmpHost per each zone PDU according to the config in newrPDUClass and save it in list newrPDUs
    for ip_host_pair in newrPDUClass.ip_list:
        newrPDUs.append(snmpHost(ip_host_pair,newrPDUClass.oid_list,stor_rootdir))

    #Create instance of generic machineClass that holds all the config informations related to ION meters.
    ionMeterClass=machineClass(config_rootdir,ion_config,'ion meter config not found')
    ionMeters=list()
    #Create instance of snmpHost per each ion meter according to the config in ionMeterClass and save it in list ionMeters
    for ip_host_pair in ionMeterClass.ip_list:
        ionMeters.append(snmpHost(ip_host_pair,ionMeterClass.oid_list,stor_rootdir))

    #Create instance of generic machineClass that holds all the config informations related to Zone 3 zPDUs.
    #Zone PDU's at Zone 3 is different than Zone 1 and Zone 2. Again this has to be defined separately.
    zone3PDUClass=machineClass(config_rootdir,zone3PDU_config,'zone3 PDU config not found')
    zone3PDUs=list()
    #Create instance of snmpHost per each zone 3 PDU according to the config in zone3PDUClass and save it in list zone3PDUs
    for ip_host_pair in zone3PDUClass.ip_list:
        zone3PDUs.append(snmpHost(ip_host_pair,zone3PDUClass.oid_list,stor_rootdir))

    #For each of the above defined instances of snmpHost run snmpListen() function individually.
    for oldrPDU in oldrPDUs:
        oldrPDU.snmpListen()

    for newPDU in newrPDUs:
        newPDU.snmpListen()

    for zonePDU in zonePDUs:
        zonePDU.snmpListen()

    for zone3PDU in zone3PDUs:
       zone3PDU.snmpListen()

    for ionMeter in ionMeters:
        ionMeter.snmpListen()
        time.sleep(60)

#Main function
def main():
    #Define logging parameters and configure logger
    rootdir=os.getcwd()
    log_dir=rootdir+'/log'
    if(os.path.exists(log_dir)==False):
        os.makedirs(log_dir)
    log_file_name=log_dir+'/pue.log'
    logging.basicConfig(filename=log_file_name,level=logging.DEBUG,format='%(asctime)s %(message)s')

    #For continuous collection uncomment the following line and call the getData() function indefinitely
    #while 1:
    logging.debug('Collection started ')
    getData()
    logging.debug('Collection finished ')

if __name__=='__main__':
    main()
