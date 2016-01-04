
from __future__ import print_function
import httplib2
import os
import base64
import email
import mysql.connector
import sys

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None
flags = None

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Quickstart'


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
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    """Shows basic usage of the Gmail API.

    Creates a Gmail API service object and outputs a list of label names
    of the user's Gmail account.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
      print('Labels:')
      for label in labels:
        print(label['name'])

    msgResults = service.users().messages().list(userId='me').execute()
    print(msgResults)

    num = msgResults.get('resultSizeEstimate')
    print(num)

    msgs = msgResults.get('messages')

    cnx = mysql.connector.connect(user='root', password=sys.argv[1],
                              host='127.0.0.1',
                              database='all_calls')


    for msglst in msgs:
        msgID = msglst.get('id')
        print(msgID)
        msg = service.users().messages().get(userId='me', id=msgID, format='raw').execute()

        # endOfJunk = msg.find('<https://groups.google.com/group/worcesterfd/subscribe>')
        # endOfData = msg.find('--')
        # msgClip = msg[endOfJunk:endOfData]
        #
        # print ('*************************************')
        #print(msg)



        print('********************************1')


        msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        #print('********************************2')
        mime_msg = email.message_from_string(msg_str)
        # print (mime_msg)

        #useFwdIdxStart = False
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
            print('*******************TEST B')
            #print (mime_msg.get_payload())
            #print('\n')
            payload = mime_msg.get_payload()

        endIdx = payload.find('\r\n--')
        print (endIdx)
        payloadClipped = payload[:endIdx]
        print (payloadClipped)





        # #print(msg.get('payload').get('parts')[0].get('body').get('data'))
        # #msg_str = base64.urlsafe_b64decode(msg.get('payload').get('parts')[1].get('data'))
        # # mime_msg = email.message_from_string(msg_str)
        # msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        # #print(msg_str)
        # mime_msg = email.message_from_string(msg_str)
        #
        # print(mime_msg)
        
    cnx.close()

if __name__ == '__main__':
    main()

