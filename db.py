from pymongo import MongoClient

#
# DB globals / singletons
#
# --twdb cllxn naming--
#
# foo_f = raw followers of profile 'foo'
# foo_c = cleaned json records of profile 'foo'
# foo_q = query stream users of token 'foo'
#


dbport  = '27017'
dbhost  = 'localhost'
dburi   = 'mongodb://' + dbhost + ':' + dbport
dfdb    = 'twdb'

class DBStore():
	def __init__(self, uri=dburi, dbname=dfdb):
		self.mongo_cl = MongoClient(uri)
		self.db = self.mongo_cl[dbname]
		self.name = dbname

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
