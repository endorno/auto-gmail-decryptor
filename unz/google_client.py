#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import googleapiclient.discovery as gdiscovery
from httplib2 import Http
from oauth2client import file, client, tools
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    # label create
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
]

SECRET_KEY_PATH = 'secrets/client_secret.json'
TOKEN_PATH = 'secrets/token.json'


def create_message_with_zip(
        sender, to, subject, message_text, zip_binary, filename):
    """Create a message for an email.
    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.
      zip_binary:

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    msg = MIMEBase('application', 'zip')
    msg.set_payload(zip_binary)

    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}


class GoogleClient:

    @classmethod
    def store_credentials(cls):
        # Setup the Gmail API
        store = file.Storage(TOKEN_PATH)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(SECRET_KEY_PATH, SCOPES)
            creds = tools.run_flow(flow, store)
        else:
            print('already has valid credentials')

    def __init__(self):
        store = file.Storage(TOKEN_PATH)
        creds = store.get()
        if not creds or creds.invalid:
            raise RuntimeError("no credentials. should get credentials before new")
        self.service = gdiscovery.build('gmail', 'v1',
                                        http=creds.authorize(Http()))  # type: gdiscovery.Resource

    def get_profile(self):
        return self.service.users().getProfile(userId='me').execute()

    def get_my_address(self):
        return self.get_profile()['emailAddress']

    def search_mails(self, query=None, get_option={}):
        """
        :param query str or GoogleSearchQueryBuilder:
        :return:
        """
        # Call the Gmail API
        # TODO ページングに対応
        res = self.service.users().messages().list(userId='me', q=query).execute()
        if 'messages' not in res:
            return []
        id_list = res['messages']

        batch = self.service.new_batch_http_request()
        ret = []

        def each_request_callback(request_id, response, exception):
            # TODO sort by request id and handle exception
            ret.append(response)

        for message in id_list:
            message_id = message['id']
            batch.add(self.service.users().messages().get(userId='me', id=message_id, **get_option),
                      callback=each_request_callback)
        batch.execute()
        return ret

    def send_message(self, message):
        ret = self.service.users().messages().send(userId='me', body=message,
                                                   ).execute()

        return ret

    def get_message(self, message_id):
        return self.service.users().messages().get(userId='me', id=message_id).execute()

    def create_label(self, label_name, visible=True):
        return self.service.users().labels().create(userId='me',
                                                    body={
                                                        'name': label_name,
                                                        'labelListVisibility': 'labelShow' if visible else 'labelHide',
                                                        'messageListVisibility': 'show' if visible else 'hide'
                                                    }
                                                    ).execute()

    def add_label(self, message_id, label_id):
        return self.service.users().messages().modify(id=message_id, userId='me',
                                                      body={
                                                          'addLabelIds': [label_id],
                                                      }
                                                      ).execute()

    def remove_label(self, message_id, label_id):
        return self.service.users().messages().modify(id=message_id, userId='me',
                                                      body={
                                                          'removeLabelIds': [label_id],
                                                      }
                                                      ).execute()

    def get_label_name2id_table(self):
        labels = self.service.users().labels().list(userId='me').execute()
        return dict([(label['name'], label['id']) for label in labels['labels']])

    def get_attachment(self, message_id, attachment_id):
        attachment = self.service.users().messages().attachments().get(id=attachment_id, messageId=message_id,
                                                                       userId='me').execute()
        return attachment  # {"data": b64_raw_data}

    #
    # utility methods
    #
    def extract_body_text(self, message):
        payload = message['payload']
        text_data = ""
        if payload['mimeType'] == 'multipart/mixed':
            parts = payload['parts']
            for part in parts:
                # TODO partのmimeTypeを見るべき？ (multipart/alternativeだけでよいか不明なので一旦全走査)
                if 'parts' not in part:
                    continue

                sub_parts = part['parts']
                for p in sub_parts:
                    if p['mimeType'] == 'text/plain':
                        # TODO not sure utf-8
                        text_data = p['body']['data']
        elif payload['mimeType'] == 'text/plain':
            text_data = payload['body']['data']
        else:
            # html/text multipart.
            parts = message['payload']['parts']
            for p in parts:
                if p['mimeType'] == 'text/plain':
                    # TODO not sure utf-8
                    text_data = p['body']['data']
        return base64.urlsafe_b64decode(text_data).decode('utf-8')

    def extract_zip_attachment_ids(self, message):
        zip_attachment_ids = []
        for part in message['payload']['parts']:
            mime = part['mimeType']
            if mime == 'application/zip' or \
                    (mime == 'application/octet-stream' and part['filename'].endswith('.zip')):
                zip_attachment_ids.append(part['body']['attachmentId'])
        return zip_attachment_ids

    def extract_message_subject(self, message):
        headers = message['payload']['headers']
        for header in headers:
            if header['name'] == 'subject' or header['name'] == 'Subject':
                return header['value']

        return ''
