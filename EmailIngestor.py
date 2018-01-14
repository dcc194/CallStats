from __future__ import print_function
import httplib2
import os
import base64
import email
import mysql.connector
import threading, time
import sys
import dateutil.parser
import datetime
from datetime import date
import re

import cPickle as pickle
import json
import os.path
import my_config

from apiclient import discovery
from apiclient import errors
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
# flags = None


SCOPES = 'https://mail.google.com'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'EmailIngestor'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gmail-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid or credentials == None:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def indOfNextKeyword(msg, curIdx):
    keyIdx = 999999999999

    keywrds = ['XST:', 'MUN:', 'NAT:', 'MAP/BOX-PLAN:', 'ADC:', 'I#', 'TIME:', 'NOTES:', 'Note:', 'TRUCKS']
    for w in keywrds:
        tmpIdx = msg.find(w)
        if tmpIdx > curIdx and tmpIdx < keyIdx:
            keyIdx = tmpIdx

    if keyIdx == 999999999999:
        keyIdx = -1
    return keyIdx

def getStationKey(msg):
    splits = msg.split(' ')
    return splits[0]

def getAddr(msg):
    xstIdx = msg.find('XST:')
    if (xstIdx < 5 and xstIdx > -1):
        return ''
    elif (xstIdx > 4):
        addrend = msg.find(':')
        return msg[0:min(addrend, xstIdx)]


def getCountyNum(msg):
    sIdx = msg.find('I#')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 2:eIdx]


