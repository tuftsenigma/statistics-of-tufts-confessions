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

dbusr = 'trends_admin'
dbpsswd = 'jumboni'
dbname = 'tufts_trends'
dbport  = '31651'
dbhost  = 'ds03651'

DB = DBCloudStore(dbhost, dbport, dbname, dbusr, dbpsswd) 

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
	global TuftsFB, AccessToken
	_ID = TuftsFB["groups"][src] if src in TuftsFB["groups"] else TuftsFB["pages"][src]
	if _ID:
		return "https://graph.facebook.com/{}/feed?access_token={}".format(_ID, AccessToken)
	else:
		return ""

def mine(src):
	"""crawl data from src and write to db"""
	global DB
	_URL = getURL(src)
	res = requests.get(_URL)
	pg = 0
	print "writing to mongo store '{}'".format(DB.getName())
	while res.status_code == 200:
		pg += 1
		print "page [{}]".format(pg)
		dat = res.json()
		for d in dat["data"]:
			# blacklist keys
			if src == "TuftsConfessions":
				del d["privacy"]
				del d["from"]
			DB.write(src, d)
		if not dat["paging"]["next"]:
			break
		else:
			res = requests.get(dat["paging"]["next"])


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


		

