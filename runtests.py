#! /usr/bin/env python

import sys, glob, os, doctest, re
from collections import OrderedDict

def execute_test(filename):
    os.system('python "%s"' % filename)

def run_unit_test(filename):
    dirpath, name = os.path.split(filename)
    test_name = os.path.splitext(name)[0]
    pwd = os.getcwd()

    os.chdir(dirpath)
    try:
        os.system('python -m unittest -q "%s"' % test_name)
    finally:
        os.chdir(pwd)

old_check_output = doctest.OutputChecker.check_output
def check_output(self, want, got, optionflags):
    if repr(b'') == repr(''):
        got = re.sub(r"""(\(|\s|^)[uU]([rR]?['"])""", r"\1\2", got)
        got = re.sub(r"""(\(|\s|^)[bB]([rR]?['"])""", r"\1\2", got)
    
    if repr(u'') == repr(''):
        got = re.sub(r"""(\(|\s|^)[uU]([rR]?['"])""", r"\1\2", got)
        got = re.sub(r"""(\(|\s|^)[bB]([rR]?['"])""", r"\1\2", got)

    return old_check_output(self, want, got, optionflags)
doctest.OutputChecker.check_output = check_output

def run_doc_test(filename):
    doctest.testfile(filename)

targets = sys.argv[1:]
test_sources = OrderedDict([
        ('DOCS',     (run_doc_test,  'docs/reference/%(filter)s*.md')),
        ('TUTORIAL', (run_doc_test,  'docs/tutorial_by_example/%(filter)s*.md')),
        ('CODE',     (run_doc_test,  'bisturi/%(filter)s*.py')),
        ('TESTS',    (run_unit_test, 'tests/test_%(filter)s*.py')),
        ('EXAMPLES', (execute_test,  'examples/%(filter)s*.py')),
        ('ROOT',     (run_doc_test,  '%(filter)s*.md')),
        ])

if not targets:
    targets = test_sources.keys()

for target in targets:
    if target in test_sources:
        runner, pattern = test_sources[target]
        for test_filename in sorted(glob.glob(pattern % {'filter': ''})):
            print(test_filename)
            runner(test_filename)

    else:
        for runner, pattern in test_sources.values():
            for test_filename in sorted(glob.glob(pattern  % {'filter': target})):
                print(test_filename)
                runner(test_filename)

