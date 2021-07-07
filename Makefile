RUNDOCTEST ?= byexample -l python --ff --diff ndiff --jobs 2
RUNUNITTEST ?= python -m unittest -q
RUNPYTHON ?= python
RUNPIP ?= pip

.PHONY: test format-test lib-test docs-test unit-test examples-test dist upload

test: index-links-test format-test lib-test docs-test unit-test examples-test

index-links-test:
	@echo "Running index-links-test"
	@./tests/idx.sh

format-test:
	yapf -vv --style=.style.yapf --diff --recursive bisturi/

lib-test:
	@${RUNDOCTEST} `find bisturi -name "*.py"`

docs-test:
	@${RUNDOCTEST} `find docs -name "*.md"` *.md

unit-test:
	@cd tests; for t in `find . -name "*.py"`; do echo $$t; ${RUNUNITTEST} `basename -s .py $$t`; done; cd ..

examples-test:
	@for t in `find examples -name "*.py"`; do echo $$t; ${RUNPYTHON} $$t; done

format:
	yapf -vv -i --style=.style.yapf --recursive bisturi/

deps:
	$(RUNPIP) install -e .

deps-dev: deps
	$(RUNPIP) install -r requirements-dev.txt

dist:
	rm -Rf dist/ build/ *.egg-info
	python setup.py sdist bdist_wheel --universal
	rm -Rf build/ *.egg-info

upload: dist
	twine upload dist/*.tar.gz dist/*.whl

clean:
	find . -name "_*_pkt.py*" -delete
	find . -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -Rf dist/ build/ *.egg-info
	rm -f .flinks.tmp .fnames.tmp
	rm -f README.rst
