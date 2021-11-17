import time
import re
import pickle
import json
import random

class KnowledgeGraph:
	def __init__(self, file_path, dicts_path, HIGHEST_ID = 79305928, load_kg=True):
		self.HIGHEST_ID = HIGHEST_ID
		self.ENT_PATTERN = re.compile('^Q[0-9]+$')
		self.PRE_PATTERN = re.compile('^P[0-9]+$')
		# load dictionaries: integer -> Wikidata ID/literal
		# the name of the dictionaries is fix
		try:
			if load_kg:
				with open(dicts_path + "/inverse_entity_nodes.pickle", "rb") as infile:
					self.inv_ents = pickle.load(infile)
				with open(dicts_path + "/inverse_pred_nodes.pickle", "rb") as infile:
					self.inv_pres = pickle.load(infile)
				with open(dicts_path + "/inverse_literals.pickle", "rb") as infile:
					self.inv_lits = pickle.load(infile)
				with open(dicts_path + "/entity_nodes.pickle", "rb") as infile:
					self.entities_dict = pickle.load(infile)
				with open(dicts_path + "/pred_nodes.pickle", "rb") as infile:
					self.predicates_dict = pickle.load(infile)
				with open(dicts_path + "/literals.pickle", "rb") as infile:
					self.literals_dict = pickle.load(infile)
				with open(dicts_path + "/aliases.pickle", "rb") as infile:
					self.aliases_dict = pickle.load(infile)
				with open(dicts_path + "/labels.pickle", "rb") as infile:
					self.labels_dict = pickle.load(infile)
				with open(dicts_path + "/descriptions.pickle", "rb") as infile:
					self.descriptions_dict = pickle.load(infile)
			print("Dictionaries successfully loaded.")
		except:
			raise Exception("Paths to dictionaries are invalid! You might have changed the names of the dictionaries!")

		# initialize neighbor indices
		self.neighboring_facts_index = list()
		self.neighboring_items_index = list()
		for i in range(self.HIGHEST_ID):
			self.neighboring_facts_index.append(None)
			self.neighboring_items_index.append(None)
		# load neighbor indices
		self.load_kg = load_kg
		if load_kg:
			self.load_index_from_file_with_spo(file_path)
		self.connectivity_cache = dict()

	def is_entity(self, integer_encoded_item):
		return integer_encoded_item >= 10000

	def is_predicate(self, integer_encoded_item):
		return integer_encoded_item > 0 and integer_encoded_item < 10000

	def is_literal(self, integer_encoded_item):
		return integer_encoded_item < 0

	def item_to_integer(self, item):
		try:
			if item[0] == "Q" and re.match(self.ENT_PATTERN, item):
				return int(self.entities_dict[item])
			elif item[0] == "P" and re.match(self.PRE_PATTERN, item):
				return int(self.predicates_dict[item])
			elif len(item) < 40:
				return int(-self.literals_dict[item])
		except:
			return None

	def integer_to_item(self, integer_encoded_item):
		if self.is_entity(integer_encoded_item):
			return self.inv_ents[integer_encoded_item-10000]
		elif self.is_predicate(integer_encoded_item):
			return self.inv_pres[integer_encoded_item]
		elif self.is_literal(integer_encoded_item):
			return self.inv_lits[-integer_encoded_item]
		else:
			raise Exception("Failure in integer_to_item with integer_encoded_item: " + str(integer_encoded_item))
			return None

	def item_to_label(self, item):
		if item is None:
			return "None"
		integer_encoded_item = self.item_to_integer(item)
		if not integer_encoded_item:
			return "None"
		if self.is_literal(integer_encoded_item):
			return item
		labels = self.integer_to_label(integer_encoded_item)
		if not labels:
			return str(item)
		return labels

	def item_to_aliases(self, item):
		if item is None:
			return "None"
		integer_encoded_item = self.item_to_integer(item)
		aliases = self.integer_to_aliases(integer_encoded_item)
		if not aliases:
			return str(item)
		return aliases

	def item_to_description(self, item):
		if item is None:
			return "None"
		integer_encoded_item = self.item_to_integer(item)
		descriptions = self.integer_to_descriptions(integer_encoded_item)
		if not descriptions:
			return str(item)
		return descriptions

	def integer_to_label(self, integer_encoded_item):
		if not integer_encoded_item:
			return None
		labels = self.labels_dict[integer_encoded_item]
		return labels

	def integer_to_aliases(self, integer_encoded_item):
		if not integer_encoded_item:
			return None
		aliases = self.aliases_dict[integer_encoded_item]		
		return aliases

	def integer_to_descriptions(self, integer_encoded_item):
		if not integer_encoded_item:
			return None
		descriptions = self.descriptions_dict[integer_encoded_item]		
		return descriptions

	def translate_integer_encoded_fact(self, integer_encoded_fact):
		return [self.integer_to_item(integer_encoded_item) for integer_encoded_item in integer_encoded_fact]

	def connectivity_check_integers(self, integer_encoded_item1, integer_encoded_item2):
		neighbors1 = self.neighboring_items_index[integer_encoded_item1]
		neighbors2 = self.neighboring_items_index[integer_encoded_item2]
		if neighbors1 is None or neighbors2 is None:
			return 0
		len1 = len(neighbors1)
		len2 = len(neighbors2)
		if len1 > len2:
			if integer_encoded_item1 in neighbors2:
				return 1
		else:
			if integer_encoded_item2 in neighbors1:
				return 1
		if neighbors1 & neighbors2:
			return 0.5
		else:
			return 0

	def connectivity_check(self, item1, item2):
		if not self.load_kg:
			return random.randint(0, 100)/100
		if not item1 or not item2:
			return 0
		# check cache
		if self.connectivity_cache.get((item1, item2)):
			return self.connectivity_cache.get((item1, item2))
		elif self.connectivity_cache.get((item2, item1)):
			return self.connectivity_cache.get((item2, item1))
		# no hit in cache, compute!
		integer_encoded_item1 = self.item_to_integer(item1)
		integer_encoded_item2 = self.item_to_integer(item2)
		if integer_encoded_item1 is None or integer_encoded_item2 is None:
			return 0
		connectivity = self.connectivity_check_integers(integer_encoded_item1, integer_encoded_item2)
		# fill cache
		self.connectivity_cache[(item1, item2)] = connectivity
		return connectivity

	'''
	return a list of facts with item1 and item2
	'''
	def find_all_connections_1_hop(self, integer_encoded_item1, integer_encoded_item2):
		neighbors1 = self.neighboring_facts_index[integer_encoded_item1]['s'] + self.neighboring_facts_index[integer_encoded_item1]['o']
		neighbors2 = self.neighboring_facts_index[integer_encoded_item2]['s'] + self.neighboring_facts_index[integer_encoded_item2]['o']
		len1 = len(neighbors1)
		len2 = len(neighbors2)
		connections = list()
		if len1 > len2:
			for fact in neighbors2:
				if integer_encoded_item1 in fact:
					connections.append(self.translate_integer_encoded_fact(fact))
		else:
			for fact in neighbors1:
				if integer_encoded_item2 in fact:
					connections.append(self.translate_integer_encoded_fact(fact))
		return connections

	'''
	return a list of facts with item1 and item_between_item1_and_item2, 
	and a list of facts with item_between_item1_and_item2 and item2
	'''
	def find_all_connections_2_hop(self, integer_encoded_item1, integer_encoded_item2):
		connections = list()
		neighbors1 = self.neighboring_items_index[integer_encoded_item1]
		neighbors2 = self.neighboring_items_index[integer_encoded_item2]
		items_in_the_middle = neighbors1 & neighbors2
		if not items_in_the_middle:
			return connections
		for item_in_the_middle in items_in_the_middle:
			connection1 = self.find_all_connections_1_hop(integer_encoded_item1, item_in_the_middle)
			connection2 = self.find_all_connections_1_hop(item_in_the_middle, integer_encoded_item2)
			connection = [connection1, connection2]
			connections.append(connection)
		return connections

	'''
	return a list of 1-hop paths or 2-hop paths between the items
	'''
	def find_all_connections(self, item1, item2, hop=None):
		integer_encoded_item1 = self.item_to_integer(item1)
		integer_encoded_item2 = self.item_to_integer(item2)
		if not hop:
			hop = self.connectivity_check(item1, item2)
		if hop == 1:
			return self.find_all_connections_1_hop(integer_encoded_item1, integer_encoded_item2)
		elif hop == 0.5:
			return self.find_all_connections_2_hop(integer_encoded_item1, integer_encoded_item2)
		else:
			return None

	def is_known(self, item):
		if self.item_to_integer(item) is None:
			print("is known (self.item_to_integer(item")
			print(self.item_to_integer(item))
			return False
		else:
			return True

	def get_types(self, item):
		if item is None or not self.load_kg:
			return None
		integer_encoded_item = self.item_to_integer(item)
		if not integer_encoded_item:
			return None
		return self.get_types_integer(integer_encoded_item)

	def get_types_integer(self, item):
		types = list()
		# only facts with item as subject are relevant
		facts = self.neighboring_facts_index[item]['s']
		for fact in facts:
			# fetch predicate
			p_integer = fact[1]
			p = self.integer_to_item(p_integer)
			# if predicate is instance of
			if p == "P31":
				o_integer = fact[2]
				o = self.integer_to_item(o_integer)
				o_label = self.item_to_label(o)
				types.append([o, o_label])
			# if predicate is occupation
			if p == "P106":
				o_integer = fact[2]
				o = self.integer_to_item(o_integer)
				o_label = self.item_to_label(o)
				types.append([o, o_label])
		return types

	def get_neighborhood_integer(self, item, fact_limit):
		neighborhood = list()
		frequent = False
		if item is None:
			return neighborhood, frequent
		neighboring_facts = self.neighboring_facts_index[item]
		if neighboring_facts is None:
			return neighborhood, frequent
		if fact_limit:
			neighboring_facts_s = neighboring_facts['s']
			neighboring_facts_o = neighboring_facts['o']
			if len(neighboring_facts_o) > fact_limit:
				neighboring_facts = neighboring_facts_s
				frequent = True
			else:
				neighboring_facts = neighboring_facts_s + neighboring_facts_o
		else:
			neighboring_facts = neighboring_facts['s'] + neighboring_facts['o']

		for fact in neighboring_facts:
			translated_fact = [self.integer_to_item(integer_encoded_item) for integer_encoded_item in fact]
			neighborhood.append(translated_fact)
		return neighborhood, frequent

	def get_neighborhood(self, item, include_labels=False, fact_limit=10000):
		if item is None or not self.load_kg:
			return list()
		integer_encoded_item = self.item_to_integer(item)
		if not integer_encoded_item:
			return list()
		neighborhood, frequent = self.get_neighborhood_integer(integer_encoded_item, fact_limit=fact_limit)
		# used for API
		if include_labels:
			neighborhood_labels = list()
			for fact in neighborhood:
				fact_labels = [{'id': item, 'label': self.item_to_label(item)} for item in fact]
				neighborhood_labels.append(fact_labels)
			return neighborhood_labels
		return neighborhood

	def get_neighborhood_two_hop(self, item, include_labels=False, fact_limit=10000):
		one_hop = self.get_neighborhood(item, include_labels=include_labels, fact_limit=fact_limit)
		two_hop = one_hop
		next_hop_items = list()
		# extract the items for the next hop
		for fact in one_hop:
			for item in fact:
				item_id = item['id']
				if item_id[0] == "Q" and re.match(self.ENT_PATTERN, item_id):
					if not item_id in next_hop_items:
						next_hop_items.append(item_id)
		# get the two hop facts
		for item_id in next_hop_items:
			two_hop += self.get_neighborhood(item_id, include_labels=include_labels, fact_limit=fact_limit)
		return two_hop

	def extract_context_graph(self, context_tuple, fact_limit=10000, connect_items=False, include_labels=False):
		context_graph = list()
		frequent_items_encoded = list()
		context_anchors_encoded = list()
		for item in context_tuple:
			integer_encoded_item = self.item_to_integer(item)
			if integer_encoded_item is None:
				continue
			context_graph_item, item_is_frequent = self.get_neighborhood_integer(integer_encoded_item, fact_limit=fact_limit)
			context_graph += context_graph_item
			if connect_items:
				if item_is_frequent:
					frequent_items_encoded.append(integer_encoded_item)
				else:
					context_anchors_encoded.append(integer_encoded_item)
		# code only used if connect_items set to True
		for item in frequent_items_encoded:
			for context_anchor in context_anchors_encoded:
				context_graph += self.connect_items(item, context_anchor) 
		# used for API
		if include_labels:
			context_graph_labels = list()
			for fact in context_graph:
				fact_labels = [{'id': item, 'label': self.item_to_label(item)} for item in fact]
				context_graph_labels.append(fact_labels)
			return context_graph_labels
		return context_graph

	def extract_smart_context_graph(self, context_tuple, fact_limit=10000, connect_items=False, include_labels=False):
		context_graph = list()
		for item in context_tuple:
			integer_encoded_item = self.item_to_integer(item)
			if integer_encoded_item is None:
				continue
			context_graph_item, item_is_frequent = self.get_neighborhood_integer(integer_encoded_item, fact_limit=fact_limit)
			context_graph += context_graph_item
		filtered_facts = list()
		for fact in context_graph:
			# intersect tuple items and fact items
			intersection = set(fact) & set(context_tuple)
			if len(intersection) > 1:
				filtered_facts.append(fact)
		return filtered_facts

	def extract_full_context_graph(self, context_tuple):
		context_graph = list()
		frequent_items_encoded = list()
		context_anchors_encoded = list()
		for item in context_tuple:
			integer_encoded_item = self.item_to_integer(item)
			if integer_encoded_item is None:
				continue
			context_graph_item, item_is_frequent = self.get_neighborhood_integer(integer_encoded_item, fact_limit=False)
			context_graph += context_graph_item
		return context_graph

	def connect_items(self, frequent_item_integer_encoded, context_anchor_integer_encoded):
		start = time.time()
		connecting_facts = list()
		neighbors = self.neighboring_items_index[context_anchor_integer_encoded]
		for neighbor_integer_encoded in neighbors:
			if len(self.neighboring_facts_index[neighbor_integer_encoded]['o']) > 10000:
				continue
			else:
				neighborhood, item_is_frequent = self.get_neighborhood_integer(neighbor_integer_encoded, fact_limit=10000)
				for fact in neighborhood:
					if frequent_item_integer_encoded in fact:
						connecting_facts.append(fact)
		# connecting_facts = self.find_all_connections_2_hop(frequent_item_integer_encoded, context_anchor_integer_encoded)
		if connecting_facts:
			print("Time to connect_items")
			print(time.time() - start)
			print(str(self.integer_to_item(context_anchor_integer_encoded)) + ";" + str(self.integer_to_item(frequent_item_integer_encoded)))
			print(connecting_facts)
		return connecting_facts

	def frequency(self, item):
		integer_encoded_item = self.item_to_integer(item)
		if not integer_encoded_item:
			return [0, 0]
		neighboring_facts = self.neighboring_facts_index[integer_encoded_item]
		if neighboring_facts is None:
			return [0, 0]
		else:
			subject_frequency = len(neighboring_facts['s'])
			object_frequency = len(neighboring_facts['o'])
			return [subject_frequency, object_frequency]
			
	def load_index_from_file(self, file_path):
		print("KG loading started.")
		start = time.time()
		with open(file_path, "r") as kg:
			item = kg.readline()
			index = 0
			start_index = 0
			fact_length = 0
			fact_items = list()
			fact_entities = list()
			count = 0
			while item:
				curr_item = int(item[:-1])
				item = kg.readline()
				count += 1
				if fact_length < 3:
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
					fact_length += 1
				# was in qualifiers, new fact appears
				elif (fact_length-3) % 2 == 0 and self.is_entity(curr_item):
					for fact_item in fact_items:
						if self.is_literal(fact_item):
							continue
						# empty index -> initialize
						try:
							if self.neighboring_facts_index[fact_item] is None:
								self.neighboring_facts_index[fact_item] = list()
								self.neighboring_items_index[fact_item] = set()
							self.neighboring_facts_index[fact_item].append(fact_items)
							self.neighboring_items_index[fact_item].update(fact_entities)
						except:
							raise Exception("Fail with ngb_index[fact_item]: " + str(fact_item))
					index = index + 1
					start_index = index
					fact_length = 1
					fact_items = list()
					fact_entities = list()
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
				# in qualifiers, new qualifier predicate/object appears
				else:
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
					fact_length += 1
				index += 1
				if count % 100000000 == 0:
					print (str(count) + " lines loaded...")
		print("Successfully loaded neighboring_facts_index and neighboring_items_index in " + str(time.time() - start) + " seconds.")

	def load_index_from_file_with_spo(self, file_path):
		print("KG loading started.")
		start = time.time()
		with open(file_path, "r") as kg:
			item = kg.readline()
			index = 0
			start_index = 0
			fact_length = 0
			fact_items = list()
			fact_entities = list()
			count = 0
			while item:
				curr_item = int(item[:-1])
				item = kg.readline()
				count += 1
				if fact_length < 3:
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
					fact_length += 1
				# was in qualifiers, new fact appears
				elif (fact_length-3) % 2 == 0 and self.is_entity(curr_item):
					for fact_item_index, fact_item in enumerate(fact_items):
						if self.is_literal(fact_item):
							continue
						# empty index -> initialize
						try:
							if self.neighboring_facts_index[fact_item] is None:
								self.neighboring_facts_index[fact_item] = dict()
								self.neighboring_facts_index[fact_item]['s'] = list()
								self.neighboring_facts_index[fact_item]['o'] = list()
								self.neighboring_items_index[fact_item] = set()
							if fact_item_index == 0:
								self.neighboring_facts_index[fact_item]['s'].append(fact_items)
							else:
								self.neighboring_facts_index[fact_item]['o'].append(fact_items)
							self.neighboring_items_index[fact_item].update(fact_entities)
						except:
							raise Exception("Fail with ngb_index[fact_item]: " + str(fact_item))
					index = index + 1
					start_index = index
					fact_length = 1
					fact_items = list()
					fact_entities = list()
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
				# in qualifiers, new qualifier predicate/object appears
				else:
					fact_items.append(curr_item)
					if self.is_entity(curr_item):
						fact_entities.append(curr_item)
					fact_length += 1
				index += 1
				if count % 100000000 == 0:
					print (str(count) + " lines loaded...")
		print("Successfully loaded neighboring_facts_index and neighboring_items_index in " + str(time.time() - start) + " seconds.")