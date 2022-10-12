import math
import time

from scipy.stats import entropy

from clocq.FaginsAlgorithm import FaginsThresholdAlgorithm
from clocq.WikidataSearch import CandidateList, WikidataSearch


class TopkProcessor:
    """
    Operator that computes the top-k KB items for
    one specific question word. There is one such operator
    for each question word, i.e. m parallel operators.
    """

    def __init__(
        self,
        kb,
        wiki2vec,
        connectivity_graph,
        coherence_graph,
        question_word_index,
        question_words,
        h_match=0.4,
        h_rel=0.3,
        h_conn=0.2,
        h_coh=0.1,
        d=20,
        k="AUTO",
        wikidata_search_cache=None,
        verbose=False,
    ):
        self.kb = kb
        self.verbose = verbose
        # initialize question words
        self.question_word_index = question_word_index
        self.question_words = question_words
        self.question_word = question_words[question_word_index]
        self.number_of_question_words = len(question_words)
        # initialize required structures
        self.connectivity_graph = connectivity_graph
        self.coherence_graph = coherence_graph
        self.wiki2vec = wiki2vec
        # used for computing k (if applicable)
        self._initialize_item_retrieval(d, wikidata_search_cache)
        # hyperparameters
        self.h_match = h_match
        self.h_rel = h_rel
        self.h_conn = h_conn
        self.h_coh = h_coh
        # other parameters
        self.d = d
        self.k = k
        # internal variable
        self.top_k = (
            None  # top-k list as returned by FaginsAlgorithm.apply() method, structure: [score, id, score[1-4]]
        )
        # initialize candidate list
        self.candidate_list = CandidateList(
            self.question_word, kb, list_depth=d, wikidata_search_cache=wikidata_search_cache
        )
        # priority queues for individual scores
        self.queue_matching_score = list()
        self.queue_connectivity_score = list()
        self.queue_relevance_score = list()
        self.queue_coherence_score = list()
        # set k automatically for question word
        if k == "AUTO":
            self.k = self._set_k()
        else:
            self.k = int(k)

    def _initialize_item_retrieval(self, depth, wikidata_search_cache):
        """
        Initialize a Wikidata search. The search can be initialized
        with existing search results for (better) reproducibility of results.
        """
        if wikidata_search_cache:
            self.search = WikidataSearch(depth, wikidata_search_cache)
        else:
            self.search = WikidataSearch(depth)

    def add_candidates_to_graph(self):
        """Add candidate KB items to graphs (connectivity and coherence)."""
        # check if candidates already initialized (in k=AUTO setting)
        if not self.candidate_list.get_items():
            self.candidate_list.initialize()
        # add items to graphs
        for node in self.candidate_list.get_items():
            self.connectivity_graph.add_node(node, self.question_word_index)
            self.coherence_graph.add_node(node, self.question_word_index)

    def get_candidates(self):
        """Return all candidate KB items (left) in the list."""
        return self.candidate_list.get_items()

    def _set_k(self):
        """
        Determine the k parameter for the given question word.
        The current implementation is based on the ambiguity of the word,
        which relates to the uncertainty of the disambiguation.
        This uncertainty is computed by the entropy of the frequency
        distribution of candidate KB items in the KB.
        """
        self.candidate_list.initialize()
        search_result = self.candidate_list.get_items()
        frequencies = list()
        # determine frequencies
        for item in search_result:
            freqs = self.kb.get_frequency(item)
            freq = sum(freqs)
            frequencies.append(freq)
        sum_frequency = sum(frequencies)
        if sum_frequency == 0:
            k = 0
            return k
        # transform to probabilities
        probabilities = [float(freq) / float(sum_frequency) for freq in frequencies]
        ent = entropy(probabilities, base=2)
        # compute k
        k = math.floor(ent) + 1
        return k

    def initialize_scores(self):
        """
        Creates a list for each score, in which KB items are
        sorted in score-descending order.
        """
        start = time.time()
        other_question_words = [
            word for i, word in enumerate(self.question_words) if not i == self.question_word_index
        ]
        other_question_words_vectors = self.wiki2vec.get_word_vectors(other_question_words)
        for i in range(self.d):
            item = self.candidate_list.scan()
            if item is None:
                break
            item, score = item
            # matching
            matching_score = score
            # matching_score = self.wiki2vec.matching(item, self.question_word) # alternative to 1/rank
            matching_score = round(matching_score, 4)
            self.queue_matching_score.append((item, matching_score))
            # relevance
            relevance_score = self.wiki2vec.get_question_relevance_score(item, other_question_words_vectors)
            relevance_score = round(relevance_score, 4)
            self.queue_relevance_score.append((item, relevance_score))
            # connectivity
            connectivity_score, max_weights = self.connectivity_graph.get_single_connectivity_score(
                item, self.number_of_question_words, self.question_word_index
            )
            connectivity_score = round(connectivity_score, 4)
            self.queue_connectivity_score.append((item, connectivity_score))
            # coherence
            coherence_score, max_weights = self.coherence_graph.get_single_coherence_score(
                item, self.number_of_question_words, self.question_word_index
            )
            coherence_score = round(coherence_score, 4)
            self.queue_coherence_score.append((item, coherence_score))
        # sort the individual queues
        self.queue_matching_score = sorted(self.queue_matching_score, key=lambda j: j[1], reverse=True)
        self.queue_relevance_score = sorted(self.queue_relevance_score, key=lambda j: j[1], reverse=True)
        self.queue_connectivity_score = sorted(self.queue_connectivity_score, key=lambda j: j[1], reverse=True)
        self.queue_coherence_score = sorted(self.queue_coherence_score, key=lambda j: j[1], reverse=True)
        self._print_verbose(f"Time (initialize_scores): {time.time() - start}")

    def compute_top_k(self, connectivity_graph, coherence_graph):
        """
        Compute the top-k KB items for the question term, given the
        connectivity graph, coherence graph and initialized matching
        and coherence scores.
        First, the queues are established and sorted in score-descending
        order, then Fagin's Threshold Algorithm (TA) is applied.
        """
        self.connectivity_graph = connectivity_graph
        self.coherence_graph = coherence_graph
        self.initialize_scores()
        start = time.time()
        fagins = FaginsThresholdAlgorithm()
        self.top_k = fagins.apply(
            self.queue_matching_score,
            self.queue_relevance_score,
            self.queue_connectivity_score,
            self.queue_coherence_score,
            (self.h_match, self.h_rel, self.h_conn, self.h_coh),
            k=self.k,
        )
        self._print_verbose(f"Time (FaginsAlgorithm) {time.time() - start}")

    def get_top_k(self):
        """Returns the top-k KB items for the question term."""
        return self.top_k

    def scan(self):
        """Returns the next top-k KB item for the question term."""
        return self.top_k.pop()

    def _print_verbose(self, string):
        """Print only if verbose is set."""
        if self.verbose:
            print(string)
