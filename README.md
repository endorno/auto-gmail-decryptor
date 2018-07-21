# auto-gmail-decryptor
Automatically decrypt encrypted zipped gmail tool

# How it works
1. Search your mails attached encrypted zip mails.
2. Extract password candidates from same address(or domain) mails and try all.
3. If decrypted, rezip and send back to yourself on same thread.

# How to run
1. Get Google API credentials for yourself (currently not included this repository)
    1. Access https://developers.google.com/gmail/api/quickstart/python 
    2. Do "Step 1: Turn on the Gmail API"
    3. Download credentials.json (e.g. ~/Downloads)
2. Run following code.

```
# clone this repository
git clone https://github.com/endorno/auto-gmail-decryptor.git

# change directory
cd auto-gmail-decryptor

# move credential to secrets directory
mv ~/Downloads/credentials.json ./secrets/client_secret.json

# set library path
export PYTHONPATH=`pwd`

# install gmail api library
pip install -r requirements.txt

# get access token for your account
python scripts/setup.py

# run script
python scripts/main.py --range domain --newer_than 1m --verbose

# or set cron (not tested yet)
# TODO

```



