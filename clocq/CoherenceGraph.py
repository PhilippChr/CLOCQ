import random
import threading
import time

import networkx as nx
import numpy as np


class CoherenceGraph:
    def __init__(self, wiki2vec):
        self.graph = nx.Graph()
        self.wiki2vec = wiki2vec
        self.lock = threading.Lock()

    def add_node(self, node, question_word_index):
        """Add the given node to the graph."""
        self.lock.acquire()
        if node in self.graph and not question_word_index in self.graph.nodes(data=True)[node]["question_word_index"]:
            self.graph.nodes(data=True)[node]["question_word_index"].append(question_word_index)
        else:
            self.graph.add_node(node, question_word_index=[question_word_index])
        self.lock.release()

    def add_edge(self, node1, node2, coherence_score):
        """Add edge between the nodes with their coherence score as weight."""
        self.lock.acquire()
        if coherence_score == 0:
            self.lock.release()
            return
        else:
            self.graph.add_edge(node1, node2, weight=coherence_score)
            self.lock.release()

    def get_single_coherence_score(self, node, number_of_question_words, question_word_index):
        """Compute the maximum score the item can get in any context tuple (exactly one connection per question word)."""
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
        NOT IN USE. Compute the coherence score of a complete KB item
        tuple (one disambiguation per question term.
        """
        count = 0
        sum_coherence_score = 0
        for i, item1 in enumerate(kb_item_tuple):
            for j, item2 in enumerate(kb_item_tuple):
                if j <= i:
                    continue
                count += 1
                sum_coherence_score += self.coherence(item1, item2)
        return sum_coherence_score / count

    def get_connected_components(self):
        """NOT IN USE. Get connected components in the graph."""
        return nx.connected_component_subgraphs(self.graph)

    def nodes(self):
        """NOT IN USE. Returns all graph nodes (= candidate KB items)."""
        return self.graph.nodes

    def coherence(self, item1, item2):
        """NOT IN USE. Performs a coherence check, based on the populated graph data."""
        data = self.graph.get_edge_data(item1, item2)
        if data:
            return data["weight"]
        else:
            return 0


class CoherenceScoreProcessor:
    def __init__(self, wiki2vec, coherence_graph):
        self.wiki2vec = wiki2vec
        self.coherence_graph = coherence_graph

    def process(self, candidates1, candidates2):
        """
        Populate coherence graph with connectivity of two
        KB item candidate lists.
        """
        counter = 0
        candidates1_vectors = list()
        for item1 in candidates1:

            vector = self.wiki2vec.embed_kb_item(item1)
            vector_norm = self.wiki2vec.norm(item1, vector)
            candidates1_vectors.append((vector, vector_norm, item1))

        candidates2_vectors = list()
        for item2 in candidates2:
            vector = self.wiki2vec.embed_kb_item(item2)
            vector_norm = self.wiki2vec.norm(item2, vector)
            candidates2_vectors.append((vector, vector_norm, item2))

        for i, (vector1, vector1_norm, item1) in enumerate(candidates1_vectors):
            for j, (vector2, vector2_norm, item2) in enumerate(candidates2_vectors):
                counter += 1
                if vector1 is None or vector2 is None:
                    continue
                coherence_score = self.wiki2vec.cosine_similarity(
                    vector1, vector2, item1, item2, norm1=vector1_norm, norm2=vector2_norm
                )
                self.coherence_graph.add_edge(item1, item2, coherence_score)

    def get_graph(self):
        """Returns the coherence graph."""
        return self.coherence_graph


if __name__ == "__main__":
    graph = ConnectivityGraph()

    graph.add_node("Croatia football")
    graph.add_node("France football")

    graph.add_edge("Croatia football", "France football", 0.5)
