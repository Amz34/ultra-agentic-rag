.PHONY: test lint run clean

test:
	python3 -m unittest discover -s tests -v

lint:
	python3 -m py_compile cli.py ultra_hybrid_rag/*.py tests/*.py

run:
	python3 cli.py benchmark

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
