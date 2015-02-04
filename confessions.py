import	re
import	time
import	os
import  requests
import	datetime
import	sys
import 	nltk
import	json
import 	gensim
import	decimal
import 	jsonpickle
import	pickle
import 	numpy as np
from	sets				import Set
from	nltk.corpus			import stopwords
from	nltk.collocations 	import BigramAssocMeasures, BigramCollocationFinder
from	nltk.collocations 	import TrigramAssocMeasures, TrigramCollocationFinder
from 	nltk				import bigrams
from 	nltk				import trigrams
from	gensim 				import corpora, models, similarities
from 	db 					import DBCloudStore
from 	os 					import path
from	slog 				import *
from 	matplotlib			import pyplot as plt


"""
Scripts used for 'TuftsConfessions' analysis

DATA TO GET:
1. popular words -- top trigrams vs specific Tufts trigrams x
2. sentiment score vs frequency vis -- need to actually write sentiment score to db, b/c throttled over time.. redo and label scores accordingly
3. LDA into good topics and map against popularity - look through different shaped models 2/2 and 2/3 and cherry pick
4. daily, monthly trends
5. correlation between sentiment and likes (?)


'mongo ds031651.mongolab.com:31651/tufts_trends -u trends_admin -p jumboni'

"""


# Data store
dbusr 	= 'trends_admin'
dbpsswd = 'jumboni'
dbhost  = 'ds031651.mongolab.com'
dbport  = 31651
dbname 	= 'tufts_trends'

DB = DBCloudStore(host=dbhost, port=dbport, db=dbname, usr=dbusr, psswd=dbpsswd) 

def model_topics(docs, terms, num_topics):
	'''Run Latent Dirichlet Allocation on docs x terms'''
	if num_topics:
		NUM_TOPICS = num_topics
	else:
		NUM_TOPICS = 15
	NUM_WORDS  = 15
	dictionary = corpora.Dictionary(docs) # map words to ids
	corpus = [dictionary.doc2bow(d) for d in docs] # create sparse vector of doc word-counts

	print "<preparing to LDA>"
	lda = gensim.models.ldamodel.LdaModel(corpus, id2word=dictionary, num_topics=NUM_TOPICS, update_every=1, passes=50)

	print "<formed LDA model>"
	topics = lda.show_topics(num_topics=NUM_TOPICS, num_words=NUM_WORDS, log=True, formatted=False)
	slogger.info("<{} topics x {} words model>\n".format(NUM_TOPICS, NUM_WORDS))
	for t,topic in enumerate(topics):
		ts = ""
		for prob, word in topic:
			ts += "{0} [{1:.04f}], ".format(word, float(prob))
		slogger.info("Topic {} : ".format(t) + ts + "\n")

def get_raw_docs(cllxn):
	"""Get unclean docs from DB"""
	confessions = DB.read(cllxn)
	posts = confessions.find()
	docs = []

	count = 0
	for post in posts:
		try:
			doc = post["message"].encode('utf-8')
			docs.append(doc)
		except KeyError:
			continue
	return docs


def munge_and_dump_posts(cllxn):
	'''Pull from database, clean FB post documents and cache them in order
	to have fast access for further analysis'''
	more_stopwords = ["hey", "doesn", "much", "didn", "could", "every", "would", "even", "get", "like", "re", "really", "www", "http", "com", "ve", "1", "watch", "youtube", "https", "tufts", "one", "two", "guy", "girl"]

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
				w = w.lower().strip("0123456789.,/?';][{}|~`!@$%^&*()-+_")
				if w not in stopwords.words("english") \
				and w not in more_stopwords \
				and w + "s" not in vocab \
				and w + "ing" not in vocab \
				and len(w) > 1:
					doc_bow.append(w)
					vocab.add(w)
			docs.append(doc_bow)
		except KeyError:
			continue

	slogger.info("total words={}".format(len(list(vocab))))
	slogger.info("total docs={}".format(len(docs)))

	return (docs, vocab)


