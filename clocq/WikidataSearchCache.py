import json
import threading


class WikidataSearchCache:
    def __init__(self, path_to_wiki_search_cache):
        self.lock = threading.Lock()
        self.cache_changed = False
        self.path_to_wiki_search_cache = path_to_wiki_search_cache
        self._initialize_cache()

    def _initialize_cache(self):
        """Initialize cache."""
        if self.path_to_wiki_search_cache:
            with open(self.path_to_wiki_search_cache, "r") as file:
                self.cache = json.load(file)
        else:
            self.cache = dict()

    def store_cache(self):
        """Store the cache to disk."""
        if self.path_to_wiki_search_cache and self.cache_changed:
            with open(self.path_to_wiki_search_cache, "w") as fp:
                json.dump(self.cache, fp)

    def get(self, question_term):
        """Retrieve results for the question_term from the cache."""
        res = self.cache.get(question_term)
        # signal no cache hit
        if not res:
            return None
        # copy object and return
        return res.copy()

    def store(self, question_term, sorted_items):
        """Store the entry in the cache."""
        self.lock.acquire()
        self.cache[question_term] = sorted_items.copy()
        self.cache_changed = True
        self.lock.release()
