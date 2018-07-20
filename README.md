# auto-gmail-decryptor
Automatically decrypt encrypted zipped gmail tool

# How it works
1. パスワード付きのzipファイルが添付されたメールを検索
2. 同一アドレス or ドメインから送られてきたメール中からパスワードっぽい文字列を抽出し、総当たりで試す
3. うまく復号化できたら復号化済みのファイルを再zip化して同一スレッドに紐づく形で自分宛てに再送信

# How to start
```
# install gmail api library
pip install -r requirements.txt

# get access token for your account
python scripts/setup.py

# run script
PYTHONPATH=. python scripts/main.py --range domain --newer_than 1m --verbose

# or set cron (not tested)

```



