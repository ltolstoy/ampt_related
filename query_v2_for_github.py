#!/home/ltolstoy/anaconda3/bin/python
"""
Script to communicate with postgresql db.
Use sqlalchemy. Create connection, send query, get results, compress it, send email.
"""

from sqlalchemy import create_engine
# from time import gmtime, strftime
from datetime import datetime
import os, sys, time
import argparse
import csv
import subprocess as sp

def check_arguments(args):
    """
    Function to check the format of start, stop dates, sn length and format
    date_start, date_stop are supposed to be in '2108-01-01' format
    serial_number is supposed to be 11 chars long and has 'K' in pos 4   
    """
    flag = 0    #all args are fine
    msg = ''    #diagnostic message
    if args.date_start[4] != '-' or args.date_start[7] != '-':
        flag = 1
        msg = "date_start in wrong format"
    if args.date_stop[4] != '-' or args.date_stop[7] != '-':
        flag = 2
        msg = "date_stop in wrong format"
    if len(args.serial_number) != 11 or args.serial_number[4] != 'K':
        flag = 3
        msg = "serial number has wrong length, or wrong format"
    return flag, msg

def send_email(p2f):
    """
    Function to send the reminder to Michelle, that file with data is ready for downloading
    p2f: full path to the file, or just file name
    """
    
    import smtplib
    import configparser
    from email.mime.text import MIMEText
    
    config = configparser.ConfigParser()
    config.read('sendgrid_settings.ini') #should be in the folder with the script
    apikey = config.get('apikey', 'key')
    text = "{} - Query results for file {} are in 172.16.248.139:8000/data_output/".format(time.ctime(), p2f)
    msg = MIMEText(text)
    me = "ltolstoy@ampt.com"
    you = [ "ltolstoy@xxxx.com", "Michelle.Propst@xxxx.com"]     

    msg['Subject'] = "DB query results are ready at {} for file {}".format(time.ctime(), p2f)
    msg['From'] = me
    msg['To'] = ",".join(you)
    s = smtplib.SMTP('smtp.sendgrid.net')
    s.login('apikey', apikey) #use key from sengdrid_settings.ini file
    s.sendmail(me, you, msg.as_string())
    s.quit()

def main():
    """
    Read input arguments: date_start, date_stop, ser_num, aver_int
    Query the db, save output file, email Michelle the result location
    """
    parser = argparse.ArgumentParser(description='Script that query DB. Needs date_start (2018-02-01), date_stop (2018-02-02), ser_num (1234K567890), aver_int (5)')
    parser.add_argument('-s','--date_start', help='Start date, like 2018-02-01', required=True)
    parser.add_argument('-f','--date_stop', help='Stop date, like 2018-02-02', required=True)
    parser.add_argument('-sn','--serial_number', help='Serial number to look for, like 1234K567890', required=True)
    parser.add_argument('-a','--aver_int', help='Averaging interval, like 5 (or 10) min', required=True)
    args = parser.parse_args()
    flag, msg = check_arguments(args)
    if flag != 0:
        print("Something wrong with arguments: {}. Can't continue, exiting now!".format(msg))
        sys.exit()
    if args.date_start[:4] == '2018' and args.date_stop[:4] == '2018' : #detecting which table in db to use
        table = 'data_electrical_2018'
    else:
        table = 'data_electrical'  #for 2017 and 2016 years data
    address = 'postgresql://ltolstoy:PWD@172.16.248.141:5432/electrical'  # 'postgresql://<username>:<pswd>@<host>:<port>/<database>'
    engine = create_engine(address)
    connection = engine.raw_connection()        #was raw_connection()
    cursor = connection.cursor()

    s00 = datetime.now()
    
    fn_out = 'data_for_' + str(args.serial_number) + '_from_' + str(args.date_start) +\
        '_till_' + str(args.date_stop) + '_averaged_' + str(args.aver_int) + '_sec.csv' # forming output file name
    p2out = '/mnt/data_log/data_output/'    #folder where query output should be
    try:
        os.remove(p2out+fn_out)         #remove output file if exists!
        os.remove(p2out+fn_out+'.bz2')  #remove compressed output file too, if exists!
    except OSError:
        pass

    #First, check if this SN exists in the DB
    cur_sn = str(args.serial_number)
    q0 = "SELECT exists (SELECT 1 FROM " +table + " WHERE sn = '" + cur_sn +"' LIMIT 1);"
    cursor.execute(q0)
    out0 = cursor.fetchone()        #tuple like (True,) or (False,)
    if out0[0] != True:     #sn doesn't exists in db
        print('SN={} doesnt exist in the database. Cant continue, exiting now'.format(cur_sn))
    else:       # sn exists in db
        print('SN={} exists in the database. Continue with a query.'.format(cur_sn))
        q2 = """SELECT mac, sn, time, date, site, location, vin1, vin2, vout, iin1, iin2, iout, text, pdiss, pout  
            FROM (
            SELECT * , row_number() OVER (order by date, time) as rn
            FROM """ +table+ """ WHERE sn='"""+cur_sn+"""' AND date BETWEEN '"""+args.date_start+"""' AND '"""+args.date_stop+"""'
            ) as t
            where t.rn%"""+args.aver_int+""" = 0 and sn='"""+cur_sn+"""' AND date BETWEEN '"""+args.date_start+"""' AND '"""+args.date_stop+"""'
            order by rn;
        """
       

        cursor.execute(q2)
        out2 = cursor.fetchall()

        columns = [i[0] for i in cursor.description]
        s1 = datetime.now()
        print(("Query:\n {}\nTook {} ").format(
                            q2,
                            str(s1 - s00).split('.', 2)[0]))
        with open(p2out+fn_out, "w") as csv_file: 
            myFile = csv.writer(csv_file, lineterminator='\n')
            myFile.writerow(columns)
            myFile.writerows(out2)
        #cmd = 'lbzip2 '+p2out+fn_out
        #os.system(cmd)
        sp.Popen(['lbzip2', p2out+fn_out]) #don't wait for the result of lbzip2 compression of output file
        send_email(fn_out)
    
if __name__ == '__main__': main()
