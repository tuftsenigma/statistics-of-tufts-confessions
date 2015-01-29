from pymongo import MongoClient
import sys

'''
Connect to cloud client db
'''

class DBCloudStore():
	def __init__(self, host, port, db, usr, psswd):
		'''create connection to db'''
		uri = "mongodb://{}:{}@{}:{}/{}".format(usr, psswd, host, port, db)
		self.connection = MongoClient(uri)
		self.db = self.connection[db]
		self.db.authenticate(usr, psswd)
		self.name = self.db

	def getName(self):
		return self.name
		
	def write(self, cllxn_id, data):
		'''write to specified collection'''
		try:
			cllxn = self.db[cllxn_id]
			cllxn.insert(data)
		except:
			print 'dbStore err: could not write to ', cllxn_id

	def read(self, cllxn_id):
		'''return collection object'''
		try:
			cllxn = self.db[cllxn_id]
			return cllxn
		except:
			print 'dbStore err: could not read from ', cllxn_id
			return None

	def find(self, cllxn_id, qstring):
		'''find single doc in collection based on specified qstring'''
		cllxn = self.db[cllxn_id]
		return cllxn.find_one(qstring)
			
	def update(self, cllxn_id, doc_param, update_param):
		'''modify document in specified collection'''
		cllxn = self.db[cllxn_id]
		cllxn.update(doc_param, update_param)
