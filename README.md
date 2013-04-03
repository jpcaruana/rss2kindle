# rss2kindle

fork from turbodog/rss2email (very ugly code, but I am lazy). I took very little time to work on this. I just wanted to fulfill my needs.
**I don't want email**, I want RSS feeds delivered to my **Kindle** (via readability).

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

Then, edit your config.py file and fill *READABILITY* fields :
````python
# Readability : see https://www.readability.com/account/api
READABILITY_CONSUMER_KEY = 'Reader API Key : Key field'
READABILITY_CONSUMER_SECRET = 'Reader API Key : Secret field'

READABILITY_USER = 'your login on readability.com'
READABILITY_PASSWORD = 'your password on readability.com'
````

## usage
````bash
cd rss2kindle
virtualenv env
. env/bin/activate
./r2k

rss2kindle: get RSS feeds delevered to your Kindle via Readability

Usage:
  new (create new feedfile)
  run [--no-send] [num]
  add feedurl
  list
  reset
  delete n
  pause n
  unpause n
  opmlexport
  opmlimport filename
````

````bash
./r2k add https://github.com/jpcaruana/rss2kindle/commits/master.atom
./r2k run
````

## automating calls to Readability
in a crontab, for instance every hour :
````
0 * * * * cd /path/to/rss2kindle && ./r2k run
````
