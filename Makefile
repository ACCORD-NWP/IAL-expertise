# Variables

TBINTERFACE = tbinterface.py

all: experts_doc clean pushrelease

.PHONY: all pushtest pushdev pushrelease experts_doc clean

# Pushes
pushtest:
	. ./deploy.sh test

pushdev:
	. ./deploy.sh dev

pushrelease:
	. ./deploy.sh

# Experts doc
experts_doc:
	tbinterface.py -f json -c outputexpert -n ial_expertise
	mv tbinterface_outputexpert.json ial_expertise/experts/.

clean:
	find . -name "*.pyc"       -print0 | xargs -0r rm
	find . -name "__pycache__" -print0 | xargs -0r rm -r

# Usual target
clobber: clean
