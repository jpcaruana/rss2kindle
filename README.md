rss2kindle
==========

fork from turbodog/rss2email (very ugly code, but I am lazy).

I don't want email, I want RSS feeds delivered to my Kindle (via readability)

install
=======
* git clone 
* cd rss2kindle
* virtualenv env
* . env/bin/activate
* pip install -r requirements.txt

usage
======
* . env/bin/activate
* ./r2k

````
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

automating
==========
in a crontab, for instance every hour :
````
0 * * * * cd /path/to/rss2kindle && ./r2k run
````
