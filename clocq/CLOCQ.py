import json
import pickle
import random
import re
import time
import requests
import sys

from clocq import config

from clocq.CLOCQAlgorithm import CLOCQAlgorithm
from clocq.knowledge_base.KnowledgeBase import KnowledgeBase
from clocq.StringLibrary import StringLibrary
from clocq.WikidataSearchCache import WikidataSearchCache


class CLOCQ:
    def __init__(self, dev=False):
        # load required modules
        string_lib = StringLibrary(config.PATH_TO_STOPWORDS, config.TAGME_TOKEN, config.PATH_TO_TAGME_NER_CACHE)
        wikidata_search_cache = WikidataSearchCache(config.PATH_TO_WIKI_SEARCH_CACHE)
        if dev:
            self.kb = KnowledgeBase(config.PATH_TO_KB_LIST, config.PATH_TO_KB_DICTS, max_items=10)
        else:
            self.kb = KnowledgeBase(config.PATH_TO_KB_LIST, config.PATH_TO_KB_DICTS)

        # load CLOCQ
        method_name = "clocq"
        self.clocq = CLOCQAlgorithm(
            self.kb,
            string_lib,
            method_name,
            config.NER,
            config.PATH_TO_STOPWORDS,
            config.PATH_TO_WIKI2VEC_MODEL,
            config.PATH_TO_WIKIPEDIA_MAPPINGS,
            config.PATH_TO_NORM_CACHE,
            wikidata_search_cache=wikidata_search_cache,
        )

        # define regex pattern
        self.ENTITY_PATTERN = re.compile("^Q[0-9]+$")
        self.PRED_PATTERN = re.compile("^P[0-9]+$")

    def get_label(self, kb_item):
        """
        Retrieves a single label for the given KB item.
        E.g. "France national association football team" for "Q47774".

        Note: The n-triples Wikidata dump stores multiple labels (not aliases) for the same item.
        Here, we return the first KB label which is not exactly the KB item id (i.e. "Q47774").
        Shown as: "Label".
        """
        return self.kb.item_to_single_label(kb_item)

    def get_labels(self, kb_item):
        """
        Retrieves the list of label for the given KB item.
        E.g. ["France national association football team", "France national team"] for "Q47774".

        Note: The n-triples Wikidata dump stores multiple labels (not aliases) for the same item.
        Here, we return the full list of KB labels stored in the n-triples dump.
        Shown as: "Label".
        """
        return self.kb.item_to_labels(kb_item)

    def get_aliases(self, kb_item):
        """
        Retrieves the aliases for the given KB item.
        E.g. "France" for "Q47774".
        Shown as: "Also known as".
        """
        return self.kb.item_to_aliases(kb_item)

    def get_description(self, kb_item):
        """
        Retrieves the description for the given KB item.
        The descriptions can be seen on top of Wikidata pages.
        E.g. "men's national association football team representing France" for "Q47774".
        Shown as: "Description".
        """
        return self.kb.item_to_description(kb_item)

    def get_types(self, kb_item):
        """
        Retrieves the types for the given KB item.
        Returns list of items with keys: {"id", "label"}.
        E.g. {"id": "Q6979593", "label": "national association football team"} for "Q47774".
        """
        return self.kb.item_to_types(kb_item)

    def get_frequency(self, kb_item):
        """
        A list of two frequency numbers for the given KB item:
        - number of facts with the item occuring as subject
        - number of facts with the item occuring as object/qualifier-object.
        """
        return self.kb.frequency(kb_item)

    def get_neighborhood(self, kb_item, p=1000, include_labels=True):
        """
        Returns a list of facts including the item (the 1-hop neighborhood)
        each fact is a n-tuple, with subject, predicate, object and qualifier information.
        """
        return self.kb.get_neighborhood(kb_item, p=p, include_labels=include_labels)

    def get_neighborhood_two_hop(self, kb_item, p=1000, include_labels=True):
        """
        Returns a list of facts in the 2-hop neighborhood of the item
        each fact is a n-tuple, with subject, predicate, object and qualifier information.
        """
        return self.kb.get_neighborhood_two_hop(kb_item, p=p, include_labels=include_labels)

    def connect(self, kb_item1, kb_item2):
        """
        Returns a list of paths between item1 and item2. Each path is given by either 1 fact
        (1-hop connection) or 2 facts (2-hop connections).
        """
        return self.kb.find_all_connections(kb_item1, kb_item2)

    def connectivity_check(self, kb_item1, kb_item2):
        """
        Returns the distance of the two items in the graph, given a fact-based definition.
        Returns 1 if the items are within 1 hop of each other,
        Returns 0.5 if the items are within 2 hops of each other,
        and returns 0 otherwise.
        """
        return self.kb.connectivity_check(kb_item1, kb_item2)

    def get_search_space(self, question, parameters=dict(), include_labels=True):
        """
        Extract a question-specific context for the given question using the CLOCQ algorithm.
        Returns k (context tuple, context graph)-pairs for the given questions,
        i.e. a mapping of question words to KB items and a question-relevant KG subset.
        In case the dict is empty, the default CLOCQ parameters are used
        """
        if not parameters:
            parameters = config.DEF_PARAMS
        else:
            new_parameters = config.DEF_PARAMS
            for key in parameters:
                new_parameters = parameters[key]
            parameters = new_parameters
        return self.clocq.get_seach_space(question, parameters=parameters, include_labels=include_labels)

    def is_wikidata_entity(self, string):
        """
        Check whether the given string can be a wikidata entity.
        """
        return self.ENTITY_PATTERN.match(string) is not None

    def is_wikidata_predicate(self, string):
        """
        Check whether the given string can be a wikidata predicate.
        """
        return self.PRED_PATTERN.match(string) is not None


"""
MAIN
"""
if __name__ == "__main__":
    clocq = CLOCQ(dev=True)

    kb_item = "Q5"
    res = clocq.get_label(kb_item)
    print(res)
