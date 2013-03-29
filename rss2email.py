#!/usr/bin/python
"""rss2email: get RSS feeds emailed to you
http://rss2email.infogami.com

Usage:
  new [emailaddress] (create new feedfile)
  run [--no-send] [num]
  add feedurl
  list
  reset
  delete n
  pause n
  unpause n
  opmlexport
  opmlimport filename
"""
__version__ = "2.72"
__author__ = "Lindsey Smith (lindsey@allthingsrss.com)"
__copyright__ = "(C) 2004 Aaron Swartz. GNU GPL 2 or 3."
___contributors__ = ["Dean Jackson", "Brian Lalor", "Joey Hess",
                     "Matej Cepl", "Martin 'Joey' Schulze",
                     "Marcel Ackermann (http://www.DreamFlasher.de)",
                     "Lindsey Smith (maintainer)", "Erik Hetzner", "Aaron Swartz (original author)"]

import urllib2

urllib2.install_opener(urllib2.build_opener())

### Vaguely Customizable Options ###

# 1: Receive one email per post.
# 0: Receive an email every time a post changes.
TRUST_GUID = 1

# 1: Name feeds as they're being processed.
# 0: Keep quiet.
VERBOSE = 0

# Set this to override the timeout (in seconds) for feed server response
FEED_TIMEOUT = 60

# If you have an HTTP Proxy set this in the format 'http://your.proxy.here:8080/'
PROXY = ""


### Load the Options ###

# Read options from config file if present.
import sys

sys.path.insert(0, ".")
try:
    from config import *
except:
    pass

warn = sys.stderr

### Import Modules ###

import cPickle as pickle, time, os, traceback

hash = ()
try:
    import hashlib

    hash = hashlib.md5
except ImportError:
    import md5

    hash = md5.new

unix = 0
try:
    import fcntl
    # A pox on SunOS file locking methods
    if (sys.platform.find('sunos') == -1):
        unix = 1
except:
    pass

import socket

socket_errors = []
for e in ['error', 'gaierror']:
    if hasattr(socket, e): socket_errors.append(getattr(socket, e))

import feedparser

feedparser.USER_AGENT = "rss2email/" + __version__ + " +http://www.allthingsrss.com/rss2email/"
feedparser.SANITIZE_HTML = 0

from types import *

### Utility Functions ###

import threading

class TimeoutError(Exception): pass


class InputError(Exception): pass


