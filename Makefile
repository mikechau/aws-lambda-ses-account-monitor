VERSION := $(shell egrep -o "([0-9]{1,}\.)+[0-9]{1,}" .bumpversion.cfg)

.PHONY: all project init dev pip build clean major minor patch release master lint test

all: project

project: clean lint test build

init: dev pip

dev:
	deactivate | true
	rm -rf venv
	virtualenv venv -p python3.6

pip:
	. ./venv/bin/activate && pip install -r requirements.txt

build:
	mkdir -p build/src/ses_account_monitor
	find ./ses_account_monitor -name '*.py' | cpio -pdm ./build/src
	cp lambda_handler.py ./build/src
	cd build/src && zip -r9 ../lambda-ses-account-monitor.py.zip .

clean:
	rm -rf build

major: lint test
	bumpversion major

minor: lint test
	bumpversion minor

patch: lint test
	bumpversion patch

release: master
	git push origin v${VERSION}

master:
	git push origin master

lint:
	flake8 ses_account_monitor lambda_handler.py

test:
	pytest -vv --cov=./ses_account_monitor
