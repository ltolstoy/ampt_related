#!/home/ltolstoy/anaconda3/bin/python
"""
This script is to use klein and twisted to create a request form and run DB query 
(with 1-of-N, or averaged-every-N-min results), 
prepare and compress output data set and send it to Michelle. 
So JMP doesn't stuck.
Right now only 1-of-every-N records works, may be will implement both in a future.
"""

from klein import Klein
from twisted.web.proxy import ReverseProxyResource
from twisted.internet.defer import inlineCallbacks, returnValue
import time, os
import subprocess as sp

app = Klein()

@app.route('/', methods=['GET'])  #https://stackoverflow.com/questions/37581015/how-do-i-handle-post-requests-in-twisted
def render_GET(request):
    return b"""<html><body>
    <form method="POST">
    <h1>In this form you can input parameters for PostgreSQL DB query search:</h1><br><br>
    Start date for query search, in format yyyy-mm-dd:<br>
    <input name="date_start" type="text"/><br>
    Stop date for query search, in format yyyy-mm-dd:<br>
    <input name="date_stop" type="text"/><br>
    Serial number, in format nnnnKnnnnnn:<br>
    <input name="ser_num" type="text"/><br>
    Selecting every Nth row: (enter N, like 5,10 or 20)<br>
    <input name="aver_int" type="text"/><br>
    <input type="submit" /></form></body></html>"""

@app.route('/', methods=['POST'])
def render_POST(request, branch=True):  # branch=True lets you return Resources
    date_start = request.args.get(b'date_start', b'172.16.248.139')[0].decode('utf-8')        # also use request.args instead
    date_stop = request.args.get(b'date_stop', b'172.16.248.139')[0].decode('utf-8')
    ser_num = request.args.get(b'ser_num', b'172.16.248.139')[0].decode('utf-8')
    aver_int = request.args.get(b'aver_int', b'172.16.248.139')[0].decode('utf-8')
    out = make_output(date_start, date_stop, ser_num, aver_int)
    #args=['-s', date_start, '-f', date_stop, '-sn', ser_num, '-a', aver_int]
    app ='/home/ltolstoy/scripts/remote_query/query_v2.py'
    sp.Popen([app, '-s', date_start, '-f', date_stop, '-sn', ser_num, '-a', aver_int])
    return out


def make_output(date_start, date_stop, ser_num, aver_int):
    """
    Function to form nice HTML output
    date_start: '2018-01-01'
    date_stop; '2018-01-02'
    ser_num: '4417K000482'
    aver_int: '5'  min
    """
    out = ('<body><html><br>'+ \
    'Start date is {},<br><br>'+ \
    'stop date is {},<br><br>'+ \
    'SN: {},<br><br>'+ \
    'averaging interval is {} sec <br><br>'+\
    'Query start time is {}<br><br>'+\
    'Email will be send when the result is ready.<br><br>'+\
    'The compressed result, when ready, could be found '+\
    '<a href=\"172.16.248.139:8000/data_output\">here</a>'+\
    '</body></html>').format(date_start, date_stop, ser_num, aver_int, time.ctime())
    
    return out


@app.route('/output/', branch=True)
def pg_index(request):
    return File('/mnt/data_log/data_output') #output

app.run(host='172.16.248.139', port=9000)
