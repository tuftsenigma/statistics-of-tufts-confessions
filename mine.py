import json
import sys
import time
import requests
from   db import *


"""
Script to mine public FB data
"""


"""
GLOBAL SPACE
"""

# Data store
dbusr = 'trends_admin'
dbpsswd = 'jumboni'
dbhost  = 'ds031651.mongolab.com'
dbport  = 31651
dbname = 'tufts_trends'

DB = DBCloudStore(host=dbhost, port=dbport, db=dbname, usr=dbusr, psswd=dbpsswd) 

# Access credentials
AccessToken = "CAACEdEose0cBANeHjrTuk3Uppaqj5LEdp5lUMIKoD7lNnIZC0uGpBgPVDn1pSqEzTfQYx6GTAuykZAINZB2LWkscqdeCGWW6gZAABeqcsHL0kLmcnIEiX04cy0LE114stObT6GRZB5u3I7rBjdzcPdXttG4kjVDZBedVxL2XMhaUMTlno71ZBeJusQm2t8ERPhFgTiZCvg6lBoovVIaAGZBVh"

# Tufts data lookup
TuftsFB = {
	"groups" : {
		"TuftsTextbookExchange"	: 383445068415903,
		"TuftsClassof2018" : 629457363732303,
		"TuftsClassof2017" : 322242727853379,
		"TuftsClassof2016" : 206357896085471,
		"TuftsClassof2015" : 130730100305858,
	},
	"pages"	: {
		"TuftsConfessions" : 117787288404239,
	}
}

# Data keys
FBKeys = [
"id", 
"status_type", 
"from", 
"privacy", 
"actions", 
"update_time", 
"comments",
"created_time",
"message",
"type"
]


"""
SCRIPT SPACE
"""
def getURL(src):
	"""input a FB group / page and return graph API URL"""
	global TuftsFB, AccessToken
	_ID = TuftsFB["groups"][src] if src in TuftsFB["groups"] else TuftsFB["pages"][src]
	if _ID:
		return "https://graph.facebook.com/{}/feed?access_token={}".format(_ID, AccessToken)
	else:
		return ""

def dedup(src):
	"""iterate through DB collection corresponding to src and dedup keys"""

def mine(src):
	"""crawl data from FB group or page (src) and write to db w/src as cllxn id"""
	global DB
	_URL = getURL(src)
	res = requests.get(_URL)
	pg = 0
	print "writing to mongo store '{}'".format(DB.getName())
	while True:
		pg += 1
		print "page [{}]".format(pg)
		dat = res.json()
		for d in dat["data"]:
			# blacklist keys
			if src == "TuftsConfessions":
				del d["privacy"]
				del d["from"]

			if DB.find(src, { "id" : d["id"]}): # don't write duplicate documents
				print "<document already exists...did not write to DB>"
			else:
				DB.write(src, d)
		try:
			if not dat["paging"]["next"]:
				break
		except KeyError:
			print res.json()
			break
		else:
			res = requests.get(dat["paging"]["next"])
			while res.status_code != 200:
				print res.json()
				time.sleep(200)


if __name__ == '__main__':
	if len(sys.argv) > 1:
		try:
			srcs = sys.argv[1::]
		except ValueError:
			print 'Invalid input... try again.'
	else:
		try:
			srcs = raw_input('Enter FB sources to mine:\n').split(' ')
		except:
			print 'Invalid input... try again.'

	for src in srcs:
		mine(src)


		

