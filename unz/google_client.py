#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import googleapiclient.discovery as gdiscovery
from httplib2 import Http
from oauth2client import file, client, tools

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    # label create
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
]

SECRET_KEY_PATH = 'secrets/client_secret.json'
CREDENTIAL_PATH = 'secrets/credentials.json'


class GoogleClient:

    @classmethod
    def store_credentials(cls):
        # Setup the Gmail API
        store = file.Storage(CREDENTIAL_PATH)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(SECRET_KEY_PATH, SCOPES)
            creds = tools.run_flow(flow, store)
        else:
            print('already has valid credentials')

    def __init__(self):
        store = file.Storage(CREDENTIAL_PATH)
        creds = store.get()
        if not creds or creds.invalid:
            raise RuntimeError("no credentials. should get credentials before new")
        self.service = gdiscovery.build('gmail', 'v1',
                                        http=creds.authorize(Http()))  # type: gdiscovery.Resource

    def get_recent_mails(self):
        pass
        # Call the Gmail API
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            print('No labels found.')
        else:
            print('Labels:')
            for label in labels:
                print(label['name'])
