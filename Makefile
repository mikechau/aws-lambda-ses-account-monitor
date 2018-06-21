.PHONY: lint clean major minor patch test release master

VERSION := $(shell egrep -o "([0-9]{1,}\.)+[0-9]{1,}" .bumpversion.cfg)

all: project

project: clean lint test build

build:
	mkdir -p build/src/ses_account_monitor
	cd ses_account_monitor && cp --parents `find -name \*.py` ../build/src/ses_account_monitor
	cp lambda_handler.py build/src
	cd build/src && zip -r9 ../lambda-ses-account-monitor.zip .

clean:
	rm -rf build

major:
	bumpversion major

minor:
	bumpversion minor

patch:
	bumpversion patch

release: master
	git push origin v${VERSION}

master:
	git push origin master

lint:
	flake8 ses_account_monitor lambda_handler.py

test:
	pytest -vvv --cov=./ses_account_monitor
