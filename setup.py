# https://packaging.python.org/en/latest/distributing.html
# https://github.com/pypa/sampleproject

from setuptools import setup
from codecs import open
from os import path, system

import sys

here = path.abspath(path.dirname(__file__))

system('''pandoc -o '%(dest_rst)s' '%(src_md)s' ''' % {
            'dest_rst': path.join(here, 'README.rst'),
            'src_md':   path.join(here, 'README.md'),
            })

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# load __version__, __doc__, _author, _license and _url
exec(open(path.join(here, 'bisturi', '__init__.py')).read())

system("find . -name '_[^_]*' -delete")
setup(
    name='bisturi',
    version=__version__,

    description=__doc__,
    long_description=long_description,

    url=_url,

    # Author details
    author=_author,
    author_email='use-github-issues@example.com',

    license=_license,

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',

        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',

        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Compilers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    python_requires='>=2.6',

    keywords='parse parsing binary network file compiler code generator',

    packages=['bisturi'],
)

