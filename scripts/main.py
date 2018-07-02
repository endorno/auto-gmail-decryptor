#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse

from setuptools import glob

from unz.google_client import GoogleClient
from unz.mail_unzipper import MailUnzipper, GmailSearchQueryBuilder, PROCESSING_LABEL, DONE_LABEL
import base64
import zipfile
import io
import re
import logging
import os

TMP_CACHE_DIR = "tmp/"


def attachment_id2tmp_filename(attachment_id):
    return attachment_id[:30] + ".zip"


def store_encrypted_zip_mail(newer_than):
    client = GoogleClient()
    label_name2id_table = client.get_label_name2id_table()  # type: dict[str, str]

    for need_label_name in [PROCESSING_LABEL, DONE_LABEL]:
        if need_label_name not in label_name2id_table:
            created = client.create_label(need_label_name)
            label_name2id_table[need_label_name] = created['id']

    query_builder = GmailSearchQueryBuilder(newer_than)

    # zip付きのファイルを検出し、暗号化してあれば:doingラベルをつけ、ファイルをtmp以下にキャッシュ。暗号化してなければdoneフラグを立てる
    # TODO: 複数のzipfileに対応させる
    new_zip_mails = client.search_mails(query_builder.build_new_zip_mails_query())
    for mail in new_zip_mails:
        message_id = mail['id']
        zip_attachment_ids = client.extract_zip_attachment_ids(mail)

        # 一つでも未解凍なファイルがあったらprocessingにする。（混在は無いと思うが一応・・）
        should_add_processing_label = False
        for attachment_id in zip_attachment_ids:
            zip_resource = client.get_attachment(message_id, attachment_id)
            zip_binary = base64.urlsafe_b64decode(zip_resource['data'])

            zip = zipfile.ZipFile(io.BytesIO(zip_binary))

            is_encrypted = False
            # 1つでも暗号化されていれば暗号化zipとみなす（混在することがあるのかはよくわからない・・）
            for zinfo in zip.infolist():
                if zinfo.flag_bits & 0x1:
                    is_encrypted = True
                    break
            if is_encrypted:
                should_add_processing_label = True
                save_dir = os.path.join(TMP_CACHE_DIR, message_id)
                os.makedirs(save_dir, exist_ok=True)

                filename = attachment_id2tmp_filename(attachment_id[:30])
                with open(os.path.join(save_dir, filename), 'wb') as f:
                    f.write(zip_binary)
                logging.info("store encrypted file:{}".format(filename))

        if should_add_processing_label:
            client.add_label(message_id, label_name2id_table[PROCESSING_LABEL])
        else:
            client.add_label(message_id, label_name2id_table[DONE_LABEL])


def decrypt_stored_files(newer_than, search_range):
    unzipper = MailUnzipper()
    query_builder = GmailSearchQueryBuilder(newer_than)

    client = GoogleClient()
    # processing
    processing_zip_mails = client.search_mails(query_builder.build_processing_mails_query(),
                                               {'format': 'metadata', 'metadataHeaders': ['From']})

    # processingメールがあれば、同一人物からのメールを検索し、パスワード候補を抽出、復号化を試みる。対象ファイルはまずtmp以下を探し、なければダウンロードしてくる
    # 復号に成功すればdoneフラグを立てて解凍済みファイルを自分宛てに再送
    # 失敗すればdoingのまま次の試行を待つ
    # TODO 関係ないメールが間に入った場合、何度も解析することになってしまう。フラグを立てるべき。ただし複数ファイルに対して暗号化されることもあるのでn:nのラベル管理が必要
    # WARNING 時間軸は考慮してない。いったんnewer_than以降のメールはすべて解析する（パスワードを先に送るケースがある？）

    address_extractor = re.compile(r'.*<(.+)@(.+)>.*')
    for mail in processing_zip_mails:
        # c.f. http://srgia.com/docs/rfc2822j.html
        # Fromの他にSenderやReply-toも考えられるが、オプション扱いなのでまずはFromで運用してみる
        from_kvs = list(filter(lambda x: x['name'] == 'From', mail['payload']['headers']))
        if len(from_kvs) == 0:
            print("Warning: no From header message:", mail)
            continue

        from_value = from_kvs[0]['value']
        match = address_extractor.match(from_value)
        if match is None:
            print("Unknown address format:", from_value)
            continue

        if search_range == 'himself':
            from_address = match.group(1) + "@" + match.group(2)
        else:  # domain
            from_address = "@" + match.group(2)

        candidate_mails = client.search_mails(query_builder.build_password_candidate_mails_query(from_address))

        # TODO 対象ファイルよりあとに送られたことを前提にできるようにする

        password_candidates = []
        for message in candidate_mails:
            content = client.extract_body_text(message)
            password_candidates += unzipper.search_password_candidates(content)

        password_candidates = list(set(password_candidates))  # make unique

        if len(password_candidates) == 0:
            # password mail is not comming yet.
            continue
        message_id = mail['id']

        # attachment_idは毎回変わってしまう・・
        # message_with_detail = client.get_message(message_id)
        # zip_attachment_ids = client.extract_zip_attachment_ids(message_with_detail)
        # del mail

        encrypted_file_paths = glob.glob(os.path.join(TMP_CACHE_DIR, message_id, "*.zip"))

        # TODO 別サーバーでやってると保存されていない。保存し直す

        # 基本的には1つ想定
        for fpath in encrypted_file_paths:
            with zipfile.ZipFile(fpath) as zf:
                matched_password = unzipper.try_passwords(zf, password_candidates)

                if matched_password is not None:
                    print("find correct password {} for {}".format(matched_password, fpath))
                    zf.extractall(fpath.replace(".zip", ""), pwd=matched_password.encode('ascii'))
                    # TODO labelをdoneにする
                    # TODO 解凍してthreadに紐付けてメール送信
                else:
                    pass


def main():
    parser = argparse.ArgumentParser('mail-unzipper')
    parser.add_argument('--newer_than', type=str, default='1d', help='gmail search query: e.g. 1d, 1m, 1y')
    parser.add_argument('--range', type=str, default='himself', choices=['himself', 'domain'],
                        help='sender who can send password range(himself or domain)')
    args = parser.parse_args()
    store_encrypted_zip_mail(args.newer_than)
    decrypt_stored_files(args.newer_than, args.range)


def _storing_test():
    store_encrypted_zip_mail('1m')  #


def _decrypt_test():
    decrypt_stored_files('1m', 'himself')


if __name__ == '__main__':
    # main()
    # _storing_test()
    _decrypt_test()
