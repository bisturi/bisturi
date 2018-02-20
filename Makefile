RUNDOCTEST=python -m doctest
RUNUNITTEST=python -m unittest -q
RUNPYTHON=python

.PHONY: test test-docs test-src test-examples test-tests dist upload

test: test-src test-docs test-tests test-examples

test-docs:
	@${RUNDOCTEST} `find docs -name "*.md"` *.md

test-src:
	@${RUNDOCTEST} `find bisturi -name "*.py"`

test-examples:
	@for t in `find examples -name "*.py"`; do echo $$t; ${RUNPYTHON} $$t; done

test-tests:
	@cd tests; for t in `find . -name "*.py"`; do echo $$t; ${RUNUNITTEST} `basename -s .py $$t`; done; cd ..

dist:
	rm -Rf dist/ build/ *.egg-info
	python setup.py sdist bdist_wheel --universal
	rm -Rf build/ *.egg-info

upload: dist
	twine upload dist/*.tar.gz dist/*.whl