def getXst(msg):
    sIdx = msg.find('XST:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 4:eIdx]


def getMun(msg):
    sIdx = msg.find('MUN:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 4:eIdx]


def getNat(msg):
    sIdx = msg.find('NAT:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 4:eIdx]


def getMap(msg):
    sIdx = msg.find('MAP/BOX-PLAN:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 13:eIdx]


def getDateime(msg):
    # sIdx = msg.find('TIME:')
    # if sIdx == -1:
    #     return ''
    # else:
    #     eIdx = indOfNextKeyword(msg, sIdx)
    #     if eIdx == -1:
    #         eIdx = len(msg)
    splits = msg.split(' ')
    date = splits[2].split('-')
    return date[2] + '-' + date[1] + '-' + date[0] + ' ' + splits[1]

def getDay(msg):
    splits = msg.split(' ')
    # print(splits[2])
    try:
        tm_struct = time.strptime(splits[2], '%d-%m-%y')
    except:
        tm_struct = time.strptime(splits[2], '%d-%m-%Y')

    return time.strftime('%a', tm_struct)

def getNotes(msg):
    sIdx = msg.find('NOTES:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
    return msg[sIdx + 6:eIdx]


def getNote(msg):
    sIdx = msg.find('Note:')
    print(sIdx)
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 5:eIdx]


def getTrucks(msg):
    sIdx = msg.find('TRUCKS:')
    if sIdx == -1:
        return ''
    else:
        eIdx = indOfNextKeyword(msg, sIdx)
        if eIdx == -1:
            eIdx = len(msg)
    return msg[sIdx + 7:eIdx]


def getlat(msg):
    notes = getNotes(msg)

    m = re.search('40.[0-9]+', notes)

    if m:
        return m.group(0)
    else:
        return ''


def getlon(msg):
    notes = getNotes(msg)

    m = re.search('-0*75.[0-9]+', notes)

    if m:
        return m.group(0)
    else:
        return ''

def countCalls(call):

    if (calls['nat'] != ''):

        now = datetime.datetime.now()

        fname = str(now) + ".txt"

        # check if file exists
        if (os.path.isfile(fname)):

            with open(fname) as myfile:
                # read dict
                dict = json.loads(myfile)

                if (call['montco_id'].startswith('F')):
                    dict['fire'] = dict['fire'] + 1
                else:
                    dict['ems'] = dict['ems'] + 1

                print ("Daily Totals\n Fire: " + dict['fire'] + "\n EMS: " + dict['ems'])

                # write dict
                myfile.write(json.dumps(dict))
        else:
            with open(fname) as myfile:
                dict['fire'] = 0
                dict['ems'] = 0
                if (call['montco_id'].startswith('F')):
                    dict['fire'] = dict['fire'] + 1
                else:
                    dict['ems'] = dict['ems'] + 1

                myfile.write(json.dumps(dict))

        file_staNam = call['stationKey'] + ".txt"
        if (os.path.isfile(file_staNam)):
            with open(file_staNam) as myfile:
                callTypeCounts = json.loads(myfile)
                if call['nat'] in callTypeCounts:
                    callTypeCounts[call['nat']] = call['nat'] + 1
                else:
                    callTypeCounts[call['nat']] = 1
                myfile.write(json.dumps(callTypeCounts))
        else:
            callTypeCounts[call['nat']] = 1
            myfile.write(json.dumps(callTypeCounts))






def parseMsg(msg, date):
    call = {'stationKey': '',
            'montco_id': '',
            'addr': '',
            'xst': '',
            'mun': '',
            'nat': '',
            'map': '',
            'date_time': '',
            'notes': '',
            'Trucks': '',
            'lat': '',
            'lon': '',
            'day': ''
            }

    splits = msg.split(' ')
    if splits[3] == '2400':
        return None

    includeBitRate = True
    datapart = ''
    if splits[3] != '2400' and splits[3] != '1200':
        includeBitRate = False
        print(splits[3])
        datapart = ' '.join(splits[3:])
    else:
        datapart = ' '.join(splits[4:])

    xstIdx = datapart.find('XST:')
    if xstIdx < 5 and xstIdx > -1:
        call['addr'] = getXst(msg)
        call['notes'] = getNotes(msg)
        call['montco_id'] = getCountyNum(msg)
    elif xstIdx > 4:
        call['addr'] = getAddr(datapart)
        call['notes'] = getNotes(msg)
        call['montco_id'] = getCountyNum(msg)
    elif xstIdx < 0:
        munIdx = msg.find('MUN:')
        if munIdx < 0:
            # must just be notes
            call['montco_id'] = datapart[1:msg.find(' ')]
            call['notes'] = getNote(msg)

    call['stationKey'] = getStationKey(msg)
    call['date_time'] = getDateime(msg)
    call['xst'] = getXst(msg)
    call['mun'] = getMun(msg)
    call['nat'] = getNat(msg)
    call['map'] = getMap(msg)
    call['date_time'] = getDateime(msg)
    call['Trucks'] = getTrucks(msg)
    call['lat'] = getlat(msg)
    call['lon'] = getlon(msg)
    call['day'] = getDay(msg)

    # datestuff = email.utils.parsedate(date)
    # datestuff = dateutil.parser.parse(date).astimezone(dateutil.tz.tzstr('America/New_York'))
    # print(datestuff)

    print(call)

    countCalls(call)

    return call


def processPage(msgs, service, cnx):
    for msglst in msgs:
        msgID = msglst.get('id')
        # print(msgID)
        msg = service.users().messages().get(userId='me', id=msgID, format='raw').execute()

        # endOfJunk = msg.find('<https://groups.google.com/group/worcesterfd/subscribe>')
        # endOfData = msg.find('--')
        # msgClip = msg[endOfJunk:endOfData]
        #
        # print ('******(*******************************')
        # print(msg)


        print('********************************')

        msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        # print('********************************2')
        mime_msg = email.message_from_string(msg_str)
        # print (mime_msg)
        date = mime_msg["Date"]
        print(date)

        # useFwdIdxStart = False
        payload = ''
        if mime_msg.is_multipart():
            # payload = mime_msg[0].get_payload()
            # # for payload in mime_msg.get_payload():
            #     # if payload.is_multipart(): ...
            # print('*******************TEST A')
            # useFwdIdxStart = True
            # print (payload.get_payload())
            print('\n')
        else:
            #print('*******************TEST B')
            # print (mime_msg.get_payload())
            # print('\n')
            payload = mime_msg.get_payload()

        endIdx = payload.find('\r\n--')
        #print(endIdx)
        payloadClipped = payload[:endIdx]
        payloadClipped = payloadClipped.replace('=\r\n', '')
        payloadClipped = payloadClipped.replace('\r', '')
        payloadClipped = payloadClipped.replace('\r\n', '')
        print(payloadClipped)
        # data = None
        if payloadClipped.strip(' ') != '':
            data = parseMsg(payloadClipped, date)

        if (data != None):

            cursor = cnx.cursor()

            add_call = ("INSERT INTO calls "
                    "(stationKey, montco_id, addr, xst, mun, nat, map, date_time, notes, Trucks, lat, lon, day) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            call_data = (data['stationKey'], data['montco_id'], data['addr'], data['xst'], data['mun'], data['nat'],
                         data['map'], data['date_time'], data['notes'], data['Trucks'],
                         data['lat'], data['lon'], data['day'])

            # Insert new employee
            cursor.execute(add_call, call_data)

            cnx.commit()
            cursor.close()

        try:
            service.users().messages().trash(userId='me', id=msgID).execute()
            print('Message with id: %s deleted successfully' % msgID)
        except errors.HttpError, error:
            print('an error occurred: %s' % error)

        # #print(msg.get('payload').get('parts')[0].get('body').get('data'))
        # #msg_str = base64.urlsafe_b64decode(msg.get('payload').get('parts')[1].get('data'))
        # # mime_msg = email.message_from_string(msg_str)
        # msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        # #print(msg_str)
        # mime_msg = email.message_from_string(msg_str)
        #
        # print(mime_msg)


def main():
    """Shows basic usage of the Gmail API.


    Creates a Gmail API service object and outputs a list of label names
    of the user's Gmail account.
    """
    # print (flags)

    # return

    print('\n\n')
    print(time.ctime())
    print('Checking Mail . . .')

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    results = service.users().labels().list(userId='me').execute()
    # labels = results.get('labels', [])
    #
    # if not labels:
    #     print('No labels found.')
    # else:
    #     print('Labels:')
    #     for label in labels:
    #         print(label['name'])

    msgResults = service.users().messages().list(userId='me', labelIds=['SENT']).execute()
    # print(msgResults)

    num = msgResults.get('resultSizeEstimate')
    print('Message(s) found: ' + str(num))

    msgs = msgResults.get('messages')

    if (msgs) != None:

        cnx = mysql.connector.connect(user='root', password=my_config.mysqlPass,
                                  host='127.0.0.1',
                                  database='all_calls')

        processPage(msgs, service, cnx)


        while 'nextPageToken' in msgResults:
            page_token = msgResults['nextPageToken']
            msgResults = service.users().messages().list(userId='me', labelIds=['SENT'], pageToken=page_token).execute()
            #print(msgResults)

            num = msgResults.get('resultSizeEstimate')
            print(num)

            msgs = msgResults.get('messages')
            processPage(msgs, service, cnx)

        cnx.close()

    threading.Timer(60.0, main).start()


if __name__ == '__main__':
    main()
