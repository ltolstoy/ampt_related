#!/home/ltolstoy/anaconda/bin/python2.7
"""
Script to read and process xxxx_bxx.log files
v1 - 5/15/17 from_zone="UTC", to_zone - comes from settings_pic.ini file (line 559)
v2 - 5/17/17 - read all settings (and name and timezone) from just one file settings.ini
v3 - 5/18/17 - filter out case when responce timestamp is too far from request timestamp (case of stalled, or stuck, data)
v4 - 5/19/17 - add PowerDissipation columnt into _electrical.csv (I1*U1 +I2*U2-Iout*Uout)
v5 - 6/12/17 - add filter for unreadable chars in ED response
v6 - 6/29/17 - add columns for location, date, and Pout
v7 - 7/5/17 - add email alert to Michelle in case we see Vout>999V in data. Add time, mac, location.
    Use sendgrid API as shown in sendgrid.com/docs/Integrate/Code_Examples/v2_Mail/python.html
v8 - 7/10/17 - add date+time into one column for Kengoo 
v9 - 7/19/17 - change date format for mysql loading, to yyyy-mm-dd 
v10 - 7/31/17 - modified cond_check, to eliminate unreadable characters (line 551)
"""

# import pdb
#import matplotlib.pyplot as plt
import datetime, time
import csv, os
import sys
#import numpy as np
import argparse, ConfigParser
from pathlib2 import Path
from dateutil import tz


def mail_notification_sendgrid(subject, text):
    """It sends email to several people with warning
    subject - like "Bad rfstatus found at Canadian_solar_305 at ip=10.8.4.22"
    text - body, like 
    "Body"
    https://stackoverflow.com/questions/31936881/sendgrid-python-library-and-templates
    """
    import smtplib
    from email.mime.text import MIMEText
    # ltolstoy@ampt.com# John.Daharsh@ampt.com, Corey.Sauer@ampt.com,Lawrence.Coburn@ampt.com
    msg = MIMEText(text)
    me = "ltolstoy@ampt.com"
    you = [ "ltolstoy@ampt.com","Michelle.Propst@ampt.com"]

    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = ",".join(you)
    s = smtplib.SMTP('smtp.sendgrid.net')
    s.login('apikey', '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')
    s.sendmail(me, you, msg.as_string())
    s.quit()

def get_list_of_items(block, p_to_logs):
    '''
    block = '302','303',
    p_to_logs - path to folder where log is, like /media/win_EON/data_log/canadian_solar/tmp/
    p_to_struc - Here we find a file structure_xxx.xml, and get list_of_macs, sn, string_name from it
    '''
    import xml.etree.ElementTree as ET
    p_to_struc = os.path.abspath(os.path.join(p_to_logs, os.pardir)) # gets 1 level up, to /media/win_EON/data_log/canadian_solar/
    name_str = '/structure_'+block+'.xml'
    p = p_to_struc + name_str #full path, including file name
    if os.path.exists(p):
        tree = ET.parse(p)
        root = tree.getroot()
        macs = [] #mac addresses
        sns = []  #serial numbers
        stnames =[]  #string names "02.01.01-1"
        for m in root.iter('String'):
            a = m.get('name')
            stnames.append(''.join(a))
        for m in root.iter('Converter'):
            a = m.get('mac')
            macs.append(''.join(a)) #otherwise doesn't work
            b = m.get('sn')
            sns.append(''.join(b))
        print "getting items from structure_"+block+".xml: got " + str(len(macs)) + " items"
        return macs,sns,stnames
    else:
        print p + "doesnt exist, can work without structure.xml. Exiting now"
        sys.exit()

