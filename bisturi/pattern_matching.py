from itertools import ifilter
from re import finditer
from functools import partial
from operator import eq as equals_to

class Any(object):
    def __init__(self, regexp=None):
        self.regexp = regexp
        self.length = None

    def create_regexp(self, field, pkt, fragments, stack):
        if self.regexp:
            fragments.append(self.regexp)
        else:
            field.pack_regexp(pkt, fragments, stack=stack)

    def __eq__(self, other):
        return True
    
    def __ne__(self, other):
        return False 

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
