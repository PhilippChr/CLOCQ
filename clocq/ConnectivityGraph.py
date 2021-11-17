import random
import threading
import time

import networkx as nx


class ConnectivityGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.lock = threading.Lock()

    def add_node(self, node, question_word_index):
        """Add the given node to the graph."""
        self.lock.acquire()
        if node in self.graph and not question_word_index in self.graph.nodes(data=True)[node]["question_word_index"]:
            self.graph.nodes(data=True)[node]["question_word_index"].append(question_word_index)
        else:
            self.graph.add_node(node, question_word_index=[question_word_index])
        self.lock.release()

    def add_edge(self, node1, node2, connectivity_score):
        """Add edge between the nodes with their connectivity score as weight."""
        self.lock.acquire()
        if connectivity_score == 0:
            self.lock.release()
            return
        else:
            self.graph.add_edge(node1, node2, weight=connectivity_score)
            self.lock.release()

    def get_single_connectivity_score(self, node, number_of_question_words, question_word_index):
        """
        Compute the maximum score the item can get in any context
        tuple (exactly one connection per question word).
        """
        # get (weight, question-word-index) pairs from the edges and sort them in descending order of the coherence score
        edge_weights = (
            (edge[2]["weight"], self.question_word_indexes(edge[0]), self.question_word_indexes(edge[1]))
            for edge in self.graph.edges([node], data=True)
        )
        sorted_weights = sorted(edge_weights, key=lambda j: j[0], reverse=True)
        # initialize array to store the maximum weight per question word index
        max_weights = [0] * number_of_question_words
        for counter, (weight, indexes1, indexes2) in enumerate(sorted_weights):
            # find other question word indexes for edges
            # this helps e.g. if there is the same word occurring two times, with the same candidate items
            indexes = set(indexes1 + indexes2)
            indexes.remove(question_word_index)
            # iterate through these other word indexes
            for index in indexes:
                # remember the maximum weight for the question word
                if not max_weights[index]:
                    max_weights[index] = weight
        maximum_weight = sum(max_weights)
        if number_of_question_words == 1:
            return maximum_weight, max_weights
        return maximum_weight / (number_of_question_words - 1), max_weights

    def question_word_indexes(self, kb_item):
        """ Returns the question word index for the item. """
        return self.graph.nodes[kb_item]["question_word_index"]

    def compute_item_tuple_score(self, kb_item_tuple):
        """
        NOT IN USE. Compute the connectivity score of a complete KB item
        tuple (one disambiguation per question term.
        """
        count = 0
        sum_connectivity_score = 0
        for i, item1 in enumerate(kb_item_tuple):
            for j, item2 in enumerate(kb_item_tuple):
                if j <= i:
                    continue
                count += 1
                sum_connectivity_score += self.connectivity_check(item1, item2)
        return sum_connectivity_score / count

    def get_connected_components(self):
        """NOT IN USE. Get connected components in the graph."""
        return nx.connected_component_subgraphs(self.graph)

    def nodes(self):
        """NOT IN USE. Returns all graph nodes (= candidate KB items)."""
        return self.graph.nodes

    def connectivity_check(self, item1, item2):
        """NOT IN USE. Performs a connectivity check, based on the populated graph data."""
        data = self.graph.get_edge_data(item1, item2)
        if data:
            return data["weight"]
        else:
            return 0


class ConnectivityScoreProcessor:
    def __init__(self, kb, connectivity_graph):
        self.kb = kb
        self.kb_loaded = True  # can be set to False for testing purposes
        self.connectivity_graph = connectivity_graph

    def process(self, candidates1, candidates2):
        """
        Populate connectivity graph with connectivity of two
        KB item candidate lists.
        """
        for item1 in candidates1:
            for item2 in candidates2:
                connectivity_score = self.kb.connectivity_check(item1, item2)
                if connectivity_score > 0:
                    self.connectivity_graph.add_edge(item1, item2, connectivity_score)

    def process_pairs(self, pairs):
        """
        NOT IN USE. Given a list of question-word pairs, populate the connectivity
        graph with the connectivity among candidate KB item pairs.
        """
        start = time.time()
        max_time_consumed = 0
        max_pair = None
        for pair in pairs:
            candidates1, candidates2 = pair
            counter = 0
            for item1 in candidates1:
                for item2 in candidates2:
                    counter += 1
                    if self.kb_loaded:
                        start_conn_check = time.time()
                        connectivity_score = self.kb.connectivity_check(item1, item2)
                        time_consumed = time.time() - start_conn_check
                        if time_consumed > max_time_consumed:
                            max_time_consumed = time_consumed
                            max_pair = (item1, item2)
                    else:
                        connectivity_score = self._static_connectivity_check(item1, item2)
                    if connectivity_score > 0:
                        self.connectivity_graph.add_edge(item1, item2, connectivity_score)
        if time.time() - start > 0.5:
            print("High cost for pair: ", max_pair, "max_time_consumed: ", max_time_consumed)

    def _static_connectivity_check(self, item1, item2):
        """
        NOT IN USE. This method is only for testing purposes.
        Can be used when the KB is not loaded.
        """
        return 0.5

    def get_graph(self):
        """Returns the connectivity graph."""
        return self.connectivity_graph


if __name__ == "__main__":
    graph = ConnectivityGraph()

    graph.add_node("Croatia football")
    graph.add_node("France football")

    graph.add_edge("Croatia football", "France football", 0.5)
