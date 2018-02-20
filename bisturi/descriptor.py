from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

class Auto(object):
    def __init__(self, func):
        self.func = func

    def _compile(self, field_name, descriptor_name, bisturi_conf):
        self.iam_enabled_attr_name = "_is_descriptor_%s_enabled" % descriptor_name
        return [self.iam_enabled_attr_name]

    def __get__(self, instance, owner):
        if instance is None:
            return self

        iam_enabled = getattr(instance, self.iam_enabled_attr_name, True)
        if iam_enabled:
            return self.func(instance)
        else:
            real_value = getattr(instance, self.real_field_name)
            return real_value

    def __set__(self, instance, val):
        setattr(instance, self.iam_enabled_attr_name, False)
        setattr(instance, self.real_field_name, val)

    def __delete__(self, instance):
        setattr(instance, self.iam_enabled_attr_name, True)

    def sync_before_pack(self, instance):
        # this can be calculated or not, we don't care
        val = self.__get__(instance, type(instance))

        # we only care that the real field has the same value
        setattr(instance, self.real_field_name, val)


class AutoLength(Auto):
    def __init__(self, length_of):
        self.length_of = length_of
        Auto.__init__(self, self.calculate_length)

    def calculate_length(self, instance):
        return len(getattr(instance, self.length_of))

