import logging
import time
import datetime
from   datetime import date
import os
import sys

#
#
#
#	Author : Soubhik Barari
#
#	Custom logger that allows:
# 	- date/time stamps for all logging output
# 	- dumps to logs folder (filed by date)
# 	- log output marked by running executable
#
#	to use :
#		* slogger = slog()
#		* slogger.info("hello world!")
#

ldir = "logs"
lf 	 = str(date.today())

def slog():
	try:
		os.mkdir("logs")
	except Exception as e:
		if (e.errno == 17):
			pass
		else:
			print e
			exit(1)

	log = logging.getLogger()
	log.setLevel(logging.DEBUG)
	fmt = logging.Formatter("[%(asctime)s] %(message)s")

	# file log
	fh = logging.FileHandler("./{dir}/{f}".format(dir=ldir, f=lf))
	fh.setFormatter(fmt)
	log.addHandler(fh)

	# console log
	sh = logging.StreamHandler()
	sh.setFormatter(fmt)
	log.addHandler(sh)

	log.info("<RUN {p}>".format(p=sys.argv[0]))
	return log


