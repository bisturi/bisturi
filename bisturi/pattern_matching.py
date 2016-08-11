

class Any(object):
    def __init__(self, regexp=None):
        self.regexp = regexp
        self.length = None

    def create_regexp(self, field, pkt, fragments, stack):
        if self.regexp:
            fragments.append(self.regexp)
        else:
            field.pack_regexp(pkt, fragments, stack=stack)



def anything_like(pkt_class):
    pkt = pkt_class()

    for field_name, field, _, _ in pkt_class.get_fields():
        setattr(pkt, field_name, Any())

    return pkt


    
