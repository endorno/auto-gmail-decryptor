#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Setup the Gmail API
from unz.google_client import GoogleClient, create_message_with_zip
import base64
from pprint import pprint


def get_messages():
    client = GoogleClient()
    service = client.service
    # messages = service.users().messages().list(userId='me', q='from:{dummy@mail} filename:zip').execute()
    messages = service.users().messages().list(userId='me', q='filename:zip').execute()
    client.get_message('')
    pprint(messages)


def get_batch_messages():
    client = GoogleClient()
    service = client.service
    # messages = service.users().messages().list(userId='me', q='from:{dummy@mail} filename:zip').execute()
    message_ids = service.users().messages().list(userId='me', q='filename:zip').execute()
    batch = service.new_batch_http_request()
    ret = []

    def each_request_callback(request_id, response, exception):
        print(request_id)
        ret.append(response)

    import time
    tic = time.time()
    for message in message_ids['messages']:
        message_id = message['id']
        batch.add(service.users().messages().get(userId='me', id=message_id, format='metadata'),
                  callback=each_request_callback)
    batch.execute()
    # print("elapsed:", time.time() - tic)
    pprint(ret)


def load_zip():
    client = GoogleClient()
    service = client.service
    # messages = service.users().messages().list(userId='me', q='from:{dummy@mail} filename:zip').execute()
    messages = service.users().messages().list(userId='me', q='filename:zip').execute()
    if messages['resultSizeEstimate'] < 1:
        print("no zip message")
        return

    message_id = messages['messages'][0]['id']

    message = service.users().messages().get(userId='me', id=message_id).execute()
    # print(message)

    zip_attachment_id = None
    for attachment in message['payload']['parts']:
        mime = attachment['mimeType']
        if mime == 'application/zip':
            zip_attachment_id = attachment['body']['attachmentId']
            # currently only one zip file.
            break
    print(zip_attachment_id)
    if zip_attachment_id is None:
        print("no zip attachment(mime type error)")
        return

    attachment = service.users().messages().attachments().get(id=zip_attachment_id, messageId=message_id,
                                                              userId='me').execute()
    zip_binary = base64.b64decode(attachment['data'])
    print(zip_binary)


def label_handling():
    client = GoogleClient()
    service = client.service
    labels = service.users().labels().list(userId='me').execute()

    # find unzipper labels
    needs_label = ['unzipper:done']
    unzipper_labels = []
    for label in labels['labels']:
        if label['name'] in needs_label:
            unzipper_labels.append(label)
            needs_label.remove(label['name'])

    if len(needs_label) > 0:
        print("create needed label")
        for label in needs_label:
            created_label = service.users().labels().create(userId='me',
                                                            body={
                                                                'name': label,
                                                                'labelListVisibility': 'labelShow',
                                                                'messageListVisibility': 'show'
                                                            }
                                                            ).execute()
            print(created_label)
            unzipper_labels.append(created_label)
    print(unzipper_labels)


def send_zipped_mail():
    client = GoogleClient()
    my_address = client.get_profile()['emailAddress']
    service = client.service
    with open('data/example/important_files_noenc.zip', 'rb') as f:
        zip_binary = f.read()
    message = create_message_with_zip(my_address, my_address,
                                      'Re: Hello Teppei',
                                      'これは大事なファイルです from script', zip_binary, 'important_files_noenc.zip')
    message['threadId'] = '1648ecad0fcc073b'
    ret = service.users().messages().send(userId='me', body=message,
                                          ).execute()
    print("sent: ", ret)


def get_profile():
    client = GoogleClient()
    profile = client.get_profile()
    print(profile)


def get_subjects():
    client = GoogleClient()
    messages = client.search_mails()
    for message in messages:
        print(client.extract_message_subject(message))


def get_with_option():
    from unz.mail_unzipper import GmailSearchQueryBuilder
    client = GoogleClient()
    query_builder = GmailSearchQueryBuilder('1m')
    ret = client.search_mails(query_builder.build_processing_mails_query(),
                              {'format': 'metadata',
                               'metadataHeaders': ['From', 'Subject', 'subject']})
    pprint(ret)


if __name__ == '__main__':
    # get_profile()
    # main()
    # sandbox()
    # get_messages()
    # get_batch_messages()
    send_zipped_mail()
    # load_zip()
    # get_subjects()
    # get_with_option()
