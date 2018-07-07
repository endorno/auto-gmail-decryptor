#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import base64
import zipfile

"""

パスワードの条件
・英数字、記号、4文字以上、20文字以内
・「」などで囲まれている可能性があるので前後の空白は仮定しない
・日本語パスワードは想定しない
・パスワード直前直後に空白以外の記号、英数字が来ることは想定しない
・[、"で始まっていた場合はそれらを除いたものも候補にする
・]、"、,、.で終わっていた場合にはそれらを除いたものも候補にする
"""

# password_searcher = re.compile(r'(\w{4,20})')
# c.f. https://ja.wikipedia.org/wiki/ASCII
password_searcher = re.compile(r'([!-~]{4,20})')
head_separators = ['\"', '\'', '[']
tail_separators = ['\"', '\'', ']', '.', ',']

PROCESSING_LABEL = "unzipper:processing"

DONE_LABEL = "unzipper:done"


class GmailSearchQueryBuilder:
    def __init__(self, newer_than='1d'):
        self.newer_than = newer_than

    def build_new_zip_mails_query(self):
        return "newer_than:{} filename:zip -label:{} -label{}".format(self.newer_than, PROCESSING_LABEL, DONE_LABEL)

    def build_processing_mails_query(self):
        return "newer_than:{} filename:zip label:{}".format(self.newer_than, PROCESSING_LABEL)

    def build_password_candidate_mails_query(self, sender_address_or_domain):
        return "newer_than:{} from:{}".format(self.newer_than, sender_address_or_domain)


class MailUnzipper:
    def __init__(self):
        pass

    def search_password_candidates(self, text):
        searched = password_searcher.finditer(text)
        if searched is None:
            return []
        ret = []
        for sep in searched:
            cand = sep.group(1)
            ret.append(cand)
            # TODO 正規表現で書きたい。ペア性を見たり、全組み合わせを入れるべきかも
            while cand[0] in head_separators:
                cand = cand[1:]
                ret.append(cand)

            while cand[-1] in tail_separators:
                cand = cand[:-1]
                ret.append(cand)

        return list(set(ret))

    def try_passwords(self, zf, password_candidates):
        """
        :param zipfile.ZipFile zf:
        :param password_candidates:
        :return:
        """
        for c in password_candidates:
            # TODO 日本語パスワードに対応？
            binary_c = c.encode('ascii')  # should be ascii
            zf.setpassword(binary_c)
            chunk_size = 2 ** 5

            try:
                for zinfo in zf.filelist:
                    with zf.open(zinfo.filename, "r") as f:
                        # readしないと変なパスワードがパスしてしまう
                        f.read(chunk_size)
                        pass
                return c
            except:
                continue
        return None

    def extract_all(self, zf, save_path, password, fix_encoding_as_sjis=True):
        """
        :param zipfile.ZipFile zf:
        :return:
        """
        if fix_encoding_as_sjis:
            for t in zf.filelist:
                if not (t.flag_bits & 0x800):
                    old_name = t.filename
                    new_name = t.filename.encode('cp437').decode('sjis')
                    if old_name != new_name:
                        t.filename = new_name
                        zf.NameToInfo[new_name] = zf.NameToInfo[old_name]
                        del zf.NameToInfo[old_name]
        zf.extractall(save_path, pwd=password)
