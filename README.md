# rss2kindle

fork from turbodog/rss2email (very ugly code, but I am lazy). I took very little time to work on this. I just wanted to fulfill my needs.

**I don't want email**, I want RSS feeds delivered to my **wallabag** account.

## how to install
````bash
git clone https://github.com/jpcaruana/rss2kindle.git
cd rss2kindle
virtualenv env
. env/bin/activate
pip install -r requirements.txt
````

## configuration
````bash
cp config.py.example config.py
````

Then, edit your config.py file and fill *WALLABAG* fields :
````python
# Wallabag
WALLABAG_URL = 'https://www.wallabag.it/'
WALLABAG_USERNAME = 'Your username'
WALLABAG_PASSWORD = 'Your passwrod associated with your username'
WALLABAG_CLIENT_ID = 'Your client ID (se Wallabag documentation)'
WALLABAG_CLIENT_SECRET = 'Your client secret key (se Wallabag documentation)'

````

## usage
````bash
cd rss2kindle
virtualenv env
. env/bin/activate
./r2k

rss2kindle: get RSS feeds delevered to your Wallabag account

Usage:
  new (create new feedfile)
  run [--no-send] [num]
  add feedurl
  list
  reset
  delete n
  pause n
  unpause n
  archiveall
  opmlexport
  opmlimport filename
````

````bash
./r2k add https://github.com/jpcaruana/rss2kindle/commits/master.atom
./r2k run
````

## automating calls to Wallabag
in a crontab, for instance every hour :
````
0 * * * * cd /path/to/rss2kindle && . env/bin/activate && ./r2k run
````