def csv_writer(data, data_gw, path, start_time, finish_time, p_to_csv):
    '''
    Write data to a CSV file path
    Make header, then form the line, which includes all SS info and all macs
    data_gw is 4x1179
    Outputs data in time range , from start_time till finish_time (1122 -1923 ex)
    path - fill path with fname, 
    p_to_csv- path to folder only (I weill add filename later) - for one last line
    '''

    try:  #removing exisitng csv file if it exists
        os.remove(path)
    except OSError:
        pass    
    p_to_lastline = p_to_csv + "last_line.csv" #to hold last line only
    try:  #removing exisitng csv file if it exists
        os.remove(p_to_lastline)
    except OSError:
        pass
    
    [d1,d2,d3] = size(data)  # find out dimensions 22x83x1179 d1=22, d2=83, d3=1179
    d1=d1-2  #for this version i use only 20 elements
    gw_header = ['time_UTC', 'msec', 'chnl', 'antn']
    device_header = ['MAC',\
    'chnl','bnch','slot','mpp','mdl',\
    'VOut','Vin1','IOut','Vin2',\
    'Text','Iin2','Iin1','Ref',\
    'Goff','Grss','Eoff','Erss',\
    'OV', 'OC'] #22-2 items
    #header = gw_header + device_header * d2 #making really long header,3+22*83 = 1497
    #making header line with changed MAC number
    header = gw_header
    for i in xrange(d2):  #for each mac
        tmp = device_header
        tmp[0] = 'MAC-' + str(i+1)
        header.extend(tmp)
        for c in xrange(d3):  #for each SC
            #removing 2 columns from data: string itself and 'midstring'
            data[c][i].pop(1)  #remove string_itself, which is 1st elem
            data[c][i].pop(1)   #now remove "midstring", which became 1st el (was 2nd before)
            
    #at this point data conveterd from 22x46x1111 to 20x46x1111
    print "csv_writer: start writing file " + path
    
    with open(path, "wb") as csv_file:
        wr= csv.writer(csv_file, delimiter=',')
        wr.writerow(header)  #putting header in place
        for c in range(0,d3-1):   #making 1179 lines, skipping last (empty) line
            line = ['']*(4 + d1 * d2) #making empty array of string, *83 devices
            line[0:4] = [ time.strftime('%H:%M:%S',  time.gmtime(data_gw[c][0])), data_gw[c][1], data_gw[c][2], data_gw[c][3] ]
            for i in range(0,d2): #counting devices,
                for j in range(0,d1): #counting pos in 0-20 params of MAC
                    try:
                        line[4 + i*d1 + j] = data[c][i][j]  # adding data string for all devices

                    except IndexError:
                        print "csv_writer: error in line forming: c,i,j:"
                        print c,i,j
            # at this point done with line formation
            wr.writerow(line)
            #addition 4/15/16 - save last line in separate file
            '''if c == d3-2:  #-2 bcs d3-1 is never reached, its not included into the range
                with open(p_to_lastline, "wb") as csv_file:
                    wlast= csv.writer(csv_file, delimiter=',')
                    wlast.writerow(header)
                    wlast.writerow(line)'''


