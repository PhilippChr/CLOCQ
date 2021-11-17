class FaginsAlgorithm:
    """Fagin's Algorithm (FA)."""

    def __init__(self):
        pass

    def apply(self, queue1, queue2, queue3, queue4, hyperparameters, k):
        """
        Return the top-k items in the queues, using the hyperparameters
        in the aggregation function.

        Inputs:
                - queue1, queue2, queue3, queue4 of form: list of tuples: (id, score in queue).
                - hyperparameters: list of float-numbers (4 hyperparameters)
                - k: int
        """
        h1, h2, h3, h4 = hyperparameters
        queues = [queue1, queue2, queue3, queue4]
        length = len(queue1)
        seen_ids = dict()

        for i in range(length):
            for j, queue in enumerate(queues):
                item = queue[i][0]
                score = queue[i][1]
                self._add_item_to_seen(item, score, seen_ids, j)
            if self._k_items_shared(seen_ids, len(queues), k):
                break
        candidates = []
        seen_items = [item for item in seen_ids]

        for item in seen_items:
            scores = [None] * len(queues)
            for queue_index, score in seen_ids[item]:
                scores[queue_index] = score
            for index in [i for i, score in enumerate(scores) if score == None]:
                queue = queues[index]
                scores[index] = self._random_access(queue, item)[1]
            score = h1 * scores[0] + h2 * scores[1] + h3 * scores[2] + h4 * scores[3]
            candidates.append(
                {"id": item, "score": score, "match": scores[0], "rel": scores[1], "conn": scores[2], "coh": scores[3]}
            )

        top_candidates = sorted(candidates, key=lambda j: j["score"], reverse=True)
        top_candidates = top_candidates[:k]
        return top_candidates

    def _add_item_to_seen(self, item, score, seen_ids, queue_index):
        """Remember the item as seen."""
        if seen_ids.get(item) is None:
            seen_ids[item] = [(queue_index, score)]
        else:
            seen_ids[item].append((queue_index, score))

    def _random_access(self, queue, item_id):
        """Random access of an id in a queue."""
        return next((x for x in queue if x[0] == item_id), None)

    def _k_items_shared(self, seen_ids, queues_count, k):
        """Returns true if k items are shared among all queues."""
        count = 0
        for item in seen_ids:
            if len(seen_ids[item]) == queues_count:
                count += 1
                if count == k:
                    return True
        return False


class FaginsThresholdAlgorithm:
    """Fagin's Threshold Algorithm (TA). Slightly more efficient than FA."""

    def __init__(self):
        pass

    def apply(self, queue1, queue2, queue3, queue4, hyperparameters, k):
        """
        Return the top-k items in the queues, using the hyperparameters
        in the aggregation function.

        Inputs:
                - queue1, queue2, queue3, queue4 of form: list of tuples: (id, score in queue).
                - hyperparameters: list of float-numbers (4 hyperparameters)
                - k: int
        """
        queues = [queue1, queue2, queue3, queue4]
        length = len(queue1)
        seen_ids = set()
        # initialize list maintaining top items
        top_k_items = [{"id": None, "score": 0}] * k
        k_th_score = 0

        threshold_scores = [1] * len(queues)
        for i in range(length):
            for j, queue in enumerate(queues):
                item_id = queue[i][0]
                single_score = queue[i][1]
                # update highest possible score in queue
                threshold_scores[j] = single_score
                # check whether item already fully scored
                if item_id in seen_ids:
                    continue
                # fully score item
                scored_item = self.compute_aggregated_score(item_id, queues, hyperparameters, single_score, j)
                aggregated_score = scored_item["score"]
                seen_ids.add(item_id)
                # update top-k items
                if aggregated_score > k_th_score:
                    top_k_items = top_k_items[:k]
                    top_k_items.append(scored_item)
                    top_k_items = sorted(top_k_items, key=lambda j: j["score"], reverse=True)
            # update threshold
            threshold = 0
            for l in range(len(hyperparameters)):
                threshold += threshold_scores[l] * hyperparameters[l]
            # check termination criteria
            k_th_score = top_k_items[k - 1]["score"]
            if threshold <= k_th_score:
                break
        top_k_items = top_k_items[:k]
        return top_k_items

    def compute_aggregated_score(self, item_id, queues, hyperparameters, single_score, single_score_index):
        """Score the given item wrt. all scores in the different queues.
        -> Use random accesses in these lists."""
        aggregated_score = 0
        scores = list()
        for i, queue in enumerate(queues):
            if not i == single_score_index:
                new_score = self.random_access(queue, item_id)[1]
                aggregated_score += new_score * hyperparameters[i]
                scores.append(new_score)
            else:
                aggregated_score += single_score * hyperparameters[i]
                scores.append(single_score)
        return {
            "id": item_id,
            "score": aggregated_score,
            "match": scores[0],
            "rel": scores[1],
            "conn": scores[2],
            "coh": scores[3],
        }

    def random_access(self, queue, item_id):
        """Random access of an item in a specific queue."""
        return next((x for x in queue if x[0] == item_id), None)
