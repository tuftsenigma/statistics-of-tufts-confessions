import	re
import	time
import	os
import  requests
import	datetime
import	sys
import	csv
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
2. sentiment score vs frequency vis -- get most popular trigrams per bracket x
3. LDA into good topics and map against popularity - assign topic to each document based on likelihood (gibbs sampling?) and then count popularity of topics + avg sentiment + visualize
4. daily, monthly trends - peaks in postage + particular topics / words over time
5. correlation between sentiment and likes (?) - look at posts that have the most likes and analyze data

QUESTIONS TO ASK:
1. are positive or negative topics more popular on confessions? (data 1, 2, 3)
2. what are patterns over time in topics and popularity? data 4
3. what do people actually like on tufts confessions? is there a pattern? data 5

FUTURE QUESTIONS TO ASK:
1. what are dichotomies? love vs sex, beautiful vs hot
2. comparisons between schools


Mongo cmds:

connect =
'mongo ds031651.mongolab.com:31651/tufts_trends -u trends_admin -p jumboni'

query =
'db.TuftsConfessions.find( { $text : { $search : <text query> }})'

count = 
'db.TuftsConfessions.count( { $text : { $search : <text query> }})'
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
	finder.apply_freq_filter(2)
	trigrams = finder.nbest(trigram_measures.pmi, 50)
	tri_tokens = nltk.trigrams(text)

	print "<printing trigram freqs>"
	for tri in trigrams:
		score = finder.score_ngram(trigram_measures.pmi, tri[0], tri[1], tri[2])
		print "< {}, {}, {} > freq= {}, score={}".format(tri[0], tri[1], tri[2], tri_tokens.count(tri), score)
	time.sleep(10)

def score_topics(cllxn):
	"""take topic bins and score them in sentiment and popularity

	PASS 1 : popularity of topic t is {sum over all docs}_proportion of topic words in t over all topic words
	
	PASS 2 : Bayesian score... P(w = t|docs) = P(w = t|d1) + ... + P(w = t|dn) --> P(w = t|di) = 
	P(di | w = t) <probability that we get this document when looking for word w> * 
	P(w = t) <probability of getting that word in our corpus in general - word_to_docs[word].> /
	P(d) <1/num_docs>
	"""


	collection = DB.read(cllxn)
	posts = collection.find()

	with open("posts/confessions/notes/topic_compilation.tsv") as tsv:
		topics = csv.reader(tsv, delimiter="\t", quotechar="\"")
		topic_data = []
		for t in topics:
			ws = t[1].split(",")
			topic_data.append((t[0], ws))

		topic_pop = [0]*len(topic_data) # p(topic t)
		topic_sentiments = [0]*len(topic_data)
		word_to_docs = {}

		D = float(1/float(posts.count())) # 1/P(doc d)
		T = 1/float(len(topic_data))

		for post in posts:
			try:
				doc = post["message"].encode('utf-8').split()
				doc = [word.lower() for word in doc if word.lower() not in stopwords.words("english")]
				if len(doc) > 1:
					for topic in topic_data:
						for word in topic[1]:
							try:
								if (word_to_docs[word] and doc.count(word) > 0):  
									word_to_docs[word][post["id"]] = doc.count(word)
							except KeyError:
								word_to_docs[word] = { post["id"] : doc.count(word) }
			except KeyError:
				continue
		print word_to_docs		





		# for post in posts:
		# 	try:
		# 		topic_words = [0]*len(ts) # p(t)
		# 	 	doc = post["message"].encode('utf-8').split()
		# 	 	doc = [word.lower() for word in doc if word.lower() not in stopwords.words("english") ]
		# 	 	if len(doc) > 1:

		# 		 	for t, topic in enumerate(ts):
		# 		 		for word in doc:
		# 		 			topic_words[t] += topic[1].count(word)
		# 		 			T += topic[1].count(word)
		# 		 	topic_words = [float(num_topic_words)/float(T) for num_topic_words in topic_words]
		# 		 	for t,topic_count in enumerate(topic_words):
		# 				topic_pop[t] += topic_count

		# 	except KeyError:
		# 		continue

		# for t,topic in enumerate(ts):
		# 	print "{} : {}".format(topic[0], topic_pop[t])





def popular_trigrams_by_sentiment(cllxn):
	sents = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
	freq = [8, 15, 22, 25, 35, 10, 10, 10, 6]
	posts = DB.read(cllxn)
	for i, sent in enumerate(sents):
		print "< SENT : {} >".format(sent)
		docs = posts.find({ "sentiment" : sent })
		if type(docs) == dict:
			text = [docs["message"]]
		else:
			text = []
			for doc in docs:
				try:
					text.append(doc["message"])
				except KeyError:
					continue
			text = re.split("\W+", " ".join(text))
		print "<split text>"
		trigram_measures = TrigramAssocMeasures()
		finder = TrigramCollocationFinder.from_words(text)
		finder.apply_freq_filter(freq[i])
		trigrams = finder.nbest(trigram_measures.pmi, 30)
		tri_tokens = nltk.trigrams(text)
		print "<printing trigram freqs>"
		for tri in trigrams:
			score = finder.score_ngram(trigram_measures.pmi, tri[0], tri[1], tri[2])
			print "< {}, {}, {} > freq= {}, score={}".format(tri[0], tri[1], tri[2], tri_tokens.count(tri), score)


def sentiment_analysis(cllxn):
	"""use text-processing.com API to get sentiment score for each post"""
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
	time.sleep(1)
	count = 0
	for doc in docs:
		count += 1
		print "analyzed {} documents".format(count)
		pt = get_sentiment(doc[0])
		if pt:
			DB.update(cllxn, {"id" : doc[1]}, { "$set" : { "sentiment" : round(pt, 1) }})
			data[round(pt, 1)] += 1
			print DB.find(cllxn, { "id" : doc[1]})

	slogger.info("total words={}".format(len(list(vocab))))
	slogger.info("total docs={}".format(len(docs)))
	slogger.info(data)


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
		if e == "popular_trigrams_by_sentiment":
			popular_trigrams_by_sentiment(cllxn)
		if e == "score_topics":
			score_topics(cllxn)