def csv_writer_short_michelle(data, data_gw, path,list_of_macs, sns, stnames, dt2):
    '''
    Write data to a CSV file path
    Make header, then form the line, which includes all SS info and all macs
    data_gw is 4x1179
    Outputs data in time range , from start_time till finish_time (1122 -1923 ex)
    path - /media/win_EON/data_log/canadian_solar/170629/20170629_electrical.csv full path with file name
    list_of_macs - list of mac addresses
    sns -  list of serial numbers
    stnames -  station names, aka locations
    dt2 - date to put in the column, was part of filename , ex:20170629_301
        Used in the mail_notification too
    '''
    import pandas as pd

    try:  # removing existing csv file if it exists
        os.remove(path)
    except OSError:
        pass
    [d1, d2, d3] = size(data)  # find out dimensions 22x83x1179 d1=22, d2=83, d3=1179
    #gw_header = ['SC_time_UTC', 'SC_msec', 'SC_channel', 'SDAG_antenna_config']
    '''['MAC',                         #'String','Midstring or SPT',\
    'chnl','bnch','slot','mpp','mdl',\
    'VOut','Vin1','IOut','Vin2',\
    'Text','Iin2','Iin1','Ref',\
    'Goff','Grss','Eoff','Erss',\
    'OV', 'OC'] #22-2 items '''
    dt1 = dt2.split('_')[0]  #from 20170629_301 we need just 1st part
    #dt = dt1[4:6]+'/'+dt1[6:]+'/'+dt1[:4]          # convert to 06/29/2017
    dt = dt1[:4] + '-' + dt1[4:6] + '-' + dt1[6:]   # convert to 2017-06-29
    header = ['Mac', 'SN', 'Time', 'Date', 'Date_Time','Location', 'Vin1', 'Vin2','Vout', 'Iin1','Iin2','Iout', 'Text', 'Pdiss', 'Pout']
    #df = pd.DataFrame(data) #converting from 3d list of lists into dataframe
    #df.T #transpone, now rows are 175 units, columns are 263 sc
    print "csv_writer: start writing file " + path
    flag = 0 # flag to trigger allert if Vout was fount to be >950V. Send email if so.
    vlim = 999 # Alarm if Vout found to be higher than this
    alarm_time = [] #list of times when it was found
    alarm_locs = [] #list of lications where alert condition happened
    alarm_mac = []  #list of macs with the alert condition
    with open(path, "wb") as csv_file:
        wr = csv.writer(csv_file, delimiter=',')
        wr.writerow(header)  # putting header in place
        for macnum in xrange(d2):  # countig units or macs 0..175
            for sc in xrange(d3):   #counting sc and time 0..363
                if data[sc][macnum][0] != '' :  #if record exists for this time
                    if len(data[sc][macnum]) == 20:
                        line = [''] * len(header)  # making empty  string, 9 positions
                        line[0] = data[sc][macnum][0]     #mac
                        line[1] = sns[list_of_macs.index(data[sc][macnum][0])] # SN corresponding to current MAC
                        line[2] = time.strftime('%H:%M:%S',  time.gmtime(data_gw[sc][0])) #time from UTC
                        line[3] = dt                    # date
                        line[4] = dt + ' ' + line[2]    # date and time
                        line[5] = stnames[list_of_macs.index(data[sc][macnum][0])] # SN corresponding to current MAC
                        line[6] = data[sc][macnum][7]   # Vin1
                        line[7] = data[sc][macnum][9]   # Vin2
                        line[8] = data[sc][macnum][6]   # Vout
                        line[9] = data[sc][macnum][12]  # Iin1
                        line[10] = data[sc][macnum][11]  # Iin2
                        line[11] = data[sc][macnum][8]   # Iout
                        line[12] = data[sc][macnum][10]  # Text
                        line[13] = str(round(float(line[6])*float(line[9]) +
                            float(line[7]) * float(line[10]) -
                            float(line[8]) * float(line[11]),3 )) # Pdiss = Vin1*Iin1+Vin2*Iin2-Vout*Iout
                        line[14] = str(round(float(line[8]) * float(line[11]),3))  # Pout = Vout*Iout
                        if float(data[sc][macnum][6]) >vlim: #Vout > 950V
                            flag = 1
                            alarm_time.append(line[2])  #add time when alert happened
                            alarm_locs.append(line[5])  #add location of alert
                            alarm_mac.append(line[0])   # add mac
                    elif len(data[sc][macnum]) == 22: #shift by 2
                        line = [''] * len(header)  # making empty  string, 9 positions
                        line[0] = data[sc][macnum][0]  # mac
                        line[1] = sns[list_of_macs.index(data[sc][macnum][0])]  # SN corresponding to current MAC
                        line[2] = time.strftime('%H:%M:%S', time.gmtime(data_gw[sc][0]))  # time from UTC
                        line[3] = dt                    # date
                        line[4] = dt + ' ' + line[2]    # date and time
                        line[5] = stnames[list_of_macs.index(data[sc][macnum][0])]  # SN corresponding to current MAC
                        line[6] = data[sc][macnum][9]   # Vin1
                        line[7] = data[sc][macnum][11]  # Vin2
                        line[8] = data[sc][macnum][8]   # Vout
                        line[9] = data[sc][macnum][14]  # Iin1
                        line[10] = data[sc][macnum][13]  # Iin2
                        line[11] = data[sc][macnum][10]  # Iout
                        line[12] = data[sc][macnum][12]  # Text
                        line[13] = str(round(float(line[6]) * float(line[9]) +
                            float(line[7]) * float(line[10]) -
                            float(line[8]) * float(line[11]), 3))  # Pdiss = Vin1*Iin1+Vin2*Iin2-Vout*Iout
                        line[14] = str(round(float(line[8]) * float(line[11]), 3))  # Pout = Vout*Iout
                    if float(data[sc][macnum][8]) > vlim: #Vout > 950V
                        flag = 1
                        alarm_time.append(line[2])  # add time when alert happened
                        alarm_locs.append(line[5])  # add location of alert
                        alarm_mac.append(line[0])   # add mac
                    # at this point done with line formation
                    wr.writerow(line)
    if flag == 1:  # Vout was found to be >950V at least once
        print("Double FET failure alert! Sending emails...")
        mail_notification_sendgrid("Found Possible Double FET failure at " + path + " during csv processing",
                                   "Vout in file " +path +
                                   " was found to exceed the limit value of " +
                                   str(vlim) + "V.\n It is probably double FET failure, please turn off modules on the site!\n Thanks.\n"+
                                    "\n Log time when it happened: " + str(alarm_time[0])+
                                   "\n Mac (at least): " + str(alarm_mac[0])+
                                   "\n Location as per structure file (at least): "+ str(alarm_locs[0])
                                   )

def fill_info(s):  
    # gets whole line of info from device, returns separated strings
