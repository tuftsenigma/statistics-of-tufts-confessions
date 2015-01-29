import	re
import	time
import	os
import	datetime
import	sys
import 	nltk
import	json
import 	gensim
import 	jsonpickle
import	pickle
import 	numpy as np
from	sets			import Set
from	nltk.corpus		import stopwords
from	gensim 			import corpora, models, similarities
from 	db 				import DBCloudStore
from 	os 				import path
from	slog 			import *


"""
Scripts used for 'TuftsConfessions' analysis

TODO:
- better clean the tokens
- LDA until good topics
- do sentiment analysis on topics and cross with popularity
- visualize sentiment vs popularity of topics

"""


# Data store
dbusr 	= 'trends_admin'
dbpsswd = 'jumboni'
dbhost  = 'ds031651.mongolab.com'
dbport  = 31651
dbname 	= 'tufts_trends'

DB = DBCloudStore(host=dbhost, port=dbport, db=dbname, usr=dbusr, psswd=dbpsswd) 

def model_topics(docs, terms):
	'''Run Latent Dirichlet Allocation on docs x terms'''
	NUM_TOPICS = 15
	NUM_WORDS  = 10
	dictionary = corpora.Dictionary(docs) # map words to ids
	corpus = [dictionary.doc2bow(d) for d in docs] # create sparse vector of doc word-counts

	print "<preparing to LDA>"
	lda = gensim.models.ldamodel.LdaModel(corpus, id2word=dictionary, num_topics=NUM_TOPICS, update_every=1, passes=20)

	print "<formed LDA model>"
	topics = lda.show_topics(num_topics=NUM_TOPICS, num_words=NUM_WORDS, log=True, formatted=False)
	for t,topic in enumerate(topics):
		ts = ""
		for prob, word in topic:
			ts += "{0} [{1:.04f}], ".format(word, float(prob))
		print "Topic {} : ".format(t) + ts + "\n"



def munge_and_dump_posts(cllxn):
	'''Pull from database, clean FB post documents and cache them in order
	to have fast access for further analysis'''
	more_stopwords = ["get", "like", "re", "really", "www", "http", "com", "1", "watch", "youtube", "https", "tufts", "one", "two", "guys"]


	confessions = DB.read(cllxn)
	posts = confessions.find()
	docs = []
	vocab = Set([])

	count = 0
	for post in posts:
	# extract vocabulary and clean docs
		count += 1
		print "parsed {} documents".format(count)
		try:
			doc = post["message"].encode('utf-8')
			doc_bow = []
			for w in re.split("\W+", doc):
				w = w.lower().strip(".,/?';][{}|~`!@$%^&*()-+_")
				if w not in stopwords.words("english") \
				and w not in more_stopwords \
				and len(w) > 1:
					doc_bow.append(w)
					vocab.add(w)
			docs.append(doc_bow)
		except KeyError:
			continue

	slogger.info("total words={}".format(len(list(vocab))))
	print "total docs={}".format(len(docs))

	return (docs, vocab)

if __name__ == '__main__':

	slogger = slog()

	cllxn = "TuftsConfessions"
	cache_path = path.relpath('cache/{}.pkl'.format(cllxn))
	with open(cache_path, 'rb') as cache:
		# try to quickly load from cached file
		try:
			docs,vocab = pickle.load(cache)
			print "<cache hit>"
		except EOFError:
			docs = None
		except IOError:
			docs = None

	if not docs:
		# if no cache, re-munge and dump
		print "<cache miss>"
		docs, vocab = munge_and_dump_posts(cllxn)
		with open(cache_path, 'wb') as cache:
			pickle.dump((docs, vocab), cache)

	model_topics(docs, vocab)