def popular_bigrams(docs):
	text = re.split("\W+", " ".join(docs))
	for t in text:
		if len(t) == 1:
			del t

	print "<split text>"
	bigram_measures = BigramAssocMeasures()
	finder = BigramCollocationFinder.from_words(text)
	finder.apply_freq_filter(50)
	bigrams = finder.nbest(bigram_measures.pmi, 50)
	bi_tokens = nltk.bigrams(text)

	print "<printing bigram freqs>"
	for bi in bigrams:
		score = finder.score_ngram(bigram_measures.pmi, bi[0], bi[1])
		print "< {}, {} > freq= {}, score={}".format(bi[0], bi[1], bi_tokens.count(bi), score)
	time.sleep(10)


def popular_trigrams(docs):
	text = re.split("\W+", " ".join(docs))

	print "<split text>"
	trigram_measures = TrigramAssocMeasures()
	finder = TrigramCollocationFinder.from_words(text)
	finder.apply_freq_filter(500)
	trigrams = finder.nbest(trigram_measures.pmi, 50)
	tri_tokens = nltk.trigrams(text)

	print "<printing trigram freqs>"
	for tri in trigrams:
		score = finder.score_ngram(trigram_measures.pmi, tri[0], tri[1], tri[2])
		print "< {}, {}, {} > freq= {}, score={}".format(tri[0], tri[1], tri[2], tri_tokens.count(tri), score)
	time.sleep(10)

def sentiment_analysis(cllxn):
	"""plot sentiment analysis on dataset"""
	# more_stopwords = ["could", "every", "would", "even", "get", "like", "re", "really", "www", "http", "com", "ve", "1", "watch", "youtube", "https", "tufts", "one", "two", "guy", "girl"]

	confessions = DB.read(cllxn)
	posts = confessions.find()
	docs = []
	vocab = Set([])
	data = { 0.0 : 0, 0.1 : 0, 0.2 : 0, 0.3 : 0, 0.4 : 0, 0.5 : 0, 0.6 : 0, 0.7 : 0, 0.8 : 0, 0.9 : 0, 1.0 : 0 }

	count = 0
	for post in posts:
		# collect post from database
		count += 1
		print "collected {} documents".format(count)
		try:
			print post["sentiment"]
		except KeyError:
			try:
				doc = (post["message"].encode('utf-8'), post["id"])
				docs.append(doc)
			except KeyError:
				continue

	time.sleep(10)

	count = 0
	for doc in docs:
		count += 1
		print "analyzed {} documents".format(count)
		pt = get_sentiment(doc[0])
		if pt:
			print pt
			DB.update(cllxn, {"id" : doc[1]}, { "$set" : { "sentiment" : round(pt, 1) }})
			data[round(pt, 1)] += 1
			print DB.find(cllxn, { "id" : doc[1]})

	slogger.info("total words={}".format(len(list(vocab))))
	slogger.info("total docs={}".format(len(docs)))
	slogger.info(data)

	print data


def get_sentiment(msg):
	"""use third party API to get polarity on msg text"""
	API = "http://text-processing.com/api/sentiment/"
	res = requests.post(API, data={ 'text'  : msg })
	if res.status_code == 200:
		return res.json()["probability"]["pos"]
	else:
		print "error in retrieving sentiment analysis"
		return ""


if __name__ == '__main__':

	if len(sys.argv) > 1:
		try:
			exps = sys.argv[1:len(sys.argv):]
		except ValueError:
			print 'Invalid input... try again.'
	else:
		try:
			print "--CURRENT EXPERIMENTS--"
			for e in exp_lookup:
				print "\t{}".format(e)
			exps = raw_input('Enter experiment to run:\n').split(' ')
		except:
			print 'Invalid input... try again.'

	slogger = slog()

	cllxn = "TuftsConfessions"
	texts = get_raw_docs(cllxn)

	for e in exps:
		if e == "popular_bigrams":
			popular_bigrams(texts)
		if e == "popular_trigrams":
			popular_trigrams(texts)
		if e == "model_topics":
			topics = [7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28]
			cache_path = path.relpath('cache/{}.pkl'.format(cllxn))
			with open(cache_path, 'rb') as cache:
				# try to quickly load from cached file
				try:
					docs,vocab = pickle.load(cache)
					slogger.info("<cache hit>")
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

			for t in topics:
				slogger.info("{} TOPIC MODEL".format(t))
				model_topics(docs, vocab, t)

		if e == "sentiment_analysis":
			sentiment_analysis(cllxn)