#and f = "Midstring" if Midstring, "SPT" if SPT (by 1st char of MAC we can decide)
#Short format:
    # |00FEAA|5A2FC454_92E4_2873C000006E_481374260A00710C2203010000003A00FFA05F19
    # 00FEAA: Bunch 	00
	#      GW Offset    FE
	#      GW RSSI        CA
    # 5A2FC454 UTC		
    # 92E4	Mix of channel, SlotID, mmp Flag, module flag
    # 2873C000006E	mac
    # 4813_7426_0A00_710C_2203_0100_0000_3A00_FF_A0_5F_19:
    # 4813 - Vout
    # 7426 - Pin_or_Vin1
    # 0A00 - Iout, =val if val >0 and <=32767, = val -65536 if val>32767
    # 710C - Vin_or_Vin2
    # 2203 - T of pcb
    # 0100 - Iin_or_Iin2 , =val if val >0 and <=32767, = val - 65536 if val>32767
    # 0000 - T prepare package (for Midstring) or Grn (Amp, for SPT) 
    # 3A00 - network flag for MS, Ref for SPT
    # FF    - Ed offset
    # A0    - Ed RSSI
    # 5F    - Over current
    # 19    - Over voltage
    m = s[20:32] # Midstring has 1st char 2,4,9, SPT has 3 or 6
    dlina = 18+1+1+1+1 #+1 for string, +1 for sign SPT or Midstring, mpp , module
    out = ['']*dlina  # empty output 22 positions, +1 for string itself
    if m[0] == '2' or m[0] == '4' or m[0] == '5' or m[0] == '9': #if it's Midstring
        f = "Midstring" 
    else:
        f = "Midstring"
    if len(s) == 72 and s[0] != '*':
        out[0] = s[20:32] # MAC of converter, 12 bytes
        out[1] = '' #=s saving string itself! Disabled in this version
        out[2] = f
        [out[3], out[5], out[6], out[7]] = mix(s[16:20])   #unmixing mix chnl,tslot,mpp, module
        out[4] = bnch(s[1:3]) # BunchID, str or "", converted to decimal and to string
        if f == "Midstring":
            [out[4+4], out[5+4], out[7+4]] = fill_voltages_ms(s[32:36], s[36:40], s[44:48]) #Vout, Vin1, Vin
        else:
            [out[4+4], out[5+4], out[7+4]] = fill_voltages_spt(s[32:36], s[36:40], s[44:48]) #Vout, Vin1, Vin
        # Vout ,1/50 for midstring, 1/500 for SPT
        # Vin1 ,1/50 for midstring, Pin = 1/100 for SPT
        # Vin,  1/50 for midstring, Vin2 = 1/500 for SPT
        [out[6+4], out[8+4], out[9+4], out[10+4], out[11+4]] = fill_rest(s[40:44],s[48:52],s[52:56],s[56:60],s[60:64])
        # Iout,T of PCB,Iin or Iin2, Iin1 or GRN, Network flag or Ref.
        try:
            t = int(s[3:5],16)
            out[12+4] = str(t) if (t>= 0 and t <=127) else str(t-256) #GW offset, if [0-127] then val, else 256-val
        except ValueError:
            out[12+4] = ''
        try:
            t = int(s[5:7], 16)
            out[13+4]  = str(t) if (t>= 0 and t<= 127) else str(t-256) #GW RSSI, 256-val. <0 dB
        except ValueError:
            out[13+4] = ''               
    
        try:
            t1 = int(s[64:66],16)  #integer
            out[14+4] = str(t1) if (t1>= 0 and t1 <=127) else str(t1-256) #ED offset, if [0-127] then val, else 256-val
        except ValueError:
            out[14+4] = ''
        try:
            t1 = int(s[66:68], 16)
            out[15+4] = str(t1) if (t1>= 0 and t1 <=127) else str(t1-256) # ED RSSI, <0 dB
        except ValueError:
            out[15+4] = ''
        try:    
            out[16+4] = str(int(s[68:70],16)) #OV overvoltage
        except ValueError:
            out[16+4] = ''
        try:
            out[17+4] = str(int(s[70:72],16)) #OC overcurrent
        except ValueError:
            out[17+4] = ''
        # At this point the whole string is formed, so return it
        return out # returning splitted data
    else:
        return ['']*dlina  # if lenght if string is not standard, return empty string
            
    
            
    
def fill_rest(iout,tpcb,iin,iin1,nf):
    # Gets Iout, T of PCB, Iin or Iin2, Iin1 instead of Tprep, Network flag.
    # Returns Iout, A. 1/1000, or ""
    # T of PCB, 1/100, or ""
    # Iin or Iin2, 1/1000, or ""
    # Iin1, or GRN, A for SPT. , or ""
    # Network flag. 50 or 58, , or ""
    try:
	t1 = int(swap(iout),16)
	t = t1 if (t1>= 0 and t1 <=32767) else str(t1 - 65536)
        iout_out = str(float( t )/1000)
    except ValueError: 
        iout_out = ''
    try:
        t1 = float(int(swap(tpcb),16))  
        t = t1 if (t1>= 0 and t1 <=32767) else (t1 - 65536 )
        tpcb_out = str(t/100)
    except ValueError: 
        tpcb_out = ''
    try:
        t1 = int(swap(iin),16)
        t = t1 if (t1>= 0 and t1 <=32767) else str(t1 - 65536 )
        iin_out = str(float( t )/1000)
    except ValueError: 
        iin_out = ''
    
    try:
        t1 = int(swap(iin1),16)
        t = t1 if (t1>= 0 and t1 <=32767) else str(t1 - 65536 )
        iin1_out = str(float( t )/1000)
    except ValueError: 
        iin1_out = ''
    try:
        nf_out = str(int( swap(nf),16 ) )
    except ValueError: 
        nf_out = ''
    return iout_out,tpcb_out,iin_out,iin1_out,nf_out


