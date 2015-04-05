import json
import csv

with open("topic_markov.json", "r") as infile:
	data = json.load(infile)
	print(data)
	with open("topic_markov.csv", "wb+") as outfile:
		writer = csv.writer(outfile, delimiter=",") 
		writer.writerow(["from_topic","to_topic","count"])
		for from_topic in data:
			for to_topic in data[from_topic]:
				writer.writerow([from_topic, to_topic, data[from_topic][to_topic]])


