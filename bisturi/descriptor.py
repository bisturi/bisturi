
class AutoLength(object):
    def __init__(self, length_of, is_enabled_autolength_from_start=True):
        self.length_of = length_of
        self.is_enabled_autolength_from_start = is_enabled_autolength_from_start

    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        real_value = getattr(instance, self.real_field_name) 
        if real_value is None:
            return len(getattr(instance, self.length_of))
        else:
            return real_value

    def __set__(self, instance, val):
        setattr(instance, self.real_field_name, val)

    def sync_before_pack(self, instance):
        self.__set__(instance, self.__get__(instance, type(instance)))

    def sync_after_unpack(self, instance):
        if self.is_enabled_autolength_from_start:
            self.__set__(instance, None) # set to None so __get__ returns the computed value and not the stored

