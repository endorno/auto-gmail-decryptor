# auto-gmail-decryptor
Automatically decrypt encrypted zipped gmail tool

# How it works
1. search your mails attached encrypted zip mails.
2. extract password candidates from same address(or domain) mails and try all.
3. if decrypted, rezip and send back to yourself on same thread.

1. パスワード付きのzipファイルが添付されたメールを検索
2. 同一アドレス or ドメインから送られてきたメール中からパスワードっぽい文字列を抽出し、総当たりで試す
3. うまく復号化できたら復号化済みのファイルを再zip化して同一スレッドに紐づく形で自分宛てに再送信

# How to start
1. Access https://developers.google.com/gmail/api/quickstart/python
2. create new app
3. get credentials.json and save to ./secrets as "client_secret.json"
4. run following code.

```
# install gmail api library
pip install -r requirements.txt

# get access token for your account
python scripts/setup.py

# run script
PYTHONPATH=. python scripts/main.py --range domain --newer_than 1m --verbose

# or set cron (not tested)

```



