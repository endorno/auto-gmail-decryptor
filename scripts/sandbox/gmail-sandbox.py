#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Setup the Gmail API
from unz.google_client import GoogleClient
import base64


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



# def main():
#     client = GoogleClient()
#
#     """
#     １日以内、zipファイル付き、dor:doneラベルがついてないものを収集
#     """
#     recent_attach_zip_mails = client.get_recent_mails()
#     encrypted_zip_mails = []
#     for mail in recent_attach_zip_mails:
#         # check mail zip file is encrypted.
#         pass
#         """
#         if zip and not encrypted => done
#         """
#     if len(encrypted_zip_mails) == 0:
#         return
#
#     for mail in encrypted_zip_mails:
#         """
#         同一人物からの（もしくは同一組織・ドメイン？）、それ以降に来たメールをチェック
#         パスワード候補の文字列を取得する
#         """
#         password_candidates = []
#         for m in client.get_mail():
#             pass
#
#         """
#
#         """
#         pass
#     pass

def sandbox():
    load_zip()
    # label_handling()


if __name__ == '__main__':
    # main()
    sandbox()
