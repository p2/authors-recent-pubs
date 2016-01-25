#!/usr/bin/env python3

import io
import csv
import requests

from urllib.parse import quote_plus

_entrez_authors = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={{term}}&retmode=json&retmax={{n_max}}'
_entrez_article = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={{pmid}}&retmode=json'


def search_entrez(url, root='esearchresult'):
	ret = requests.get(url)
	ret.raise_for_status()
	js = ret.json()
	rslt = js.get(root)
	if rslt is None:
		raise Exception("`esearchresult` not found in returned JSON: {}".format(js))
	return rslt

def get_summaries(pmid_list):
	assert pmid_list
	url = _entrez_article.replace('{{pmid}}', ','.join(pmid_list))
	rslt = search_entrez(url, root='result')
	uids = rslt.get('uids', [])
	if 0 == len(uids):
		return None
	
	articles = []
	for uid in uids:
		article = rslt.get(uid)
		article['pmid'] = uid		# I'm lazy
		articles.append(article)
	return articles

def get_recent(author, n_max):
	""" Assume author is "first last". TODO: detect "last, first".
	"""
	assert author
	assert n_max > 0
	names = author.strip().split(' ')
	terms = []
	
	# reverse and use initial(s)
	# TODO: detect names like "Da Silva"
	term = '"{} {}"[AU]'.format(names[-1], ''.join([n[0] for n in names[0:-1]]))
	terms.append(term)
	
	# query
	url = _entrez_authors.replace('{{term}}', quote_plus(' OR '.join(terms)))
	url = url.replace('{{n_max}}', str(n_max))
	rslt = search_entrez(url)
	idlist = rslt.get('idlist')
	if idlist is None or 0 == len(idlist):
		return None
	
	# fetch summaries
	return get_summaries(idlist)

def recent_to_markdown(author, affil, n_max=6):
	assert author
	assert affil
	articles = get_recent(author, n_max)
	mds = ["## {}, {} ##".format(author, affil)]
	if articles is None:
		mds.append('`none`')
	else:
		for article in articles:
			all_auths = article.get('authors', [])
			if len(all_auths) > 6:
				nice_authors = ', '.join([a.get('name') for a in all_auths[0:6]]) + ' et al'
			else:
				nice_authors = ', '.join([a.get('name') for a in all_auths])
			article['nice_authors'] = nice_authors
			
			mds.append("- {title}  \n  {nice_authors},  \n  {epubdate}, {source}\n  [{pmid}](http://www.pubmed.org/{pmid})".format(**article))
	return "\n\n".join(mds)


if '__main__' == __name__:
	source = 'authors.csv'
	target = 'authors.md'
	with io.open(source, 'r', encoding='utf-8', newline='') as author_list:
		print('->  reading', source)
		reader = csv.reader(author_list, delimiter='	')
		
		with io.open(target, 'w', encoding='utf-8') as full_list:
			full_list.write("# Recent Articles\n\n")
			for row in reader:
				md = recent_to_markdown(row[0], row[1])
				full_list.write(md)
				full_list.write("\n\n")
		
		print('->  written to', target)
