#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import re



def parse_candidates_from_texts():
    texts = [
        ('ab12CD34', 'パスワードは ab12CD34 です'),
        ('ab12CD34', 'パスワードはab12CD34です'),
        ('ab12CD34', 'パスワードは ab12CD34'),
        ('ab12CD34', 'password is ab12CD34'),
        ('ab12CD34', 'password is ab12CD34.'),
        ('ab1{C@34', 'パスワードは ab1{C@34 です'),
        ('ab1{C@34', 'パスワードは"ab1{C@34"です'),
        ('ab1{C@34', 'password is "ab1{C@34".'),
    ]
    for true_password, content in texts:
        candidates = search_password_candidates(content)
        print(candidates)
        assert true_password in candidates


def parse_candidates_from_mails():
    targets = glob.glob('secrets/samples/pass_*.txt')

    for path in targets:
        true_password = os.path.basename(path).replace(".txt", "").replace('pass_', '')
        with open(path) as f:
            content = f.read()
        candidates = search_password_candidates(content)
        print(true_password, candidates)
        assert true_password in candidates

    pass


if __name__ == '__main__':
    parse_candidates_from_texts()
    parse_candidates_from_mails()
