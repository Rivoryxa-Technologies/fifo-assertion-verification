.PHONY: test
test:
	python3 -m unittest discover -s tests -v
	python3 tools/run.py
