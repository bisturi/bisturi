#! /usr/bin/python

import sys, glob, os
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

def run_doc_test(filename):
    os.system('python -m doctest "%s"' % filename)

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

