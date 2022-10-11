import pickle
import random
import re
import time
from itertools import chain


from hdt import HDTDocument


class KnowledgeBaseHDT:
    def __init__(self, path_to_hdt, path_to_kb_dicts, string_lib):
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        self.document = HDTDocument(path_to_hdt)
        self.string_lib = string_lib
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
            with open(path_to_kb_dicts + "/labels.pickle", "rb") as fp:
                self.labels_dict = pickle.load(fp)
            print("Dictionaries successfully loaded.")
        except:
            raise Exception("Paths to dictionaries are invalid! You might have changed the names of the dictionaries!")

    def item_to_single_label(self, item):
        if item is None:
            return "None"
        labels = self.labels_dict.get(item)
        if not labels:
            return "None"
        first_label = next(
            (label for label in labels if not (self.ENT_PATTERN.match(label) or self.PRE_PATTERN.match(label))),
            labels[0]
        )
        return first_label

    def _is_entity(self, integer_encoded_item):
        """Return whether encoded item is entity."""
        return integer_encoded_item >= 10000

    def _is_predicate(self, integer_encoded_item):
        """Return whether encoded item is predicate."""
        return integer_encoded_item > 0 and integer_encoded_item < 10000

    def _is_literal(self, integer_encoded_item):
        """Return whether encoded item is literal."""
        return integer_encoded_item < 0

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

    def connectivity_check(self, item1, item2):
        ngb_facts_1 = self.get_neighborhood(item1)
        ngb_facts_2 = self.get_neighborhood(item2)
        ngb_items_1 = self._facts_to_item_set(ngb_facts_1)
        ngb_items_2 = self._facts_to_item_set(ngb_facts_2)
        if item1 in ngb_items_2:
            return 1.0
        intersection = ngb_items_1 & ngb_items_2
        res = [i for i in list(intersection) if i and i[0] != "P"]
        if res:
            return 0.5
        return 0

    def distance(self, item1, item2, depth=0):
        """Compute the distance between the two items."""
        if depth == 7: # fallback to avoid getting stuck in recursion
            return 7
        conn = self.connectivity_check(item1, item2)
        if conn == 1.0:
            return 1
        elif conn == 0.5:
            return 2
        ngb_facts_1 = self.get_neighborhood(item1)
        ngb_facts_2 = self.get_neighborhood(item2)
        ngb_items_1 = self._facts_to_item_set(ngb_facts_1)
        ngb_items_2 = self._facts_to_item_set(ngb_facts_2)
        if len(ngb_items_1) + len(ngb_items_2) == 0: return 0
        if len(ngb_items_1) < len(ngb_items_2):
            if len(ngb_items_1) > 0: 
                return min([self.distance(item, item2, depth=depth+1) for item in ngb_items_1]) + 1
            else:
                return min([self.distance(item, item1, depth=depth+1) for item in ngb_items_2]) + 1
        else:
            if len(ngb_items_2) > 0:
                return min([self.distance(item, item1, depth=depth+1) for item in ngb_items_2]) + 1
            else:
                return min([self.distance(item, item2, depth=depth+1) for item in ngb_items_1]) + 1

    def get_frequency(self, item):
        entity = "http://www.wikidata.org/entity/" + item
        triples_sub, cardinality1 = self.document.search_triples(entity, "", "")
        triples_obj, cardinality2 = self.document.search_triples("", "", entity)
        return [cardinality1, cardinality2]

    def get_neighborhood(self, item, p=1000, include_labels=False):
        ngb_facts = list()
        if not item:
            return ngb_facts
        if self.ENT_PATTERN.match(item):
            ngb_facts = self._query_hdt_library_with_qualifiers_entity(item)
        elif self.PRE_PATTERN.match(item):
            ngb_facts = self._query_hdt_library_with_qualifiers_predicate(item)
        else:
            return ngb_facts
        cleaned_ngb_facts = list()
        for fact in ngb_facts:
        	cleaned_fact = [self.string_lib.wikidata_url_to_wikidata_id(item) for item in fact]
        	cleaned_ngb_facts.append(cleaned_fact)
        return cleaned_ngb_facts

    def connect(self, item1, item2, hop=None):
        """Return a list of 1-hop paths or 2-hop paths between the items."""
        if not hop:
            hop = self.connectivity_check(item1, item2)
        if hop == 1:
            return self._find_connections_1_hop(item1, item2)
        elif hop == 0.5:
            return self._find_connections_2_hop(item1, item2)
        else:
            return None

    def _find_connections_1_hop(self, item1, item2):
        """Return a list of facts with item1 and item2."""
        neighborhood1 = self.get_neighborhood(item1)
        neighborhood2 = self.get_neighborhood(item2)
        len1 = len(neighborhood1)
        len2 = len(neighborhood2)
        connections = list()
        if len1 > len2:
            for fact in neighborhood2:
                if item1 in fact:
                    connections.append(fact)
        else:
            for fact in neighborhood1:
                if item2 in fact:
                    connections.append(fact)
        return connections

    def _find_connections_2_hop(self, item1, item2):
        """
        Return a list of facts with item1 and item_between_item1_and_item2,
        and a list of facts with item_between_item1_and_item2 and item2.
        """
        connections = list()
        neighbors1 = set([item for fact in self.get_neighborhood(item1) for item in fact])
        neighbors2 = set([item for fact in self.get_neighborhood(item2) for item in fact])
        items_in_the_middle = neighbors1 & neighbors2
        if not items_in_the_middle:
            return connections
        for item_in_the_middle in items_in_the_middle:
            # skip extremely frequent items
            if sum(self.get_frequency(item_in_the_middle)) > 100000:
                continue
            connections1 = self._find_connections_1_hop(item1, item_in_the_middle)
            connections2 = self._find_connections_1_hop(item_in_the_middle, item2)
            connection = [connections1, connections2]
            connections.append(connection)
        return connections

    def extract_search_space(self, kb_item_tuple, p=1000, include_labels=False):
        context_graph = list()
        for item in kb_item_tuple:
            search_space += self.get_neighborhood(item, p=p, include_labels=include_labels)
        return search_space

    def _facts_to_item_set(self, facts):
        items = set()
        for fact in facts:
            items.update(fact)
        return items

    def _wikidata_entry_to_id(self, entry):
        if "XMLSchema" in entry:
            return entry.split("^^")[0]
        else:
            wikidata_id = entry.split("/")[-1]
            return wikidata_id

    def _query_hdt_library_with_qualifiers_entity(self, entity_id):
        entity = "http://www.wikidata.org/entity/" + entity_id
        triples_sub, cardinality1 = self.document.search_triples(entity, "", "")
        triples_obj, cardinality2 = self.document.search_triples("", "", entity)
        triples_sub = list(triples_sub)
        triples = []
        facts = list()
        for triple in triples_sub:
            s, p, o = triple
            if not p.startswith("http://www.wikidata.org"):
                continue
            s = self._wikidata_entry_to_id(s)
            p = self._wikidata_entry_to_id(p)
            if o.startswith("http://www.wikidata.org/entity/statement"):
                fact = [s, p, o]
                triples_qualifier = self._query_hdt_qualifier_obj(o)
                for qs, qp, qo in triples_qualifier:
                    qo = self._wikidata_entry_to_id(qo)
                    qp = self._wikidata_entry_to_id(qp)
                    if len(qo) == 32 and qo[0] != "Q":
                        continue
                    if qp == p:
                        fact[2] = qo
                    elif qp.startswith("http://www.wikidata.org"):
                        fact.append(qp)
                        fact.append(qo)
            else:
                o = self._wikidata_entry_to_id(o)
                fact = [s, p, o]
            facts.append(fact)
        triples_obj = list(triples_obj)
        facts_obj = list()
        # check whether cardinality2 is lower than 100,000
        # This is an upper bound, since 10,000 triples may be substantially less than 10,000 facts
        for triple in triples_obj:
            s, p, o = triple
            if not p.startswith("http://www.wikidata.org"):
                continue
            o = self._wikidata_entry_to_id(o)
            p = self._wikidata_entry_to_id(p)
            if s.startswith("http://www.wikidata.org/entity/statement/"):
                # p and o are qualifiers
                qp = p
                qo = o
                triples_qualifier_sub, triples_qualifier_obj = self._query_hdt_qualifier_sub(s)
                # exactly one fact with dummy node as object in wikidata
                s, p, dummy = triples_qualifier_obj[0]
                s = self._wikidata_entry_to_id(s)
                p = self._wikidata_entry_to_id(p)
                # original triple is remaining part of main statement
                if p == qp:
                    o = qo
                    fact = [s, p, o]
                    qualifiers = []
                else:
                    fact = [s, p]
                    qualifiers = [qp, qo]

                for dummy, qp, qo in triples_qualifier_sub:
                    qo = self._wikidata_entry_to_id(qo)
                    if len(qo) == 32 and qo[0] != "Q":
                        continue
                    if self._wikidata_entry_to_id(qp) == p:
                        fact.append(qo)
                    elif qp.startswith("http://www.wikidata.org"):
                        qp = self._wikidata_entry_to_id(qp)
                        qualifiers.append(qp)
                        qualifiers.append(qo)
                fact += qualifiers
            else:
                s = self._wikidata_entry_to_id(s)
                fact = [s, p, o]
            facts_obj.append(fact)
        return facts

    def _query_hdt_library_with_qualifiers_predicate(self, predicate_id):
        predicate = "http://www.wikidata.org/prop/direct/" + predicate_id
        triples1, cardinality1 = self.document.search_triples("", predicate, "")
        qualifier_predicate = "http://www.wikidata.org/prop/qualifier/" + predicate_id
        triples2, cardinality2 = self.document.search_triples("", predicate, "")

        facts = list()
        for triple in chain(triples1, triples2):
            s, p, o = triple
            if not p.startswith("http://www.wikidata.org"):
                continue
            o = self._wikidata_entry_to_id(o)
            p = self._wikidata_entry_to_id(p)
            if s.startswith("http://www.wikidata.org/entity/statement/"):
                # p and o are qualifiers
                qp = p
                qo = o
                triples_qualifier_sub, triples_qualifier_obj = self._query_hdt_qualifier_sub(s)
                # exactly one fact with dummy node as object in wikidata
                s, p, dummy = triples_qualifier_obj[0]
                s = self._wikidata_entry_to_id(s)
                p = self._wikidata_entry_to_id(p)
                # original triple is remaining part of main statement
                if p == qp:
                    o = qo
                    fact = [s, p, o]
                    qualifiers = []
                else:
                    fact = [s, p]
                    qualifiers = [qp, qo]

                for dummy, qp, qo in triples_qualifier_sub:
                    qo = self._wikidata_entry_to_id(qo)
                    if len(qo) == 32 and qo[0] != "Q":
                        continue
                    if self._wikidata_entry_to_id(qp) == p:
                        fact.append(qo)
                    elif qp.startswith("http://www.wikidata.org"):
                        qp = self._wikidata_entry_to_id(qp)
                        qualifiers.append(qp)
                        qualifiers.append(qo)
                fact += qualifiers
            else:
                s = self._wikidata_entry_to_id(s)
                fact = [s, p, o]
            facts.append(fact)
        return facts

    def _query_hdt_qualifier_obj(self, qualifier_statement):
        triples, cardinality = self.document.search_triples(qualifier_statement, "", "")
        return list(triples)

    def _query_hdt_qualifier_sub(self, qualifier_statement):
        triples_sub, cardinality = self.document.search_triples(qualifier_statement, "", "")
        triples_obj, cardinality = self.document.search_triples("", "", qualifier_statement)
        triples_sub = list(triples_sub)
        triples_obj = list(triples_obj)
        return triples_sub, triples_obj
