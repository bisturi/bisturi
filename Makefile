RUNDOCTEST=python -m doctest
RUNUNITTEST=python -m unittest -q
RUNPYTHON=python

test: test-src test-docs test-tests test-examples

test-docs:
	@${RUNDOCTEST} `find docs -name "*.md"` *.md

test-src:
	@${RUNDOCTEST} `find bisturi -name "*.py"`

test-examples:
	@for t in `find examples -name "*.py"`; do echo $$t; ${RUNPYTHON} $$t; done

test-tests:
	@cd tests; for t in `find . -name "*.py"`; do echo $$t; ${RUNUNITTEST} `basename -s .py $$t`; done; cd ..

