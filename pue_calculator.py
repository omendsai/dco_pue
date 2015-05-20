import csv
import sys
import os
import ConfigParser
import logging
import datetime as dt

#Main function that averages the data recorded in the text file
def getSum(filename):
    f = open(filename, 'rt')
    watts=list()
    try:
        reader = csv.reader(f)
        for row in reader:
            try:
                watts.append(float(row[2]))
            except ValueError:
                logging.debug(filename)
                watts.append(0)
    finally:
        f.close()
    sum=0
    for watt in watts:
        sum=sum+watt
    try:
        avg=sum/len(watts)
    except ZeroDivisionError:
        logging.debug(filename)
        avg=0
    return avg

#Function to check if the file exists
def checkIOError(file_path, file_name,error_msg):
    try:
        f=open(file_path+'/'+file_name,'r')
    except IOError as (errno, strerror):
        logging.debug(error_msg)
        raise Exception, "%s"%sys.exc_info()[1],None
    f.close()
    return 0

#Function to get admin configuration file. Admin config file name is hardcoded and depending on cmnd parameter
#it may GET single value for corresponding key or retrieve all the keys of that section or all the key-value pairs in that section
def getAdminConfig(section,option,cmnd):
    filename='admin_config.ini'
    error_msg='Admin config file not found'
    response=None
    if(checkIOError(os.getcwd(),filename,error_msg)==0):
        Config=ConfigParser.ConfigParser()
        Config.read('admin_config.ini')
        if option==None and cmnd=='options':
            response=Config.options(section)
        elif option==None and cmnd=='items':
            response=Config.options(section)
        else:
            response=Config.get(section,option)
    return response

#Function that constructs full path and filename for each hostname list passed to this function
def getFileName(hostnames,directory):
    files=os.listdir(directory)
    file_names=list()
    for hostname in hostnames:
        for filename in files:
            a=directory+'/'+filename
            if os.path.isfile(a) and a.__contains__(hostname):
                file_names.append(a)
    return file_names

#Main function that fetches all files and send to function and retrieves the average.
#It first fetches the PDU names from their respective config files and send it to getFileName() function to construct filename.
#Then it sends the filenames to getSummary() function to receive each PDU's power consumption summary.
def getPowerSum(directory):
    #This part gets all the hostnames of the PDU's in the config files.
    zone1_zpdu_list=getAdminConfig('zone1_zpdu',None,'options')
    zone2_zpdu_list=getAdminConfig('zone2_zpdu',None,'options')
    zone3_zpdu_list=getAdminConfig('zone3_zpdu',None,'options')
    zone1_rpdu_list=getAdminConfig('zone1_rpdu',None,'options')
    zone2_rpdu_list=getAdminConfig('zone2_rpdu',None,'options')
    #Zone 3 Rack PDU's are still not yet finalized and in network yet.
 #   zone3_rpdu_list=getAdminConfig('zone3_rpdu',None,'options')
    ion_list=getAdminConfig('ion',None,'options')

    #This part constructs the file names for each of the hostnames in the config files
    zone1_zpdu_filenames=getFileName(zone1_zpdu_list,directory)
    zone2_zpdu_filenames=getFileName(zone2_zpdu_list,directory)
    zone3_zpdu_filenames=getFileName(zone3_zpdu_list,directory)
    zone1_rpdu_filenames=getFileName(zone1_rpdu_list,directory)
    zone2_rpdu_filenames=getFileName(zone2_rpdu_list,directory)
    ion_filenames=getFileName(ion_list,directory)

    #This part computes the average of power per each class of PDU. zoneX_Ypdu_list variable contains the tuple of hostname and power average
    zone1_rpdu_list,zone1_rpdu_sum=getSummary(zone1_rpdu_filenames,zone1_rpdu_list)
    zone2_rpdu_list,zone2_rpdu_sum=getSummary(zone2_rpdu_filenames,zone2_rpdu_list)
    zone1_zpdu_list,zone1_zpdu_sum=getSummary(zone1_zpdu_filenames,zone1_zpdu_list)
    zone2_zpdu_list,zone2_zpdu_sum=getSummary(zone2_zpdu_filenames,zone2_zpdu_list)
    zone3_zpdu_list,zone3_zpdu_sum=getSummary(zone3_zpdu_filenames,zone3_zpdu_list)
    ion_list,ion_sum=getSummary(ion_filenames,ion_list)

    #This part handles the display output.
    displayPower('Total DCO Power',ion_sum,ion_list,0)
    displayPower('Total Power on Zone 1',zone1_zpdu_sum,zone1_zpdu_list,1)
    displayPower('Total Power on Zone 2',zone2_zpdu_sum,zone2_zpdu_list,1)
    displayPower('Total Power on Zone 3',zone3_zpdu_sum,zone3_zpdu_list,1)
    displayPower('Total Power of Rack PDU on zone 1',zone1_rpdu_sum/1000,zone1_rpdu_list,2)
    displayPower('Total Power of Rack PDU on zone 2',zone2_rpdu_sum/1000,zone2_rpdu_list,2)

    #This part computes the PDU
    pue_rpdu,pue_zpdu=getPue(zone1_zpdu_sum/10, zone2_zpdu_sum/10, zone3_zpdu_sum/10, zone1_rpdu_sum,zone2_rpdu_sum,ion_sum)
    return pue_rpdu,pue_zpdu

