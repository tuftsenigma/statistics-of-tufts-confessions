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


"""
Scripts used for 'TuftsConfessions' analysis

DATA TO GET:
1. popular words -- top trigrams vs specific Tufts trigrams x
2. sentiment score vs frequenct vis 
3. LDA into good topics and map against popularity
4. hourly, daily, monthly trends
5. correlation between sentiment and likes (?)

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
	NUM_TOPICS = 13
	NUM_WORDS  = 15
	dictionary = corpora.Dictionary(docs) # map words to ids
	corpus = [dictionary.doc2bow(d) for d in docs] # create sparse vector of doc word-counts

	print "<preparing to LDA>"
	lda = gensim.models.ldamodel.LdaModel(corpus, id2word=dictionary, num_topics=NUM_TOPICS, update_every=1, passes=25)

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
	more_stopwords = ["could", "every", "would", "even", "get", "like", "re", "really", "www", "http", "com", "ve", "1", "watch", "youtube", "https", "tufts", "one", "two", "guy", "girl"]

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


if __name__ == '__main__':
	exp_lookup = [
		"popular_bigrams",
		"popular_trigrams",
		"model_topics"
	]

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
		if e == exp_lookup[0]:
			popular_bigrams(texts)
		if e == exp_lookup[1]:
			popular_trigrams(texts)
		if e == exp_lookup[2]:
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

			model_topics(docs, vocab)