def fill_voltages_ms(vout,vin1, vin):
    # for Midstring, Gets 3 strings (Vout, Vin1, Vin), swaps and converts to float, if possible. Otherwise returns ""
    try:
        vout_out = str(float(int(swap(vout),16))/50) # Vout ,1/500 for midstring, 1/50 for SPT
    except ValueError: 
        vout_out = ''
    try:
        vin1_out = str(float(int(swap(vin1),16))/50)   # Vin1 , 1/50 midstring, Pin = 1/100 for SPT     
    except ValueError: 
        vin1_out = ''   
    try:
        vin_out = str(float(int(swap(vin),16))/50)     # Vin 1/50 for midstring, Vin2 = 1/500 for SPT   
    except ValueError: 
        vin_out = '' 
    return vout_out, vin1_out , vin_out
    
def fill_voltages_spt(vout, pin, vin):
    # for SPT, Gets 3 strings (Vout, Vin1, Vin), swaps and converts to float, 
    #to string, if possible. Otherwise returns ""
    try:
        vout_out = str(float(int(swap(vout),16))/50) # Vout ,1/500 for midstring, 1/50 for SPT
    except ValueError: 
        vout_out = ''
    try:
        pin_out = str(float(int(swap(pin),16))/50)  # Vin1 , 1/50 midstring, Pin = 1/100 for SPT      
    except ValueError: 
        pin_out = ''   
    try:
        vin_out = str(float(int(swap(vin),16))/50)   #Vin 1/50 for midstring, Vin2 = 1/500 for SPT     
    except ValueError: 
        vin_out = '' 
    return vout_out, pin_out , vin_out    
    
    
def swap(s):
    # swaps bytes of the string ABCD -> CDAB
    # returns string
    tmp = list(s)
    tmp[0], tmp[2] = tmp[2], tmp[0]  #swapping elements
    tmp[1], tmp[3] = tmp[3], tmp[1]
    return ''.join(tmp)  # joining all elements of the list, making it string
    
def mix(tmp)    :
    #gets  str which is mix of ms, SlotID, flag
    # returning Slot id, ms, mpp, module, or '' if error
    tmp0 = swap(tmp)  # string    
    #tslot 
    try:
        tmp1 = int(tmp0,16) # converting string to int
        tslot2 = tmp1 >> 10 
        p = int('0xF',16)
        tslot = str(tslot2 & p) #making bitwise operations, getting int
         # channel
        p = int('0xFF',16)
        chnl = tmp1 & p #making bitwise operations, getting int
        #chnl = str((chnl + 4)/10) #converting from int to string, making it in range 1-26 
        chnl = str(chnl)
        # mpp flag
        tmp2 = tmp1 >> 14 
        p = 1 #int('0x1',16)
        mpp = str(tmp2 & p )#making bitwise operations, getting int; converting from int to string  
        # module
        tmp2 = tmp1 >> 15 
        p = 1 #int('0x1',16)
        module = str(tmp2 & p) #making bitwise operations, getting int; converting from int to string 
    except ValueError:
        tslot = ''
        mpp = ''
        module = ''
        chnl = ''
    return chnl,tslot,mpp, module 
    
    
def bnch(s):
    # gets string, return BunchID string, or "" if can't
    try:
        tmp1 = int(s,16) # converting string to int 
        return tmp1
    except ValueError:
        return ''
    

def size(array):
    # gets 3d array, return it's dimensions: AxBxC -> [1:C][1:B][1:A]
    a = len(array[0][0])
    b = len(array[0])
    c = len(array)
    return a,b,c
    
def progress(val1):
    #    Gets a float value, and prints it if % is mod of 10
    z=1e5
    val = val1*100/z
    if int(val) % 10 == 0:
        #sys.stdout.write("\r%d%%" % int(pos*100/pos_eof)) #\r progress indicator
        print "\r" + str(int(val)) + "%", 
        # ','  here to stay in the same line
        sys.stdout.flush()    
    
