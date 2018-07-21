#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse

from setuptools import glob

from unz.google_client import GoogleClient, create_message_with_zip
from unz.mail_unzipper import MailUnzipper, GmailSearchQueryBuilder, PROCESSING_LABEL, DONE_LABEL
import base64
import zipfile
import io
import re
import logging
import os
import shutil
import colorlog
from pprint import pprint

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if logger.hasHandlers():  # default logger
    logger.handlers.clear()
logger.propagate = False  # stop propagate to root logger
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(handler)

TMP_CACHE_DIR = "cache/"
NOPASS_SUFFIX = "_nopass"


def attachment_id2tmp_filename(attachment_id):
    return attachment_id[:30] + ".zip"


client = GoogleClient()


def store_encrypted_zip_mail(newer_than):
    label_name2id_table = client.get_label_name2id_table()  # type: dict[str, str]
    my_address = client.get_my_address()

    for need_label_name in [PROCESSING_LABEL, DONE_LABEL]:
        if need_label_name not in label_name2id_table:
            created = client.create_label(need_label_name)
            label_name2id_table[need_label_name] = created['id']

    query_builder = GmailSearchQueryBuilder(newer_than, exclude_from=my_address)

    # zip付きのファイルを検出し、暗号化してあれば:doingラベルをつけ、ファイルをtmp以下にキャッシュ。暗号化してなければdoneフラグを立てる
    new_zip_mails = client.search_mails(query_builder.build_new_zip_mails_query())
    logger.info("hit {} new zip message".format(len(new_zip_mails)))

    for mail in new_zip_mails:
        message_id = mail['id']
        zip_attachment_ids = client.extract_zip_attachment_ids(mail)

        # 一つでも未解凍なファイルがあったらprocessingにする。（混在は無いと思うが一応・・）
        has_encrypted_file = False
        for attachment_id in zip_attachment_ids:
            zip_resource = client.get_attachment(message_id, attachment_id)
            zip_binary = base64.urlsafe_b64decode(zip_resource['data'])

            zip = zipfile.ZipFile(io.BytesIO(zip_binary))

            is_encrypted = False
            # 1つでも暗号化されていれば暗号化zipとみなす（ファイル単位で混在することがあるのかは不明・・）
            for zinfo in zip.infolist():
                if zinfo.flag_bits & 0x1:
                    is_encrypted = True
                    break
            if is_encrypted:
                has_encrypted_file = True
                save_dir = os.path.join(TMP_CACHE_DIR, message_id)
                os.makedirs(save_dir, exist_ok=True)

                filename = attachment_id2tmp_filename(attachment_id[:30])
                with open(os.path.join(save_dir, filename), 'wb') as f:
                    f.write(zip_binary)
                logging.info("store encrypted file:{}".format(filename))
            else:
                # logging.info("not encrypted zip mail")
                pass

        if has_encrypted_file:
            client.add_label(message_id, label_name2id_table[PROCESSING_LABEL])
        else:
            client.add_label(message_id, label_name2id_table[DONE_LABEL])


