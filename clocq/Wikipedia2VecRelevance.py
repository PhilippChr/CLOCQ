import json
import re
import time

import numpy as np
from wikipedia2vec import Wikipedia2Vec


class Wikipedia2VecRelevance:
    def __init__(
        self, kb, path_to_stopwords, path_to_wiki2vec_model, path_to_wikipedia_mappings, path_to_norm_cache=None
    ):
        self.kb = kb
        self.wiki2vec = Wikipedia2Vec.load(path_to_wiki2vec_model)
        # define regular expressions
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        # load stopwords
        with open(path_to_stopwords, "r") as file:
            self.stopwords = file.read().split("\n")
        # load mappings (wikidata->wikipedia)
        with open(path_to_wikipedia_mappings, "r") as file:
            self.wikipedia_mappings = json.load(file)
        # initialize cache for vector norms
        self.path_to_norm_cache = path_to_norm_cache
        self._initialize_norm_cache()
        self.cache_changed = False

    def _initialize_norm_cache(self):
        """Initialize the vector norm cache."""
        if self.path_to_norm_cache:
            with open(self.path_to_norm_cache, "r") as fp:
                self.norm_cache = json.load(fp)
        else:
            self.norm_cache = dict()

    def store_norm_cache(self):
        """Store the cache for vector norms on disk."""
        if self.path_to_norm_cache and self.cache_changed:
            with open(self.path_to_norm_cache, "w") as fp:
                fp.write(json.dumps(self.norm_cache))

    def cosine_similarity(self, vector1, vector2, string1, string2, norm1=False, norm2=False):
        """Compute the cosine similarity between the two vectors."""
        if norm1 and norm2:
            sim = np.dot(vector1, vector2) / (norm1 * norm2)
        else:
            sim = np.dot(vector1, vector2) / (self.norm(string1, vector1) * self.norm(string2, vector2))
        return sim

    def norm(self, string, vector):
        """Compute (or retrieve from cache) the vector norm."""
        if vector is None:
            return None
        # retrieve vector norm from cache
        cached = self.norm_cache.get(string)
        if cached is None:
            vector_norm = np.linalg.norm(vector)
            # store norm in cache
            self.norm_cache[string] = str(vector_norm)
            self.cache_changed = True
            return vector_norm
        else:
            return float(cached)

    def embed_kb_item(self, kb_item):
        """Retrieve embedding for Wikidata ID."""
        if self._is_entity(kb_item):
            wikipedia_name = self.entity_to_wikipedia_name(kb_item)
            if wikipedia_name:
                try:
                    vector = self.wiki2vec.get_entity_vector(wikipedia_name)
                    return vector
                except:
                    pass
            label = self.kb.item_to_single_label(kb_item)
            if label is None:
                return None
            label = label.lower()
        # string is predicate id
        elif self._is_predicate(kb_item):
            label = self.kb.item_to_single_label(kb_item)
            if label is None:
                return None
            label = label.lower()
        # string is not a kb item
        else:
            string = kb_item
            label = string.lower()
        # lookup averaged vector for predicate label or question word
        vector = self.embed_phrase(label)
        return vector

    def embed_phrase(self, phrase):
        """Embed the given phrase into latent space."""
        phrase = phrase.lower()
        words = phrase.split()
        # remove stopwords
        words = [word for word in words if not word in self.stopwords]
        vectors = list()
        for word in words:
            try:
                vector = self.wiki2vec.get_word_vector(word)
                vectors.append(vector)
            except:
                continue
        if len(vectors) == 0:
            return None
        return np.mean(vectors, axis=0)

    def matching(self, kb_item, question_term):
        """Compute the matching score between the kb_item and the question term."""
        return self.relevance_score(kb_item, question_term)

    def relevance_score(self, string1, string2):
        """Embed both strings and return cosine similarity."""
        vector1 = self.embed_kb_item(string1)
        vector2 = self.embed_kb_item(string2)
        if vector1 is None or vector2 is None:
            return 0
        res = self.cosine_similarity(vector1, vector2, string1, string2)
        return res

    def _is_entity(self, string):
        """Check if string follows entity pattern."""
        return re.match(self.ENT_PATTERN, string)

    def _is_predicate(self, string):
        """Check if string follows predicate pattern."""
        return re.match(self.PRE_PATTERN, string)

    def entity_to_wikipedia_name(self, entity):
        """Retrieve Wikipedia name of entity for loading into wikipedia2vec."""
        if self.wikipedia_mappings.get(entity) is None:
            return None
        else:
            wikipedia_name = self.wikipedia_mappings[entity]
            wikipedia_name = wikipedia_name.replace("%27", "'")
            wikipedia_name = wikipedia_name.replace("_", " ")
            return wikipedia_name

    def get_question_relevance_score(self, kb_item, other_question_words_vectors):
        """
        Compute the relevance score for the given KB item, using the word vectors
        of the words the KB item was not retrieved for. E.g. for the question
        'who is the coach of the France national football team?', candidate disambiguations
        for 'France national football team' are only scored upon their relevance to 'coach'.
        """
        item_vector = self.embed_kb_item(kb_item)
        if item_vector is None or not len(other_question_words_vectors):
            return 0
        score = 0
        for word, word_vector in other_question_words_vectors:
            score += self.cosine_similarity(item_vector, word_vector, kb_item, word)
        question_relevance = score / len(other_question_words_vectors)
        return question_relevance

    def get_word_vectors(self, other_question_words):
        """
        Get word vectors of all question words given.
        Used for initializing 'other_question_words_vectors'
        for the method 'get_question_relevance_score'.
        """
        vectors = list()
        for word in other_question_words:
            word_vector = self.embed_phrase(word)
            if word_vector is None:
                continue
            else:
                vectors.append((word, word_vector))
        return vectors


if __name__ == "__main__":
    wiki2vec = Wikipedia2Vec.load("data/enwiki_20180420_300d.pkl")

    res = wiki2vec.get_word_vector("19")
    print(res)

    question_words = ["2018", "final", "Croatia", "played"]
    question_word_vectors = wiki2vec.get_word_vectors(question_words)
    score = wiki2vec.get_question_relevance_score("Q170645", question_word_vectors)
    print("score (Q170645)", score)
    score = wiki2vec.get_question_relevance_score("Q47774", question_word_vectors)
    print("score (Q47774)", score)
