
class AutoLength(object):
    def __init__(self, length_of=None):
        self.init(length_of)
    
    def init(self, length_of):
        self.length_of = length_of

    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        return len(getattr(instance, self.length_of))

    def sync_before_pack(self, instance):
        assert instance is not None
        setattr(instance, self.real_field_name, self.__get__(instance, type(instance)))

