import json
import pickle
import random
import re
import sys
import time


class KnowledgeBase:
    """This class encapsulates the logic of the efficient KB index as described in the CLOCQ paper (Christmann et al., WSDM 2022)."""

    def __init__(self, path_to_kb_list, path_to_kb_dicts, max_items=None, verbose=False):
        # define regular expressions
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        # load data
        try:
            with open(path_to_kb_dicts + "/HIGHEST_ID.txt", "r") as fp:
                HIGHEST_ID = fp.readline().strip()
                self.HIGHEST_ID = int(HIGHEST_ID)
            with open(path_to_kb_dicts + "/inverse_entity_nodes.pickle", "rb") as fp:
                self.inv_ents = pickle.load(fp)
            with open(path_to_kb_dicts + "/inverse_pred_nodes.pickle", "rb") as fp:
                self.inv_pres = pickle.load(fp)
            with open(path_to_kb_dicts + "/inverse_literals.pickle", "rb") as fp:
                self.inv_lits = pickle.load(fp)
            with open(path_to_kb_dicts + "/entity_nodes.pickle", "rb") as fp:
                self.entities_dict = pickle.load(fp)
            with open(path_to_kb_dicts + "/pred_nodes.pickle", "rb") as fp:
                self.predicates_dict = pickle.load(fp)
            with open(path_to_kb_dicts + "/literals.pickle", "rb") as fp:
                self.literals_dict = pickle.load(fp)
            with open(path_to_kb_dicts + "/labels.pickle", "rb") as fp:
                self.labels_list = pickle.load(fp)
            with open(path_to_kb_dicts + "/aliases.pickle", "rb") as fp:
                self.aliases_list = pickle.load(fp)
            with open(path_to_kb_dicts + "/descriptions.pickle", "rb") as fp:
                self.descriptions_list = pickle.load(fp)
            print("Dictionaries successfully loaded.")
        except:
            raise Exception(
                "Paths to dictionaries are invalid! You might have changed the names or paths of the dictionaries!"
            )
        # remember settings
        self.verbose = verbose
        # initialize neighbor indices
        self.neighboring_facts_index = list()
        self.neighboring_items_index = list()
        for i in range(self.HIGHEST_ID):
            self.neighboring_facts_index.append(None)
            self.neighboring_items_index.append(None)
        # load neighbor indices
        self._load_KB_index_from_file(path_to_kb_list, max_items)
        # initialize runtime cache for connectivity
        self.connectivity_cache = dict()


    def _is_entity(self, integer_encoded_item):
        """Return whether encoded item is entity."""
        return integer_encoded_item >= 10000

    def _is_predicate(self, integer_encoded_item):
        """Return whether encoded item is predicate."""
        return integer_encoded_item > 0 and integer_encoded_item < 10000

    def _is_literal(self, integer_encoded_item):
        """Return whether encoded item is literal."""
        return integer_encoded_item < 0

    def _item_to_integer(self, item):
        """Encode the KB-item."""
        try:
            if item[0] == "Q" and re.match(self.ENT_PATTERN, item):
                return int(self.entities_dict[item])
            elif item[0] == "P" and re.match(self.PRE_PATTERN, item):
                return int(self.predicates_dict[item])
            elif len(item) < 40:
                return int(-self.literals_dict[item])
        except:
            return None

    def _integer_to_item(self, integer_encoded_item):
        """Decode the integer to the KB-item."""
        if self._is_entity(integer_encoded_item):
            return self.inv_ents[integer_encoded_item - 10000]
        elif self._is_predicate(integer_encoded_item):
            return self.inv_pres[integer_encoded_item]
        elif self._is_literal(integer_encoded_item):
            return self.inv_lits[-integer_encoded_item]
        else:
            raise Exception("Failure in _integer_to_item with integer_encoded_item: " + str(integer_encoded_item))

    def item_to_labels(self, item):
        """Retrieve labels of Wikidata ID."""
        if item is None:
            return ["None"]
        # get integer encoding
        integer_encoded_item = self._item_to_integer(item)
        if not integer_encoded_item:
            return [str(item)]
        # literals can be returned directly
        if self._is_literal(integer_encoded_item):
            return [str(item)]
        # call efficient function
        labels = self._integer_to_labels(integer_encoded_item)
        if not labels:
            return [str(item)]
        return labels

    def item_to_single_label(self, item):
        """Retrieve first label of Wikidata ID."""
        labels = self.item_to_labels(item)
        if labels == ["None"]:
            return "None"
        # make sure first label is not a Wikidata ID (e.g. Q5)
        first_label = next(
            (label for label in labels if not (self.ENT_PATTERN.match(label) or self.PRE_PATTERN.match(label))),
            labels[0]
        )
        return first_label

    def _integer_to_labels(self, integer_encoded_item):
        """Look-up labels for integer encoded item in list."""
        if not integer_encoded_item:
            return None
        labels = self.labels_list[integer_encoded_item]
        return labels

    def item_to_aliases(self, item):
        """Retrieve aliases of Wikidata ID."""
        if item is None:
            return "None"
        # get integer encoding
        integer_encoded_item = self._item_to_integer(item)
        # call efficient function
        aliases = self._integer_to_aliases(integer_encoded_item)
        if not aliases:
            return [str(item)]
        return aliases

    def _integer_to_aliases(self, integer_encoded_item):
        """Look-up aliases for integer encoded item in list."""
        if not integer_encoded_item:
            return None
        aliases = self.aliases_list[integer_encoded_item]
        return aliases

    def item_to_description(self, item):
        """Retrieve Wikidata description for Wikidata ID."""
        if item is None:
            return "None"
        # get integer encoding
        integer_encoded_item = self._item_to_integer(item)
        # call efficient function
        description = self._integer_to_description(integer_encoded_item)
        if not description:
            return "None"
        return description

    def _integer_to_description(self, integer_encoded_item):
        """Look-up Wikidata description for integer encoded item in list."""
        if not integer_encoded_item:
            return None
        description = self.descriptions_list[integer_encoded_item]
        return description

    def item_to_types(self, item):
        """Retrieve Wikidata types for Wikidata ID."""
        if item is None:
            return []
        # get integer encoding
        integer_encoded_item = self._item_to_integer(item)
        if not integer_encoded_item:
            return []
        # call efficient function
        types = self._integer_to_types(integer_encoded_item)
        if not types:
            return []
        return types

    def _integer_to_types(self, integer_encoded_item):
        """Look-up Wikidata types for integer encoded item in list."""
        types = list()
        # only facts with item as subject are relevant
        facts = self.neighboring_facts_index[integer_encoded_item]
        if facts is None:
            return []
        facts = facts["s"]
        for fact in facts:
            # fetch predicate
            p_integer = fact[1]
            p = self._integer_to_item(p_integer)
            # if predicate is 'instance of'
            if p == "P31":
                o_integer = fact[2]
                o = self._integer_to_item(o_integer)
                o_label = self.item_to_single_label(o)
                types.append({"id": o, "label": o_label})
            # if predicate is 'occupation' (for humans)
            if p == "P106":
                o_integer = fact[2]
                o = self._integer_to_item(o_integer)
                o_label = self.item_to_single_label(o)
                types.append({"id": o, "label": o_label})
        return types

    def frequency(self, item):
        """
        Returns frequency of KB-item in Wikidata.
        Returns: [frequency as subject, frequency as (qualifier-)object]"""
        integer_encoded_item = self._item_to_integer(item)
        if not integer_encoded_item:
            return [0, 0]
        neighboring_facts = self.neighboring_facts_index[integer_encoded_item]
        if neighboring_facts is None:
            return [0, 0]
        else:
            subject_frequency = len(neighboring_facts["s"])
            object_frequency = len(neighboring_facts["o"])
            return [subject_frequency, object_frequency]

    def is_known(self, item):
        """Returns whether item is known in the Wikidata dump used."""
        integer = self._item_to_integer(item)
        # no mapping known
        if integer is None:
            return False
        # no facts with the item
        elif self.neighboring_facts_index[integer] is None:
            return False
        else:
            return True

    def connectivity_check(self, item1, item2):
        """
        Check connectivity between the two items.
        Returns:	1 	if items in 1-hop,
                    0.5 if items in 2-hop,
                    0 	else
        """
        if not item1 or not item2:
            return 0
        # check cache
        if self.connectivity_cache.get((item1, item2)):
            return self.connectivity_cache.get((item1, item2))
        elif self.connectivity_cache.get((item2, item1)):
            return self.connectivity_cache.get((item2, item1))
        # no hit in cache, compute!
        integer_encoded_item1 = self._item_to_integer(item1)
        integer_encoded_item2 = self._item_to_integer(item2)
        if integer_encoded_item1 is None or integer_encoded_item2 is None:
            return 0
        connectivity = self._connectivity_check_integers(integer_encoded_item1, integer_encoded_item2)
        # fill cache
        self.connectivity_cache[(item1, item2)] = connectivity
        return connectivity

    def _connectivity_check_integers_old(self, integer_encoded_item1, integer_encoded_item2):
        """Check connectivity between the two encoded items. DEFAULT."""
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

    def _connectivity_check_integers(self, integer_encoded_item1, integer_encoded_item2):
        """Check connectivity between the two encoded items."""
        neighbors1 = self.neighboring_items_index[integer_encoded_item1]
        neighbors2 = self.neighboring_items_index[integer_encoded_item2]
        if neighbors1 is None or neighbors2 is None:
            return 0
        if integer_encoded_item1 in neighbors2 or integer_encoded_item2 in neighbors1:
            return 1
        if neighbors1 & neighbors2:
            return 0.5
        else:
            return 0

    def find_all_connections(self, item1, item2, hop=None):
        """Return a list of 1-hop paths or 2-hop paths between the items."""
        integer_encoded_item1 = self._item_to_integer(item1)
        integer_encoded_item2 = self._item_to_integer(item2)
        if not hop:
            hop = self.connectivity_check(item1, item2)
        if hop == 1:
            return self._integer_find_connections_1_hop(integer_encoded_item1, integer_encoded_item2)
        elif hop == 0.5:
            return self._integer_find_connections_2_hop(integer_encoded_item1, integer_encoded_item2)
        else:
            return None

    def _integer_find_connections_1_hop(self, integer_encoded_item1, integer_encoded_item2):
        """Return a list of facts with item1 and item2."""
        neighbors1 = (
            self.neighboring_facts_index[integer_encoded_item1]["s"]
            + self.neighboring_facts_index[integer_encoded_item1]["o"]
        )
        neighbors2 = (
            self.neighboring_facts_index[integer_encoded_item2]["s"]
            + self.neighboring_facts_index[integer_encoded_item2]["o"]
        )
        len1 = len(neighbors1)
        len2 = len(neighbors2)
        connections = list()
        if len1 > len2:
            for fact in neighbors2:
                if integer_encoded_item1 in fact:
                    connections.append(self.decode_integer_encoded_fact(fact))
        else:
            for fact in neighbors1:
                if integer_encoded_item2 in fact:
                    connections.append(self.decode_integer_encoded_fact(fact))
        return connections

    def _integer_find_connections_2_hop(self, integer_encoded_item1, integer_encoded_item2):
        """
        Return a list of facts with item1 and item_between_item1_and_item2,
        and a list of facts with item_between_item1_and_item2 and item2.
        """
        connections = list()
        neighbors1 = self.neighboring_items_index[integer_encoded_item1]
        neighbors2 = self.neighboring_items_index[integer_encoded_item2]
        items_in_the_middle = neighbors1 & neighbors2
        if not items_in_the_middle:
            return connections
        for item_in_the_middle in items_in_the_middle:
            connection1 = self._integer_find_connections_1_hop(integer_encoded_item1, item_in_the_middle)
            connection2 = self._integer_find_connections_1_hop(item_in_the_middle, integer_encoded_item2)
            connection = [connection1, connection2]
            connections.append(connection)
        return connections

    def extract_search_space(self, kb_item_tuple, p=1000, include_labels=False):
        """Extract the search space for the given KB-item tuple."""
        search_space = list()
        # retrieve neighborhood for each item
        for item in kb_item_tuple:
            # decode item
            integer_encoded_item = self._item_to_integer(item)
            if integer_encoded_item is None:
                continue
            facts, item_is_frequent = self._get_neighborhood_integer(integer_encoded_item, p=p)
            search_space += facts
        # include labels for more efficient access
        if include_labels:
            search_space = [self._add_labels_to_fact(fact) for fact in search_space]
        return search_space

    def extract_connected_search_space(self, kb_item_tuple, p=1000, include_labels=False):
        """Extract a connected search space for the given KB-item tuple."""
        search_space = list()
        for item in kb_item_tuple:
            # decode item
            integer_encoded_item = self._item_to_integer(item)
            if integer_encoded_item is None:
                continue
            facts, item_is_frequent = self._get_neighborhood_integer(integer_encoded_item, p=p)
            search_space += facts
        filtered_facts = list()
        for fact in search_space:
            # intersect tuple items and fact items
            intersection = set(fact) & set(kb_item_tuple)
            if len(intersection) > 1:
                filtered_facts.append(fact)
        return filtered_facts

    def get_neighborhood(self, item, p=1000, include_labels=False):
        """Retrieve 1-hop KB neighborhood of the KB-item."""
        if item is None:
            return list()
        integer_encoded_item = self._item_to_integer(item)
        if not integer_encoded_item:
            return list()
        neighborhood, frequent = self._get_neighborhood_integer(integer_encoded_item, p=p)
        # used for API
        if include_labels:
            neighborhood = [self._add_labels_to_fact(fact) for fact in neighborhood]
        return neighborhood

    def get_neighborhood_two_hop(self, item, p=1000, include_labels=False):
        """Retrieve 2-hop KB neighborhood of the KB-item."""
        one_hop = self.get_neighborhood(item, p=p, include_labels=include_labels)
        # remember items seen
        two_hop = one_hop
        next_hop_items = list()
        # extract the items for the next hop
        for fact in one_hop:
            for item_ in fact:
                item_id = item_["id"]
                if item_id[0] == "Q" and re.match(self.ENT_PATTERN, item_id):
                    if not item_id in next_hop_items:
                        next_hop_items.append(item_id)
        # get the two hop facts
        for item_id in next_hop_items:
            facts = self.get_neighborhood(item_id, p=p, include_labels=include_labels)
            new_facts = list()
            # remove duplicates (facts with item)
            for fact in facts:
                ids = fact
                if include_labels:
                    ids = [it["id"] for it in fact]
                if item in set(ids):
                    continue
                new_facts.append(fact)
            two_hop += new_facts
        return two_hop

    def _get_neighborhood_integer(self, item, p):
        """
        Retrieve 1-hop neighborhood of integer encoded item, making use
        of pruning parameter p. Returns (pruned) neighborhood, and boolean
        that indicates whether facts have been pruned.
        """
        neighborhood = list()
        facts_pruned = False
        if item is None:
            return neighborhood, facts_pruned
        # retrieve facts
        neighboring_facts = self.neighboring_facts_index[item]
        if neighboring_facts is None:
            return neighborhood, facts_pruned
        # prune noisy facts with parameter p
        if p:
            neighboring_facts_s = neighboring_facts["s"]
            neighboring_facts_o = neighboring_facts["o"]
            if len(neighboring_facts_o) > p:
                neighboring_facts = neighboring_facts_s
                facts_pruned = True
            else:
                neighboring_facts = neighboring_facts_s + neighboring_facts_o
        else:
            neighboring_facts = neighboring_facts["s"] + neighboring_facts["o"]
        # decode facts
        for fact in neighboring_facts:
            decoded_fact = self._decode_integer_encoded_fact(fact)
            neighborhood.append(decoded_fact)
        return neighborhood, facts_pruned

    def _decode_integer_encoded_fact(self, integer_encoded_fact):
        """Decode an integer integer encoded fact -> list(<Wikidata ID>)."""
        return [self._integer_to_item(integer_encoded_item) for integer_encoded_item in integer_encoded_fact]

    def _add_labels_to_fact(self, fact):
        """Retrieve labels for each element in the fact and add."""
        return [{"id": item, "label": self.item_to_single_label(item)} for item in fact]

    def _load_KB_index_from_file(self, file_path, max_items):
        """Load the KB indexes (= Wikidata KB) from file."""
        print("KB loading started.")
        start = time.time()
        with open(file_path, "r") as kb_list:
            item = kb_list.readline()

            # initialization
            fact_length = 0
            count = 0
            fact_items = list()
            fact_entities = list()

            # iterate through list of items
            while item:
                curr_item = int(item[:-1])
                item = kb_list.readline()
                count += 1

                # determine current status
                if fact_length < 3:
                    # main fact is not yet finished
                    fact_items.append(curr_item)
                    if self._is_entity(curr_item):
                        fact_entities.append(curr_item)
                    fact_length += 1

                elif (fact_length - 3) % 2 == 0 and self._is_entity(curr_item):
                    # new fact detected (two successive entities) -> store prev. fact
                    for fact_item_index, fact_item in enumerate(fact_items):
                        if self._is_literal(fact_item):
                            continue
                        # empty index -> initialize
                        try:
                            if self.neighboring_facts_index[fact_item] is None:
                                self.neighboring_facts_index[fact_item] = dict()
                                self.neighboring_facts_index[fact_item]["s"] = list()
                                self.neighboring_facts_index[fact_item]["o"] = list()
                                self.neighboring_items_index[fact_item] = set()
                            if fact_item_index == 0:
                                # index facts the item occurs in as subject (s)
                                self.neighboring_facts_index[fact_item]["s"].append(fact_items)
                            else:
                                # index facts the item occurs in as object or qualifier-object (o)
                                self.neighboring_facts_index[fact_item]["o"].append(fact_items)
                            self.neighboring_items_index[fact_item].update(fact_entities)
                        except:
                            raise Exception("Fail with ngb_index[fact_item]: " + str(fact_item))

                    # initialize new fact with first item (entity)
                    fact_length = 1
                    fact_items = list()
                    fact_entities = list()
                    fact_items.append(curr_item)
                    if self._is_entity(curr_item):
                        fact_entities.append(curr_item)
                else:
                    # in qualifiers, new qualifier predicate/object appears
                    fact_items.append(curr_item)
                    if self._is_entity(curr_item):
                        fact_entities.append(curr_item)
                    fact_length += 1

                # print status
                if count % 100000000 == 0:
                    self._print_verbose(f"{count} lines loaded...")

                # stop loading if maximum is reached
                if count == max_items:
                    break
        print(f"Successfully loaded KB index in {time.time() - start} seconds.")

    def _print_verbose(self, string):
        """Print only if verbose is set."""
        if self.verbose:
            print(string)


if __name__ == "__main__":
    # kb = KnowledgeBase()
    kb = KnowledgeBase(max_items=10)

    print("done loading")
    
    # with open("kb_loading.txt", "w") as fp:
        # fp.write("loaded\n")

    while True:
        time.sleep(1000)

