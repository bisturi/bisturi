'''Parse binary data painless describing the packets' structures in python classes: no need to write 'for' loops or nested 'if' conditionals.'''

__version__ = "0.5.0"

_author  = 'Di Paola Martin'
_license = 'GNU LGPLv3'
_url = 'https://bisturi.github.io/'

try:
    from .packet import Packet
    from .field import Data, Int, Bits, Ref, Field
except SystemError:
    pass    # this happens when importing from setup.py