def get_idx(s, list_of_macs):
# getting string with data from the device, and checking if mac is in list_of_macs
# return index in the list_of_macs, or -1 if not there 
# s - whole string \xxxxxx\xxxxxxxxxxx etc
    m = s[20:32] # MAC of converter, 12 bytes
    if m in list_of_macs:
        return list_of_macs.index(m)
    else:
        return -1

def get_list_of_macs(block, p_to_logs):
    '''
    block = '302'...'405',
    p_to_logs - path to folder where log is, like /media/win_EON/data_log/canadian_solar/151105/
    Here we find a file structure.xml, and get list_of_macs from it
    '''
    import xml.etree.ElementTree as ET
    from pathlib2 import Path
    p_to_struc = str(Path(p_to_logs).parents[0]) #gets 2 levels up, to /media/win_EON/data_log/canadian_solar/
    
    
    name_str = '/structure_'+block+'.xml'
    p = p_to_struc + name_str #full path, including file name
    tree = ET.parse(p)
    root = tree.getroot()
    list_of_macs = []
    for m in root.iter('Converter'):
        a = m.get('mac')
        list_of_macs.append(''.join(a)) #otherwise doesn't work 
    print "getting list of macs from " + name_str + ": got " + str(len(list_of_macs))   + " macs"
    return list_of_macs
       
def get_good_sc(f,c ):
# receiving file + path, returns number of good, not-empty supercycles
# Need for arranging the 3d volume with data
    print "Counting good SC"
    with open(f,'r') as fn:
        ss= fn.read().split("=>") # all splitted supercycles
        cnt_ss = 0
        cnt_small_ss = 0 #counting empty ss, where only header line exisits, 
                #len=56-59 depending on ms size, max=32716
        #dims_ss = []  # contains sizes of all supercycles
        for l in ss:  #looking at one sc data, analyze if it's small
            #dims_ss.append(len(l))
            cnt_ss += 1
            if len(l) <= 127: # empty record has len ~56-59, +72 response =128
                cnt_small_ss += 1
            if (cnt_ss-cnt_small_ss) % 200 == 0:
                    print "\r" + str(c) + " good SC found", 
                    sys.stdout.flush()
    return  cnt_ss - cnt_small_ss       

def put_data( existing_data, new_data ):
    """ Gets 2 lines, existing and new
    # put_data( data[c][idx][:], fill_info(one[i]) )
    # check if exisiting_data had '' in every place, if yes (meaning previous fill was bad or first)- put
    # there new_data, if new data is empty in some positions- leave what was there before
    Returns out line, consisting of combination """
    out = [''] * len(existing_data)
    for i in range(0, len(existing_data)): #both lines are 22+2 elements
        if existing_data[i] == '':
            out[i] = new_data[i] # if current position was empty - fill it with new data
            # otherwise leave whatever was there before
            #this is to avoid overwritting good values with new , which might be empty ''
        else:
            out[i] = existing_data[i] # leave whatever was there
    return out # all good        

def cond_check(l,t, list_of_macs)        :
    """
    To check all conditions before creating a record in data_gw
    l - 1 SC, ie request and ED responces part of the log, corresponding to 1 SC
    t- number of supercycle
    list_of_macs - to check that current mac is in the list, not some garbage
    returns good_response - list of request, and filtered (by time_difference) responses from ED
    """
    rightchars = set(['A', 'B','C', 'D', 'E', 'F','\t','\n','*',  \
                      '0','1','2','3','4','5','6','7','8','9',\
                      'h', 'M', 'm','s', ':', 'U', 'T','|',' ', \
                      '#', ')', '(', ',', '=', 'G', 'L', 'O', 'N', \
                      'P', 'S', 'R', 'W', 'a', 'c', 'b', 'e', 'd', \
                      'g', 'f', 'i', 'k', 'l', 'o', 'n', 'q', 'p', \
                      'r', 'u', 't', 'w', 'v', 'y', 'z'])
    #only these chars are allowed anywhere in "one"!
    one = l.split()
    
    if (set(l).issubset(rightchars)
        and len(l) >=127 and t > 0
        and len(one) > 10
        and one[0]=="MAC:" and len(one[1]) == 12
        and one[2]=="Ch:"  and len(one[3]) <= 3
        and one[4]=="T:"  and len(one[5]) <= 4
        and one[6]=="UTC:" and len(one[7]) == 10
        and one[8]=="ms:" and len(one[9]) <=3
        and one[10][0] == '|' and one[10][7] == '|'): # and one[10][0] == '|' and one[10][7] == '|' is important!
            request_utc = int(one[7])  # change request UTC to int
            good_resp = [x for x in one[:10] ] #put request part od SC into list, then add filtered good responces
            #tdf = []
            for response in one[10:]:
                if (len(response) == 72
                    and response[7] == '|'
                    and response[0] == '|' ): #check for correct beginning, it doesn't start with '*', and bad chars
                    tmp_utc = response[8:16]   # FA0B2D55 ex  - only the first response line! Need to do for all of them
                    tmp = list(tmp_utc) #['F', 'A', '0', 'B', '2', 'D', '5', '5']
                    if len(tmp) == 8:
                        tmp[0], tmp[6] = tmp[6], tmp[0]  #swapping elements
                        tmp[1], tmp[7] = tmp[7], tmp[1]
                        tmp[2], tmp[4] = tmp[4], tmp[2]
                        tmp[3], tmp[5] = tmp[5], tmp[3]
                        try:
                            response_utc = int(''.join(tmp), 16) # convert it to unix epoch, so we can compare it to UTC from request
                        except ValueError:
                            print "Error in conversion UTC, unreadable character in response from ED?"
                            print response
                            print tmp
                        else:
                            tdifference = request_utc - response_utc # diff in sec between request time and response time for 1st responded device
                            if tdifference == 0 and get_idx(response, list_of_macs) != -1 : # means response is from near time from request, and mac exists in the list
                                good_resp.append(response)
                            else:
                                #print response, tdifference #output like |06FEA3|751ECB5806EC3082800001DF309A9F76D9005D78D0009200A4003A00059E8EC8 8<- sec diff
                                #tdf.append(tdifference)
                                pass
                else:
                    pass
            #print "Size, Min, max, mean timedifference: ", str(len(tdf)),str(min(tdf)),str(max(tdf)),str(mean(tdf))
            return good_resp
    else: # condition check failed
        return -1

