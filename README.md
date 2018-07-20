# auto-gmail-decryptor
Automatically decrypt encrypted zipped gmail tool

# How it works
1. Search your mails attached encrypted zip mails.
2. Extract password candidates from same address(or domain) mails and try all.
3. If decrypted, rezip and send back to yourself on same thread.

# How to run
1. Access https://developers.google.com/gmail/api/quickstart/python
2. Create new app
3. Get credentials.json and save to ./secrets as "client_secret.json"
4. Run following code.

```
# install gmail api library
pip install -r requirements.txt

# get access token for your account
python scripts/setup.py

# run script
PYTHONPATH=. python scripts/main.py --range domain --newer_than 1m --verbose

# or set cron (not tested yet)
# TODO

```