def timelimit(timeout, function):
    def internal2(*args, **kw):
        """
        from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878
        """

        class Calculator(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.result = None
                self.error = None

            def run(self):
                try:
                    self.result = function(*args, **kw)
                except:
                    self.error = sys.exc_info()

        c = Calculator()
        c.setDaemon(True) # don't hold up exiting
        c.start()
        c.join(timeout)
        if c.isAlive():
            raise TimeoutError
        if c.error:
            raise c.error[0], c.error[1]
        return c.result

    return internal2


def isstr(f): return isinstance(f, type('')) or isinstance(f, type(u''))


def ishtml(t): return type(t) is type(())


def contains(a, b): return a.find(b) != -1

### Parsing Utilities ###
def getID(entry):
    """Get best ID from an entry.
    NEEDS UNIT TESTS"""
    if TRUST_GUID:
        if 'id' in entry and entry.id:
            # Newer versions of feedparser could return a dictionary
            if type(entry.id) is DictType:
                return entry.id.values()[0]

            return entry.id

    if 'link' in entry: return entry.link


### Simple Database of Feeds ###

class Feed:
    def __init__(self, url):
        self.url, self.etag, self.modified, self.seen = url, None, None, {}
        self.active = True


def load(lock=1):
    if not os.path.exists(feedfile):
        print 'Feedfile "%s" does not exist.  If you\'re using r2e for the first time, you' % feedfile
        print "have to run 'r2e new' first."
        sys.exit(1)
    try:
        feedfileObject = open(feedfile, 'r')
    except IOError, e:
        print "Feedfile could not be opened: %s" % e
        sys.exit(1)
    feeds = pickle.load(feedfileObject)

    if lock:
        locktype = 0
        if unix:
            locktype = fcntl.LOCK_EX
            fcntl.flock(feedfileObject.fileno(), locktype)
        #HACK: to deal with lock caching
        feedfileObject = open(feedfile, 'r')
        feeds = pickle.load(feedfileObject)
        if unix:
            fcntl.flock(feedfileObject.fileno(), locktype)
    if feeds:
        for feed in feeds[1:]:
            if not hasattr(feed, 'active'):
                feed.active = True

    return feeds, feedfileObject


def unlock(feeds, feedfileObject):
    if not unix:
        pickle.dump(feeds, open(feedfile, 'w'))
    else:
        fd = open(feedfile + '.tmp', 'w')
        pickle.dump(feeds, fd)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.rename(feedfile + '.tmp', feedfile)
        fcntl.flock(feedfileObject.fileno(), fcntl.LOCK_UN)

#@timelimit(FEED_TIMEOUT)
def parse(url, etag, modified):
    if PROXY == '':
        return feedparser.parse(url, etag, modified)
    else:
        proxy = urllib2.ProxyHandler({"http": PROXY})
        return feedparser.parse(url, etag, modified, handlers=[proxy])


### Program Functions ###

def add(*urls):
    feeds, feedfileObject = load()
    for url in urls:
        feeds.append(Feed(url))
    unlock(feeds, feedfileObject)


def run(num=None):
    feeds, feedfileObject = load()
    try:
        if feeds and isstr(feeds[0]): default_to = feeds[0]; ifeeds = feeds[1:]
        else: ifeeds = feeds

        if num: ifeeds = [feeds[num]]
        feednum = 0

        for feed in ifeeds:
            try:
                feednum += 1
                if not feed.active: continue

                if VERBOSE: print >> warn, 'I: Processing [%d] "%s"' % (feednum, feed.url)
                http_result = {}
                try:
                    http_result = timelimit(FEED_TIMEOUT, parse)(feed.url, feed.etag, feed.modified)
                except TimeoutError:
                    print >> warn, 'W: feed [%d] "%s" timed out' % (feednum, feed.url)
                    continue

                # Handle various status conditions, as required
                if 'status' in http_result:
                    if http_result.status == 301: feed.url = http_result['url']
                    elif http_result.status == 410:
                        print >> warn, "W: feed gone; deleting", feed.url
                        feeds.remove(feed)
                        continue

                http_status = http_result.get('status', 200)
                if VERBOSE > 1: print >> warn, "I: http status", http_status
                http_headers = http_result.get('headers', {'content-type': 'application/rss+xml','content-length': '1'})
                exc_type = http_result.get("bozo_exception", Exception()).__class__
                if http_status != 304 and not http_result.entries and not http_result.get('version', ''):
                    if http_status not in [200, 302]:
                        print >> warn, "W: error %d [%d] %s" % (http_status, feednum, feed.url)

                    elif contains(http_headers.get('content-type', 'rss'), 'html'):
                        print >> warn, "W: looks like HTML [%d] %s" % (feednum, feed.url)

                    elif http_headers.get('content-length', '1') == '0':
                        print >> warn, "W: empty page [%d] %s" % (feednum, feed.url)

                    elif hasattr(socket, 'timeout') and exc_type == socket.timeout:
                        print >> warn, "W: timed out on [%d] %s" % (feednum, feed.url)

                    elif exc_type == IOError:
                        print >> warn, 'W: "%s" [%d] %s' % (http_result.bozo_exception, feednum, feed.url)

                    elif hasattr(feedparser, 'zlib') and exc_type == feedparser.zlib.error:
                        print >> warn, "W: broken compression [%d] %s" % (feednum, feed.url)

                    elif exc_type in socket_errors:
                        exc_reason = http_result.bozo_exception.args[1]
                        print >> warn, "W: %s [%d] %s" % (exc_reason, feednum, feed.url)

                    elif exc_type == urllib2.URLError:
                        if http_result.bozo_exception.reason.__class__ in socket_errors:
                            exc_reason = http_result.bozo_exception.reason.args[1]
                        else:
                            exc_reason = http_result.bozo_exception.reason
                        print >> warn, "W: %s [%d] %s" % (exc_reason, feednum, feed.url)

                    elif exc_type == AttributeError:
                        print >> warn, "W: %s [%d] %s" % (http_result.bozo_exception, feednum, feed.url)

                    elif exc_type == KeyboardInterrupt:
                        raise http_result.bozo_exception

                    elif http_result.bozo:
                        print >> warn, 'E: error in [%d] "%s" feed (%s)' % (
                        feednum, feed.url, http_result.get("bozo_exception", "can't process"))

                    else:
                        print >> warn, "=== rss2email encountered a problem with this feed ==="
                        print >> warn, "=== See the rss2email FAQ at http://www.allthingsrss.com/rss2email/ for assistance ==="
                        print >> warn, "=== If this occurs repeatedly, send this to lindsey@allthingsrss.com ==="
                        print >> warn, "E:", http_result.get("bozo_exception", "can't process"), feed.url
                        print >> warn, http_result
                        print >> warn, "rss2email", __version__
                        print >> warn, "feedparser", feedparser.__version__
                        print >> warn, "Python", sys.version
                        print >> warn, "=== END HERE ==="
                    continue

                http_result.entries.reverse()

                for entry in http_result.entries:
                    id = getID(entry)

                    # If TRUST_GUID isn't set, we get back hashes of the content.
                    # Instead of letting these run wild, we put them in context
                    # by associating them with the actual ID (if it exists).

                    frameid = entry.get('id')
                    if not (frameid): frameid = id
                    if type(frameid) is DictType:
                        frameid = frameid.values()[0]

                    # If this item's ID is in our database
                    # then it's already been sent
                    # and we don't need to do anything more.

                    if frameid in feed.seen:
                        if feed.seen[frameid] == id: continue

                    link = entry.get('link', "")

                    # TODO : call readability
                    print link

                    feed.seen[frameid] = id

                feed.etag, feed.modified = http_result.get('etag', None), http_result.get('modified', None)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print >> warn, "=== rss2email encountered a problem with this feed ==="
                print >> warn, "=== See the rss2email FAQ at http://www.allthingsrss.com/rss2email/ for assistance ==="
                print >> warn, "=== If this occurs repeatedly, send this to lindsey@allthingsrss.com ==="
                print >> warn, "E: could not parse", feed.url
                traceback.print_exc(file=warn)
                print >> warn, "rss2email", __version__
                print >> warn, "feedparser", feedparser.__version__
                print >> warn, "Python", sys.version
                print >> warn, "=== END HERE ==="
                continue

    finally:
        unlock(feeds, feedfileObject)


def list():
    feeds, feedfileObject = load(lock=0)

    if feeds and isstr(feeds[0]):
        default_to = feeds[0]
        ifeeds = feeds[1:]
        i = 1
        print "default email:", default_to
    else: ifeeds = feeds; i = 0
    for f in ifeeds:
        active = ('[ ]', '[*]')[f.active]
        print `i` + ':', active, f.url
        i += 1


def opmlexport():
    import xml.sax.saxutils

    feeds, feedfileObject = load(lock=0)

    if feeds:
        print '<?xml version="1.0" encoding="UTF-8"?>\n<opml version="1.0">\n<head>\n<title>rss2email OPML export</title>\n</head>\n<body>'
        for f in feeds[1:]:
            url = xml.sax.saxutils.escape(f.url)
            print '<outline type="rss" text="%s" xmlUrl="%s"/>' % (url, url)
        print '</body>\n</opml>'


def opmlimport(importfile):
    importfileObject = None
    print 'Importing feeds from', importfile
    if not os.path.exists(importfile):
        print 'OPML import file "%s" does not exist.' % importfile
    try:
        importfileObject = open(importfile, 'r')
    except IOError, e:
        print "OPML import file could not be opened: %s" % e
        sys.exit(1)
    try:
        import xml.dom.minidom

        dom = xml.dom.minidom.parse(importfileObject)
        newfeeds = dom.getElementsByTagName('outline')
    except:
        print 'E: Unable to parse OPML file'
        sys.exit(1)

    feeds, feedfileObject = load(lock=1)

    import xml.sax.saxutils

    for f in newfeeds:
        if f.hasAttribute('xmlUrl'):
            feedurl = f.getAttribute('xmlUrl')
            print 'Adding %s' % xml.sax.saxutils.unescape(feedurl)
            feeds.append(Feed(feedurl))

    unlock(feeds, feedfileObject)


def delete(n):
    feeds, feedfileObject = load()
    if (n == 0) and (feeds and isstr(feeds[0])):
        print >> warn, "W: ID has to be equal to or higher than 1"
    elif n >= len(feeds):
        print >> warn, "W: no such feed"
    else:
        print >> warn, "W: deleting feed %s" % feeds[n].url
        feeds = feeds[:n] + feeds[n + 1:]
        if n != len(feeds):
            print >> warn, "W: feed IDs have changed, list before deleting again"
    unlock(feeds, feedfileObject)


def toggleactive(n, active):
    feeds, feedfileObject = load()
    if (n == 0) and (feeds and isstr(feeds[0])):
        print >> warn, "W: ID has to be equal to or higher than 1"
    elif n >= len(feeds):
        print >> warn, "W: no such feed"
    else:
        action = ('Pausing', 'Unpausing')[active]
        print >> warn, "%s feed %s" % (action, feeds[n].url)
        feeds[n].active = active
    unlock(feeds, feedfileObject)


def reset():
    feeds, feedfileObject = load()
    if feeds and isstr(feeds[0]):
        ifeeds = feeds[1:]
    else: ifeeds = feeds
    for f in ifeeds:
        if VERBOSE: print "Resetting %d already seen items" % len(f.seen)
        f.seen = {}
        f.etag = None
        f.modified = None

    unlock(feeds, feedfileObject)


def email(addr):
    feeds, feedfileObject = load()
    if feeds and isstr(feeds[0]): feeds[0] = addr
    else: feeds = [addr] + feeds
    unlock(feeds, feedfileObject)

if __name__ == '__main__':
    args = sys.argv
    try:
        if len(args) < 3: raise InputError, "insufficient args"
        feedfile, action, args = args[1], args[2], args[3:]

        if action == "run":
            if args and args[0] == "--no-send":
                def send(sender, recipient, subject, body, contenttype, extraheaders=None, smtpserver=None):
                    if VERBOSE: print 'Not sending:', subject

            if args and args[-1].isdigit(): run(int(args[-1]))
            else: run()

        elif action == "add": add(*args)

        elif action == "new":
            pickle.dump([], open(feedfile, 'w'))

        elif action == "list": list()

        elif action in ("help", "--help", "-h"): print __doc__

        elif action == "delete":
            if not args:
                raise InputError, "Action '%s' requires an argument" % action
            elif args[0].isdigit():
                delete(int(args[0]))
            else:
                raise InputError, "Action '%s' requires a number as its argument" % action

        elif action in ("pause", "unpause"):
            if not args:
                raise InputError, "Action '%s' requires an argument" % action
            elif args[0].isdigit():
                active = (action == "unpause")
                toggleactive(int(args[0]), active)
            else:
                raise InputError, "Action '%s' requires a number as its argument" % action

        elif action == "reset": reset()

        elif action == "opmlexport": opmlexport()

        elif action == "opmlimport":
            if not args:
                raise InputError, "OPML import '%s' requires a filename argument" % action
            opmlimport(args[0])

        else:
            raise InputError, "Invalid action"

    except InputError, e:
        print "E:", e
        print
        print __doc__