def get_settings(path):
        # Reads settings from file settings.ini (from path)
        # path = "/media/win_EON/data_log/itf/settings.ini"
        # Returns timezone , site name
        config = ConfigParser.ConfigParser()
        config.read(path)
        blocks = config.options("Settings")
        return (config.get("Settings", "tz"),
                config.get("Settings", "name"))


# main part
def main():  
    parser = argparse.ArgumentParser(description='This is a script to convert log file created by SDAG from log format to csv. ')
    parser.add_argument('-i','--input', help='Input log file with path to it, like /path/to/log/20150101_b1.log',required=True)
    # parser.add_argument('-o','--output',help='Output file name', required=True)
    parser.add_argument('-s','--start', type=int, help='Start time to have in output, like 1334 (means 13:34 or 1:34pm), default 0001')
    parser.add_argument('-f','--finish', type=int, help='Finish time to have in output, like 1934 (means 19:34 or 7:34pm), default 2359')
    args = parser.parse_args()
    #save output csv to the same folder
    if args.start: #if exsist start time
        start_time = str(args.start)
    else:
        start_time = '0001' #default start time value 00:01
    if args.finish:
        finish_time = str(args.finish)
    else:
        finish_time = '2359'
    print "Time range selected for output: " + start_time[0:2] + ':' + start_time[2:4] +\
    ' - ' + finish_time[0:2] + ':' + finish_time[2:4]
    p2set = str(Path(args.input).parents[1])+'/' #ex '/media/win_EON/data_log/itf'

    if os.path.exists(p2set):
        if os.path.exists(p2set+"settings.ini"):
            site_tz, site_name = get_settings(p2set+"settings.ini") #Here we h\need site_tz = for ex."MST"
            #est = pytz.timezone(tz)
            print ("Using settings timezone:{} site_name:{}".format(site_tz, site_name))

        else:
            print "Can't find settings.ini file in folder " + p2set+ " Can't continue, exiting now."
            sys.exit()
    else:
        print "Can't find working folder " + p2set + " Can't continue, exiting now."
        sys.exit()

    if os.path.exists(args.input):
        fname = os.path.basename(args.input)            #getting log filename
        p_to_logs = os.path.dirname(args.input)+'/'     #getting log path
        p_to_csv = p_to_logs
        print "Working on file " + fname + " from " + p_to_logs
    else:
        print "File not found at " + args.input
        print "Exiting script, can't work without log file as input"
        sys.exit()
    block = fname[-7:-4] #Either b1,b2,b3 or b4, or 301...508
    if block[0] == '_':
        block = fname[-6:-4]
    print "Found block " +block + ", all right, continuing"
    
    #list_of_macs = get_list_of_macs(block, p_to_logs)  # all good macs - old
    list_of_macs, sns, stnames = get_list_of_items(block, p_to_logs)
    if len(list_of_macs) == 0:
        print "List of macs is empty, may be structure.xml file is not present? Can't work without macs, exititg now"
        sys.exit()
    #d2 = get_good_sc(p_to_logs + fname) #mostly counting not-empty SuperCycles, d2.
    d1 = 18+1+1+1+1 #+1 to save the string, +1 for f (0 for midstring, 1 for SPT), +mpp, +module flag
    d2 = len(list_of_macs) #83
    d3 = 1 #SC count. Can get full, or allocate dynamically. 
    #For now will be dynamically getting more as we need space for new sc
    
    data = [[['' for k in xrange(d1)] for j in xrange(d2)] for i in xrange(d3)] #3D volume to put all data , 22 x c x 83
    #22 x 83 x 1179 later
    data_gw = [['' for k in xrange(4)] for j in xrange(1)] # 4 x 1179 - to save GW params from ss header line: B0 Ch, Temper, Time
    #from here: http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(site_tz) #comes from settings.ini file in upper folder, where structure.xml file
    with open(p_to_logs + fname,'r') as fn:
        ss= fn.read().split("=>")   
        #print "Current pos, before filling array:" + str(ss.tell())
        c = 0 # counting good, not empty time lines
        for t, l in enumerate(ss):  #t- counting  every sc block, good or bad
            one = cond_check(l, t, list_of_macs) # one - list ,one filtered SC, consists of request [:10] and responses [10:]
            if one != -1 :
                try:
                    utc = float(one[7]) #time from log file
                    utc_dt_conv = datetime.datetime.utcfromtimestamp(utc).replace(tzinfo=from_zone).astimezone(to_zone)
                    timestamp = (utc_dt_conv.replace(tzinfo=None) - datetime.datetime(1970, 1, 1)).total_seconds()
                    #converting from datetime to timestamp
                    data_gw[c][0] = int(timestamp) #use full UTC, but for to_zone
                    # data_gw[c][0] = datetime.datetime.fromtimestamp(int(one[7])).strftime('%H:%M:%S')
                except ValueError:
                    data_gw[c][0] = ''
                    print "ValueError: Something wrong with line header (missing values?): " 
                    print one

                try:
                    if len(one[9]) < 4:  # check for ms - this part might be absent at all somehow!
                        data_gw[c][1] = one[9] #ms
                    else:
                        data_gw[c][1] = ''
                except IndexError:
                    data_gw[c][1] = ''
                    print "IndexError: Something wrong with line header (missing values?): " 
                    print one
                    
                try:
                    data_gw[c][2] = str(int(one[3]))                    
                    #data_gw[c][2] = str((int(one[3])+4)/10) # Ch: gives channels 1-25 instead 6,16,26,- up to 246
                except ValueError:
                    data_gw[c][2] = ''
                if len(one[5]) == 4: #check for T: 2011. Might be cut there 
                    data_gw[c][3] = str(one[5]) # T:
                else:
                    data_gw[c][3] = ''
                data_gw.append(['','','',''])  # expanding array, add new layer for new sc
                #filling one layer, one SC set of devices, up to 83            
                for i in range( 10,len(one) ): # for each left elements of the chunk, which are each device line
                    idx = get_idx(one[i], list_of_macs)  #finding index of the mac in the list_of_macs
                    if idx != -1 and idx<len(list_of_macs):  # means if mac is in list, not just some broken string
                        data[c][idx][:] = put_data( data[c][idx][:], fill_info(one[i]) )
                        # check if data[c][idx][:] had '' in every place, if yes - put
                        # there data, if new data is empty - leave what was there before
                    else:
                        '''print "Some problems with string? idx=" + str(idx)
                        print one[i]
                        print "MAC: " + one[i][20:32]+ " not in list."
                        '''
                data.append([['' for k in xrange(d1)] for j in xrange(d2)]) #adding the whole layer 22x83 for the next
                c += 1  # increasing good time lines counting, aka SC 
                #if c%20==0:
                    #print '\rGood SC:' + str(c),
                    #sys.stdout.flush()
    
    # at this point the whole data array is filled, can output it into the file
    #print ""
    #csv_writer_short_michelle(data, data_gw, p_to_csv + fname[:-4] + '_electrical.csv')
    if (len(data)>1 or len(data_gw)>1):
        csv_writer(data,data_gw, p_to_csv + fname[:-3]+'csv', start_time, finish_time, p_to_csv)
        hr = int(str(datetime.datetime.time(datetime.datetime.now()))[:2]) #'15:51:17.647363' -> 15
        #if hr>=9: #do file for Michelle only later at evening
        csv_writer_short_michelle(data, data_gw, p_to_csv + fname[:-4] + '_electrical.csv',list_of_macs, sns, stnames,fname[:-4])
    else:
        print "No good data to process in the log. Early morning?"

    print " All done! Exiting log_2_csv_universal script..."


if __name__ == "__main__": main()
