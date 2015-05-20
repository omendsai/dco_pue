from pysnmp.entity.rfc3413.oneliner import cmdgen
import ConfigParser
import socket

#Function that asks SNMP get from the host.
def snmpGet(ip,oid):
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
    cmdgen.CommunityData('public'),
    cmdgen.UdpTransportTarget((ip, 161)),
        oid
        )
    if errorIndication:
            print errorIndication,ip,oid
            # sys.exit(errorIndication)
    else:
            if errorStatus:
                a='%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex) - 1] or '?'
                    )
                print a,ip,oid
                #sys.exit(a)
            else:
                return varBinds

#Function that asks for current load in amps for the specific breaker. Breaker number is passed as parameter n and used to construct the OID
def getBreakerAmps(n,hostname):
    base='1.3.6.1.4.1.318.1.1.15.4.2.3.1.5.'
    if n.__contains__('0'):
        if n.index('0')==0:
            n=n[1:]
    oid=base+n
    ip=getIp(hostname)
    return snmpGet(ip,oid)[0][1]

#Function to ask for total zPDU power in kW.
def getZonePower(hostname):
    ip=getIp(hostname)
    oid='1.3.6.1.4.1.318.1.1.15.3.4.3.0'
    return snmpGet(ip,oid)[0][1]

#Function that ask for zPDU power factor
def getZonePowerFactor(hostname):
    ip=getIp(hostname)
    oid='1.3.6.1.4.1.318.1.1.15.3.4.5.0'
    return snmpGet(ip,oid)[0][1]

#Function that ask for zPDU voltage
def getZoneVoltage(ip):
    oid='1.3.6.1.4.1.318.1.1.15.2.3.0'
    return snmpGet(ip,oid)[0][1]

#Function that ask for ION meter power in kW
def getIonPower(ip):
    oid='1.3.6.1.4.1.10439.22.0'
    return snmpGet(ip,oid)

#Function that calculates the sum of total power listed in the power_list parameter
def getPowerSum(power_list):
    power_sum=0
    for power in power_list:
        power_sum=power_sum+power
    return power_sum

#Generic function to display the power per each zone PDU and its respective rack PDU's
def displayOutput(zpdu_name,rpdu_name,breakers,breaker_power,rpdu_power):
    print '\t'+'At zone PDU '+zpdu_name+' Breakers: '+str(breakers[0])+','+str(breakers[1])+','+str(breakers[2])+' connected to rack PDU: '+rpdu_name
    print '\t\t'+'Power at breaker: '+str(breaker_power)+' Watss'
    print '\t\t'+'Power at rack PDU: '+str(rpdu_power)+ ' Watts'

#Function that fetches IP address for specific hostname. Assumption is that every hostname will have .pdl.cmu.local suffix.
def getIp(hostname):
    hostname=hostname+'.pdl.cmu.local'
    addr = socket.gethostbyname(hostname)
    return addr

#Function that asks for power load at rack PDU in Watts
def getComputingPower(hostname):
    ip=getIp(hostname)
    oid='1.3.6.1.4.1.318.1.1.12.1.16.0'
    power=snmpGet(ip,oid)[0][1]
    return power

#Function that calculates breaker power using the current load in amps and return the power in Watt at that breaker
def getBreakerPower(breakers,voltage,zpdu_name):
    amps=list()
    for breaker in breakers:
        amp=getBreakerAmps(breaker,zpdu_name)
        amps.append(amp/10)
    breaker_power=amps[0]*voltage+amps[1]*voltage+amps[2]*voltage
    return breaker_power

#Main function that queries each breaker of the passed zone PDU and determine the load in Watts
#It also sends SNMP query to each rack PDU specified and send both the outputs to the display for comparison
def getPower(zpdu_name):
    zpdu_breaker_powers=list()
    zpdu_computing_powers=list()
    zone_power=float(getZonePower(zpdu_name))/10
    voltage=getZoneVoltage(getIp(zpdu_name))
    Config=ConfigParser.ConfigParser()
    Config.read('powerdiff.ini')
    power_nodes=Config.options(zpdu_name)
    print '\n'+'For ZonePDU '+zpdu_name+' Total power by SNMP: '+str(zone_power)+' kW'
    #For each rack PDU determine which breakers it has connected using power_diff.ini.
    #Determine the power for each rack PDU on breaker level
    #Also ask for rack PDU output power through SNMP
    for power_node in power_nodes:
        breaker_string=Config.get(zpdu_name,power_node)
        breakers=(breaker_string[:2],breaker_string[3:5],breaker_string[6:8])
        breaker_power=getBreakerPower(breakers,voltage,zpdu_name)
        if power_node.__contains__('p')==1:
            node_power=getComputingPower(power_node)
            zpdu_breaker_powers.append(breaker_power)
            zpdu_computing_powers.append(node_power)
            displayOutput(zpdu_name,power_node,breakers,breaker_power,node_power)
    zpdu_power_sum=getPowerSum(zpdu_computing_powers)
    zpdu_breaker_power_sum=getPowerSum(zpdu_breaker_powers)
    #Display the results
    print 'For ZonePDU '+zpdu_name+' Total computing power by SNMP: '+str(zpdu_power_sum)+' W'
    print 'For ZonePDU '+zpdu_name+' Total breaker power by calculation: '+str(zpdu_breaker_power_sum)+' W'

#Main function
#It reads from powerdiff.ini and for each Zone PDU in powerdiff.ini it calls getPower function.
def main():
    Config=ConfigParser.ConfigParser()
    Config.read('powerdiff.ini')
    sections=Config.sections()
    for section in sections:
        getPower(section)


if __name__=='__main__':
    main()
