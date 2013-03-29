# -*- coding: utf-8 -*-
import unittest
import feedparser

class test_getName(unittest.TestCase):
    def setUp(self):
        self.feed = feedparser.parse("""
<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
  <author>
    <name>Example author</name>
    <email>me@example.com</email>
    <url>http://example.com/</url>
  </author>
</entry>
</feed>
        """)
        self.entry = self.feed.entries[0]

if __name__ == '__main__':
    unittest.main()
