import json
import time

import requests


class WikidataSearch:
    def __init__(self, results_per_search=20, cache=None):
        self.URL = "https://www.wikidata.org/w/api.php"
        self.SESSION = requests.Session()
        self.params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srlimit": results_per_search,
            "srnamespace": "0|120",
            "srprop": "titlesnippet|snippet"
            # "srnamespace": "120" => search only in predicates
            # "srnamespace": "0" => search only in entities
        }
        self.cache = cache

    def search_term(self, term, offset=None, recursion_depth=0):
        """ Search for the given term. """
        if recursion_depth == 5:
            WikidataSearch._search_exception(term)
            return []
        # try with cache
        if self.cache and not (self.cache.get(term) is None):
            result = self.cache.get(term)
            return result
        # retrieve new
        try:
            self.params["srnamespace"] = "0|120"
            self.params["srsearch"] = term
            if offset:
                self.params["sroffset"] = offset
            res = self.SESSION.get(url=self.URL, params=self.params)
            data = res.json()
            result = [result["title"].replace("Property:", "") for result in data["query"]["search"]]
            self.cache.store(term, result)
            return result
        except:
            time.sleep(0.5)
            recursion_depth += 1
            return self.search_term(term, offset=offset, recursion_depth=recursion_depth)

    def _search_entities(self, term, num_results):
        """NOT IN USE. Searches for num_results entities."""
        try:
            self.params["srnamespace"] = "0"
            self.params["srsearch"] = term
            self.params["srlimit"] = num_results
            res = self.SESSION.get(url=self.URL, params=self.params)
            data = res.json()
            result = [result["title"].replace("Property:", "") for result in data["query"]["search"]]
            return result
        except:
            print("Search exception for", term)
            return []

    def _search_predicates(self, term, num_results):
        """NOT IN USE. Searches for num_results predicates."""
        try:
            self.params["srnamespace"] = "120"
            self.params["srsearch"] = term
            self.params["srlimit"] = num_results
            res = self.SESSION.get(url=self.URL, params=self.params)
            data = res.json()
            result = [result["title"].replace("Property:", "") for result in data["query"]["search"]]
            return result
        except:
            print("Search exception for ", term)
            return []

    @staticmethod
    def _search_exception(term):
        with open("search_exceptions.out", "a") as fp:
            fp.write("Search exception for: " + term + "\n")


class CandidateList:
    """Holds candidata KB items for the question term given, as given by the search engine."""

    def __init__(self, question_term, kb, list_depth, wikidata_search_cache=None):
        self.question_term = question_term
        self.search_engine = WikidataSearch(results_per_search=2 * list_depth, cache=wikidata_search_cache)
        self.kb = kb
        self.list_depth = list_depth
        # current positon of pointer: e.g. 10 after scanning 10 elements
        self.offset = 0
        # initialize list for candidates
        self.item_list = list()

    def initialize(self):
        """Initialize the list with candidate KB items as given by the search engine."""
        # retrieve 2xd results
        item_list = self.search_engine.search_term(self.question_term)
        # prune items that are not in the KB (e.g. pruned, or not present in a different version)
        item_list = [item for item in item_list if self.kb.is_known(item)]
        item_list = item_list[: self.list_depth]
        self.item_list = item_list

    def scan(self):
        """Return next candidate KB item with score. Removes it from the list."""
        if not len(self.item_list):
            return None
        item = self.item_list.pop(0)
        self.offset += 1
        score = 1 / (self.offset + 1)
        return item, score

    def get_items(self):
        """Return full list of candidate KB items."""
        return self.item_list

    def get_max_value(self):
        """Get maximum matching score in the remaining list."""
        return 1 / (self.offset + 1)
