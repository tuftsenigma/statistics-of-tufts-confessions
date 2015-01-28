from pymongo import MongoClient
import sys

'''
Connect to cloud client db
'''

class DBCloudStore():
	def __init__(self, host, port, db, usr, psswd):
		self.connection = MongoClient(host, port)
		self.db = self.connection[db]
		self.db.authenticate(usr, psswd)
		self.name = self.db

	def getName(self):
		return self.name
		
	def write(self, cllxn_id, data):
		try:
			cllxn = self.db[cllxn_id]
			cllxn.insert(data)
		except:
			print 'dbStore err: could not write to ', cllxn_id

	def read(self, cllxn_id):
		try:
			cllxn = self.db[cllxn_id]
			return cllxn
		except:
			print 'dbStore err: could not read from ', cllxn_id
			return None
			
	def update(self, cllxn_id, doc_param, update_param):
		cllxn = self.db[cllxn_id]
		cllxn.update(doc_param, update_param)
