import matplotlib.pyplot as plt
from collections import deque
from urlparse import urljoin
import networkx as nx
import urlparse
import urllib2
import re
import sys

class WikiPage:


	def __init__(self, link):
		self.link = link
		self.html = None
		self.distance = 0
		self.similarity = None

		if not self.load_content():
			print "HTTP error occurred while opening page: %s"  % self.link

	def load_content(self):

		location = urljoin('https://en.wikipedia.org/wiki/',self.link)
		request = urllib2.Request(location)
		try:
			self.html =  urllib2.urlopen(request).read()
			match = re.search('<h1 id="firstHeading" class="firstHeading" lang="en">(<.*>)*(.*)(<.*>)*</h1>',self.html)
			if match:
				self.name = match.group(2)
				return True

			else: return False
		except urllib2.HTTPError: return False

	def __str__(self):
		return self.title


class WikiGraph:

	def __init__(self,start,goal):
		self.graph = nx.Graph()
		self.nodes = set()
		self.edges = set()
		self.start = start
		self.goal = goal
		self.rec_heuristic = {}
		self.goal_categories = []

	def load_neighbors(self, page,limit):

		match = re.finditer('<p>.*<a href="/wiki/(\w+)" .*</p>',page.html)
		link_set = set()
		count = 0
		if match:
			for m in match:
				if count == limit: break
				count+=1
				link_set.add(m.group(1))

		neighbors = []
		for li in link_set:
			if li not in self.nodes:
				successor = WikiPage(li)
				if successor.html is not None:
					neighbors.append(successor)
					self.nodes.add(li)
		return neighbors

	def trace_path(self,path):

		final_nodes = []
		final_edges = []

		last = path[-2:]
		i = last[0]
		j = last[1]
		final_nodes.append(last)
		final_edges.append((i,j))
		edges_str = ""
		for tuple in self.edges:
			edges_str += '['+tuple[0]+','+tuple[1]+']'

		while i != self.start.link:
			match = re.finditer('[(\w+),'+i+']' ,edges_str)
			if match:
				min = len(path)
				for m in match:
					tup = m.group(0)
					if path.index(tup) < min:
						min = path.index(m.group(1))
						min_tuple = (m.group(1),i)
						final_edges.append(min_tuple)
						i = min_tuple[0]
						j = min_tuple[1]
		self.draw(final_nodes,final_edges)

	def bfs(self):
		frontier = deque()
		frontier.append(self.start)
		path = []
		print "Starting Breadth First Search from %s to %s"%(self.start.name,self.goal.name)

		while frontier:

			page = frontier.popleft()
			path.append(page.link)
			print "Searching in %s" % page.name
			match = re.search('<a href="/wiki/('+self.goal.link+')"',page.html)

			if match:
				found = match.group(1)
				print "Found goal %s!" % found
				goal_page = WikiPage(found)
				self.nodes.add(goal_page.name)
				self.edges.add((page.link,goal_page.link))
				path.append(self.goal.link)
				self.draw(self.nodes,self.edges)
				return True
			else:
				if page.name not in self.nodes: self.nodes.add(page.name)
				children = self.load_neighbors(page,5)
				for child in children:
					if child not in frontier:frontier.append(child)
					if child.name == '':child.name = child.link
					edge = (page.name,child.name)
					if child not in self.nodes : self.nodes.add(child.name)
					if edge not in self.edges : self.edges.add(edge)
		print "Page not found!"
		return False

	def categories(self, page):
		cats = set()
		match = re.search('<div id="mw-normal-catlinks" class="mw-normal-catlinks">(.*?)</div>',page.html)
		if match:
			div = match.group(1)
			cat = re.finditer('<a href="/wiki/Category:(\w+)"',div)
			if cat:
				for c in cat:
					cats.add(c.group(1))
		return cats

	def sortby_sim(self, open_nodes):
		ordered_tup = []
		ordered = []

		for o in open_nodes:
			similarity = 0
			if o.link not in self.rec_heuristic:
				start_cats = self.categories(o)
				inter = start_cats.intersection(self.goal_categories)
				similarity += len(inter)
				o.similarity = similarity
				self.rec_heuristic[o.link] = similarity
			ordered_tup.append((similarity,o))
		ordered_tup.sort(key=lambda x: x[0])
		for p in ordered_tup :
			ordered.append(p[1])
		return ordered


	def best_first(self):

		open_nodes = [self.start]
		closed = []
		path = []

		print "Starting Best First Search from %s to %s"%(self.start.name,self.goal.name)
		print "Obtaining information about goal: %s"%self.goal.name
		self.goal_categories =self.categories(self.goal)
		while open_nodes:

			open_nodes = self.sortby_sim(open_nodes)
			page = open_nodes.pop()
			closed.append(page)
			path.append(page.link)
			print "Selected page: %s with heuristic value: %s" % (page.name,page.similarity)
			match = re.search('<a href="/wiki/('+self.goal.link+')"',page.html)
			if match:
				found = match.group(1)
				print "Found goal %s!" % found
				goal_page = WikiPage(found)
				self.nodes.add(goal_page.name)
				self.edges.add((page.link,goal_page.link))
				path.append(self.goal.link)
				self.draw(self.nodes,self.edges)
				#self.trace_path(path)
				return True
			else:
				if page.name not in self.nodes: self.nodes.add(page.name)
				children = self.load_neighbors(page,10)
				for child in children:
					if child not in open_nodes and child not in closed:
						open_nodes.append(child)
						edge = (page.name,child.name)

						if child not in self.nodes : self.nodes.add(child.name)
						if edge not in self.edges : self.edges.add(edge)
		print "Page not found!"
		return False

	def draw(self,nodes,edges):
		self.graph.add_edges_from(edges)
		pos=nx.circular_layout(self.graph)

		# nodes
		nx.draw_networkx_nodes(self.graph,pos,node_size=700)
		nx.draw_networkx_edges(self.graph,pos,edgelist=self.edges,width=4,alpha=0.5,edge_color='b')
		nx.draw_networkx_labels(self.graph,pos,font_size=10,font_family='sans-serif')
		plt.axis('off')
		plt.show()

class WikiChallenge:

	def __init__(self):

		if len(sys.argv) != 4:
			print "Usage: python wiki.py -flag (-u for uninformed search, -i for informed search) start_page goal_page"
		else:
			if sys.argv[2] == sys.argv[3]:
				print "Start page and goal page can't be the same"
			else:
				self.start = WikiPage(sys.argv[2])
				self.goal = WikiPage(sys.argv[3])
				if self.start.html is None or self.goal.html is None:
					print "One of the pages wasn't loaded correctly, check the URL exists"
				else:
					self.graph = WikiGraph(self.start,self.goal)
					search = sys.argv[1]
					if search == '-u': self.graph.bfs()
					elif search == '-i': self.graph.best_first()
					else: print "Second argument options: -u or -i"


wiki = WikiChallenge()