#Function that defines the date of which the PUE needs to be calculated.
#If there was no argument passed to the main function this function is used to determine the date
#The days= parameter in timedelta function below is used which date's folder to calculate PUE from current date.
#If days=0 it means today's PUE and days=1 means yesterday's PUE.
def getDate():
    stor_rootdir=getAdminConfig('rootdir','stor_rootdir','get')
    current_date=dt.date.timetuple(dt.date.today()-dt.timedelta(days=0))
    datestamp=str(current_date[0])+'/'+str(current_date[1])+'/'+str(current_date[2])
    directory=stor_rootdir+'/'+datestamp
    return directory, current_date, stor_rootdir

#Generic display output function. lvl parameter is used to define the indentation in display
#msg parameter contains the display message and sum of the PDU powers and lst contains list of PDU hostname and power average pair.
def displayPower(msg,sum,lst,lvl1):
    str1='\t\t\t\t'
    print str1*lvl1+msg+': '+str(sum)
    for pdu in lst:
        print str1*(lvl1+1)+'->'+str(pdu[0])+': '+str(pdu[1])

#Function that combines all the similar device's average power.
#It also saves the average power for each device as tuple of hostname and average power.
def getSummary(filenames,hostname):
    power_list=list()
    total_sum=0
    i=0
    for filename in filenames:
        sum=getSum(filename)
        power_list.append([hostname[i],sum])
        total_sum=total_sum+sum
        i=i+1
    return power_list,total_sum

#Function that computes PUE.
def getPue(zone1_zpdu_sum,zone2_zpdu_sum,zone3_zpdu_sum,zone1_rpdu_sum,zone2_rpdu_sum,ion_sum):
    total_zpdu_power=zone1_zpdu_sum+zone2_zpdu_sum+zone3_zpdu_sum
    total_rpdu_power=zone1_rpdu_sum+zone2_rpdu_sum
    pue_zpdu=ion_sum/total_zpdu_power
    total_rpdu_power=total_rpdu_power/1000
    try:
        pue_rpdu=ion_sum/total_rpdu_power
    except ZeroDivisionError:
        logging.debug('zero division')
        pue_rpdu=0
    return pue_rpdu,pue_zpdu

#Function that writes computed PUE in a text file.
def pueWrite(pue,msg,current_date):
    filename=str(current_date[0])+'='+str(current_date[1])+'=PUE.txt'
    datestamp=str(current_date[0])+'/'+str(current_date[1])+'/'+str(current_date[2])
    match_str=msg+datestamp
    file_path_name=os.getcwd()+'/'+filename
    if(os.path.exists(file_path_name)==1):
        if(os.stat(file_path_name).st_size != 0):
            f=open(filename,'r')
            reader = csv.reader(f)
            for row in reader:
                if(row[0]==match_str):
                    logging.debug('duplicate record for date:'+datestamp)
                    f.close()
                    sys.exit(1)
    f=open(filename,'a+')
    if(os.stat(file_path_name).st_size == 0):
        f.write(msg+ datestamp +  ', ' + str(pue))
    else:
        f.write('\n' + msg+ datestamp +  ', ' + str(pue))
    f.close()

#Main function.
#It can accept arguments when it is called from console.
#The argument should be of format YYYY/MM/DD to see the PUE for that specific date
def main(argv):
    directory,current_date,stor_rootdir=getDate()
    if len(sys.argv[1:])!=0:
        directory=stor_rootdir+'/'+str(sys.argv[1])
    rootdir=os.getcwd()
    log_dir=rootdir+'/log'
    if(os.path.exists(log_dir)==False):
        os.makedirs(log_dir)
    log_file_name=log_dir+'/pue_sum.log'
    logging.basicConfig(filename=log_file_name,level=logging.DEBUG,format='%(asctime)s %(message)s')
    pue_rpdu,pue_zpdu=getPowerSum(directory)
    pueWrite(pue_zpdu,'PUE for Zone PDU: ',current_date)
    pueWrite(pue_rpdu,'PUE for Rack PDU: ',current_date)

if __name__=='__main__':
    main(sys.argv[1:])
