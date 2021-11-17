import json
import pickle
import random
import re
import time

from hdt import HDTDocument


class KnowledgeBaseHDT:
    def __init__(self, path_to_hdt, path_to_kb_dicts, string_lib):
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        self.document = HDTDocument(path_to_hdt)
        self.string_lib = string_lib
        # load dictionaries: integer -> Wikidata ID/literal
        # the name of the dictionaries is fix
        try:
            with open(path_to_kb_dicts + "/labels.json", "r") as infile:
                self.labels_dict = json.load(infile)
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

    def connectivity_check(self, item1, item2):
        ngb_facts_1 = self._query_hdt_library_with_qualifiers(item1)
        ngb_facts_2 = self._query_hdt_library_with_qualifiers(item2)
        ngb_items_1 = self._facts_to_item_set(ngb_facts_1)
        ngb_items_2 = self._facts_to_item_set(ngb_facts_2)
        if item1 in ngb_items_2:
            return 1.0
        intersection = ngb_items_1 & ngb_items_2
        res = [i for i in list(intersection) if i and i[0] != "P"]
        if res:
            return 0.5
        return 0

    def get_neighborhood(self, item, p=1000, include_labels=False):
        ngb_facts = list()
        if not item:
            return ngb_facts
        ngb_facts = self._query_hdt_library_with_qualifiers(item)
        for fact in ngb_facts:
        	cleaned_fact = [self.string_lib.wikidata_url_to_wikidata_id(item) for item in fact]
        	cleaned_ngb_facts.append(cleaned_fact)
        return ngb_facts

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

    def _query_hdt_library_with_qualifiers(self, entity_id):
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
        if cardinality2 < 100000:
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
            if len(facts_obj) < 10000:
                facts += facts_obj
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
