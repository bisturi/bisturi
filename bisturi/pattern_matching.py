from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

try:
    from itertools import ifilter
except:
    ifilter = filter

from re import finditer, compile, escape
from functools import partial
from operator import eq as equals_to

class Any(object):
    def __init__(self, startswith=None, endswith=None, contains=None):
        if startswith == endswith == contains == None:  # most common case
            self.regexp = None
            self.__eq__ = self.eq_for_any
            self.__ne__ = self.ne_for_any

            return

        middle = b".*" if contains is None else (b".*%s.*" % escape(contains))

        self.regexp = b""
        if startswith is not None:
            self.regexp += escape(startswith)

        self.regexp += middle

        if endswith is not None:
            self.regexp += escape(endswith)

        self.regexp = compile(self.regexp)
        self.__eq__ = self.eq_for_regexp
        self.__ne__ = self.ne_for_regexp


    def __eq__(self, other):
        if self.regexp is None:
            return self.eq_for_any(other)
        else:
            return self.eq_for_regexp(other)

    def __ne__(self, other):
        if self.regexp is None:
            return self.ne_for_any(other)
        else:
            return self.ne_for_regexp(other)

    def eq_for_any(self, other):
        return True

    def ne_for_any(self, other):
        return False

    def eq_for_regexp(self, other):
        return bool(self.regexp.search(other))

    def ne_for_regexp(self, other):
        return not bool(self.regexp.search(other))

def anything_like(pkt_class):
    pkt = pkt_class()

    for field_name, field, _, _ in pkt_class.get_fields():
        setattr(pkt, field_name, Any())

    return pkt

def filter_like(pkt, iterable, scan_through_string_for_a_match=False):
    pattern = pkt.as_regular_expression()
    return ifilter(pattern.search if scan_through_string_for_a_match else pattern.match, iterable)

def filter(pkt, iterable, filter_with_regexp_first=True, filter_like_args={}):
    if filter_with_regexp_first:
        iterable = filter_like(pkt, iterable, **filter_like_args)

    cls = pkt.__class__
    equals_to_pkt = partial(equals_to, pkt)
    return ifilter(equals_to_pkt, (cls.unpack(r, silent=True) for r in iterable))