def decrypt_stored_files(newer_than, search_range, append_to_thread=False, remain_decrypted_file=True):
    unzipper = MailUnzipper()

    label_name2id_table = client.get_label_name2id_table()
    my_address = client.get_my_address()
    query_builder = GmailSearchQueryBuilder(newer_than, exclude_from=my_address)

    # processing
    processing_zip_mails = client.search_mails(query_builder.build_processing_mails_query(),
                                               {'format': 'metadata',
                                                'metadataHeaders': ['From', 'Subject', 'subject']})
    logger.info("hit {} processing message".format(len(processing_zip_mails)))

    # processingメールがあれば、同一人物からのメールを検索し、パスワード候補を抽出、復号化を試みる。対象ファイルはまずtmp以下を探し、なければダウンロードしてくる
    # 復号に成功すればdoneフラグを立てて解凍済みファイルを自分宛てに再送
    # 失敗すればdoingのまま次の試行を待つ
    # TODO 関係ないメールが間に入った場合、何度も解析することになってしまう。フラグを立てるべき。ただし複数ファイルに対して暗号化されることもあるのでn:nのラベル管理が必要
    # WARNING 時間軸は考慮してない。いったんnewer_than以降のメールはすべて解析する（パスワードを先に送るケースがありえる？）

    address_extractor = re.compile(r'.*<(.+)@(.+)>.*')
    for mail in processing_zip_mails:
        # c.f. http://srgia.com/docs/rfc2822j.html
        # Fromの他にSenderやReply-toも考えられるが、オプション扱いなのでまずはFromで運用してみる
        from_kvs = list(filter(lambda x: x['name'] == 'From', mail['payload']['headers']))
        if len(from_kvs) == 0:
            logger.error("No From header message:", mail)
            continue

        from_value = from_kvs[0]['value']
        match = address_extractor.match(from_value)
        if match is None:
            logger.error("Unknown address format:", from_value)
            continue

        if search_range == 'himself':
            from_address = match.group(1) + "@" + match.group(2)
        else:  # domain
            from_address = "@" + match.group(2)

        candidate_mails = client.search_mails(query_builder.build_password_candidate_mails_query(from_address))

        # TODO 対象ファイルよりあとに送られたことを前提にできるようにする？

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
        # TODO 別サーバーでやってると保存されていない。そもそもlabelをサーバー側で管理するのを辞めるべき
        # 基本的には1つ想定
        for enc_fpath in encrypted_file_paths:
            if enc_fpath.endswith(NOPASS_SUFFIX + ".zip"): continue

            with zipfile.ZipFile(enc_fpath) as zf:
                logger.debug("try: {}".format(password_candidates))
                matched_password = unzipper.try_passwords(zf, password_candidates)
                if matched_password is None:
                    continue

                logger.info("find correct password {} for {}".format(matched_password, enc_fpath))
                dec_dir_path = enc_fpath.replace(".zip", NOPASS_SUFFIX)
                unzipper.extract_all(zf, dec_dir_path, password=matched_password.encode('ascii'))

            shutil.make_archive(dec_dir_path, 'zip', dec_dir_path)
            if append_to_thread:
                rezipped_path = dec_dir_path + ".zip"
                with open(rezipped_path, 'rb') as f:
                    decrypted_zip_binary = f.read()
                received_message_subject = client.extract_message_subject(mail)
                fname = os.path.basename(rezipped_path)
                reply = create_message_with_zip(my_address, my_address, 'Re: ' + received_message_subject,
                                                'decrypted zip message', decrypted_zip_binary, fname)
                reply['threadId'] = mail['threadId']
                sent = client.send_message(reply)
                os.remove(rezipped_path)

            # TODO 複数添付のときに1つだけ解凍に成功した場合が難しい・・。どうするか考える
            client.add_label(mail['id'], label_name2id_table[DONE_LABEL])
            client.remove_label(mail['id'], label_name2id_table[PROCESSING_LABEL])

            # remove cached files
            os.remove(enc_fpath)
            if not remain_decrypted_file:
                shutil.rmtree(dec_dir_path)


def main():
    parser = argparse.ArgumentParser('mail-unzipper')
    parser.add_argument('--newer_than', type=str, default='1m', help='gmail search query: e.g. 1d, 1m, 1y')
    parser.add_argument('--range', type=str, default='domain', choices=['himself', 'domain'],
                        help='sender who can send password range(himself or domain)')
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--silent', action='store_true', default=False)
    parser.add_argument('--only_decrypt', action='store_true', default=False,
                        help='decrypt only. not send to same thread')
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.silent:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

    store_encrypted_zip_mail(args.newer_than)
    decrypt_stored_files(args.newer_than, args.range, not args.only_decrypt)


def _storing_test():
    store_encrypted_zip_mail('1m')  #


def _decrypt_test():
    decrypt_stored_files('1m', 'himself')


# def test_encode():
#     path = 'tmp/1641719ea0d1ed77/ANGjdJ9rMSHopEXXYYKp7pXJQzTu62.zip'
#     pwd = b't9uphiP9UO'
#     import zipfile
#     with zipfile.ZipFile(path) as zf:
#         for t in zf.filelist:
#             if not (t.flag_bits & 0x800):
#                 old_name = t.filename
#                 new_name = t.filename.encode('cp437').decode('sjis')
#                 t.filename = new_name
#                 zf.NameToInfo[new_name] = zf.NameToInfo[old_name]
#                 del zf.NameToInfo[old_name]
#         zf.extractall(pwd=pwd)
#

if __name__ == '__main__':
    main()
