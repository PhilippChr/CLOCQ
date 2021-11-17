import sys

from clocq.CLOCQ import CLOCQ
from clocq.interface.CLOCQInterfaceClient import CLOCQInterfaceClient
from clocq.interface.CLOCQTaskHandler import CLOCQTaskHandler

def test(clocq):
    kb_item = "Q5"

    res = clocq.get_label(kb_item)
    print(res)

    res = clocq.get_labels(kb_item)
    print(res)

    res = clocq.get_aliases(kb_item)
    print(res)

    res = clocq.get_description(kb_item)
    print(res)

    res = clocq.get_types(kb_item)
    print(res)

    res = clocq.get_frequency(kb_item)
    print(res)

    res = clocq.get_neighborhood(kb_item)
    print(res)

    res = clocq.get_neighborhood_two_hop(kb_item)
    print(res)

    kb_item1 = kb_item
    kb_item2 = "Q215627"
    res = clocq.connect(kb_item1, kb_item2)
    print(res)

    res = clocq.connectivity_check(kb_item1, kb_item2)
    print(res)

    ques = "who scored a goal in 2018 final between France and Croatia?"
    res = clocq.get_search_space(ques)
    print(res.keys())

    res = clocq.is_wikidata_entity(kb_item)
    print(res)

    res = clocq.is_wikidata_predicate(kb_item)
    print(res)


if __name__ == "__main__":
    # clocq = CLOCQ(dev=True)
    # test(clocq)

    # clocq = CLOCQInterfaceClient(port="7778")
    # test(clocq)

    task_handler = CLOCQTaskHandler(dev=True)
    input_path = "clocq/interface/tasks_example.json"
    output_path = "clocq/interface/tasks_example.jsonl"
    task_handler.process_tasks(input_path, output_path)
