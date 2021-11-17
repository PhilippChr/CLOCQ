import re


class EvaluationResult:
    def __init__(self):
        self.hit = 0
        self.neighbordhood_size_facts = 0
        self.neighbordhood_size_items = 0

    def set_hit(self):
        """Remember answer presence."""
        self.hit = 1


class Evaluation:
    def __init__(self, stringLib):
        self.stringLib = stringLib
        self.PRE_PATTERN = re.compile("^P[0-9]+$")

    def evaluate(self, search_space, gold_answers, labels_included=True):
        """Evaluate the given search space."""
        result = EvaluationResult()
        gold_answers = [
            self.stringLib.convert_date_to_timestamp(answer) if self.stringLib.is_date(answer) else answer
            for answer in gold_answers
        ]
        gold_answers = set(gold_answers)
        neighbordhood_items = set()
        answer_connecting_facts = list()

        for fact in search_space:
            for ngb in fact:
                if labels_included:
                    ngb = ngb["id"]
                if not ngb or len(ngb) < 2:
                    continue
                if re.match(self.PRE_PATTERN, ngb):
                    continue
                neighbordhood_items.add(ngb)
                ngb = ngb.replace('"', "").replace("+", "")
                if self.stringLib.is_timestamp(ngb):
                    year = self.stringLib.get_year(ngb)
                    # self.print_results("Year: " + str(year))
                    if year in gold_answers:
                        answer_connecting_facts.append(fact)
                        result.set_hit()
                if ngb in gold_answers:
                    answer_connecting_facts.append(fact)
                    result.set_hit()
        result.neighbordhood_size_items = len(neighbordhood_items)
        result.neighbordhood_size_facts = len(search_space)
        return result, answer_connecting_facts
