import json
import os.path
import sys
import time
import traceback

from clocq import config
from clocq.CLOCQAlgorithm import CLOCQAlgorithm
from clocq.Evaluation import Evaluation
from clocq.knowledge_base.KnowledgeBase import KnowledgeBase
from clocq.knowledge_base.KnowledgeBaseHDT import KnowledgeBaseHDT
from clocq.knowledge_base.KnowledgeBaseSPARQL import KnowledgeBaseSPARQL
from clocq.StringLibrary import StringLibrary
from clocq.WikidataSearchCache import WikidataSearchCache


def _run_method(method, method_name, parameter_tuples, data_split, is_clocq=True, store_jsonl=False):
    """Runs the given method on the benchmarks with the specified parameter settings."""
    print("Running: ", method_name, "Testing: ", data_split, "KB: ", kb_name)

    # initialize results
    eval_path = method_name + ".res"
    detailed_eval_path = method_name + ".json"
    if os.path.isfile(detailed_eval_path):
        with open(detailed_eval_path, "r") as fp:
            results = json.load(fp)
    else:
        results = dict()
    # result path for disambiguations and search spaces
    result_path = method_name + ".jsonl"

    # go through parameter settings
    for parameters in parameter_tuples:
        # go through benchmarks
        for (benchmark_file, benchmark_name) in config.BENCHMARKS:
            # load data
            with open(benchmark_file, "r") as fp:
                benchmark = json.load(fp)
            benchmark = benchmark[data_split]

            # initialize scores
            answer_presence = list()
            neighborhood_sizes_facts = list()
            neighborhood_sizes_items = list()
            all_answer_connecting_facts = list()
            kb_item_tuples = list()
            timings = list()

            # iterate through benchmark
            for i, instance in enumerate(benchmark):
                question = instance["question"]
                answers = instance["answers"]

                # retrieve search space
                question_start = time.time()
                result = method.get_seach_space(question, parameters)
                timing = time.time() - question_start
                answer_connecting_facts = list()
                question_context_tuples = list()

                # iterate through contexts and accumulate result
                kb_item_tuple = result["kb_item_tuple"]
                search_space = result["search_space"]
                result, answer_connecting_facts = evaluation.evaluate(search_space, answers)

                # store search space and disambiguations to disk
                if store_jsonl:
                    instance["kb_item_tuple"] = kb_item_tuple
                    instance["search_space"] = search_space
                    with open(result_path, "a") as fp:
                        fp.write(json.dumps(instance))
                        fp.write("\n")

                # remember results
                kb_item_tuples.append(kb_item_tuple)
                answer_presence.append(result.hit)
                neighborhood_sizes_facts.append(result.neighbordhood_size_facts)
                neighborhood_sizes_items.append(result.neighbordhood_size_items)
                all_answer_connecting_facts.append(answer_connecting_facts)
                timings.append(timing)

                # print results
                method.print_results((question, method_name, i + 1, sum(answer_presence) / (i + 1)))

            # create result
            avg_neighborhood_sizes_facts = (
                f"{round(sum(neighborhood_sizes_facts)/len(neighborhood_sizes_facts), -2)/1000}k"
            )
            avg_neighborhood_sizes_items = (
                f"{round(sum(neighborhood_sizes_items)/len(neighborhood_sizes_items), -2)/1000}k"
            )
            avg_answer_presence = round(sum(answer_presence) / len(answer_presence), 3)
            result = {
                "method_name": method_name,
                "NER_method": str(config.NER),
                "parameters": parameters,
                "data_split": data_split,
                "instances": len(benchmark),
                # 'neighborhood_sizes_facts': neighborhood_sizes_facts,
                # 'neighborhood_sizes_items': neighborhood_sizes_items,
                "avg_neighborhood_sizes_facts": avg_neighborhood_sizes_facts,
                "avg_neighborhood_sizes_items": avg_neighborhood_sizes_items,
                # "kb_item_tuples": kb_item_tuples,
                # 'timings': timings,
                "avg_time_consumed": round(sum(timings) / len(timings), 2),
                "answer_presence": answer_presence,
                "avg_answer_presence": avg_answer_presence
                # 'answer_connecting_facts': all_answer_connecting_facts,
            }

            # append results
            if not results.get(benchmark_name):
                results[benchmark_name] = list()
            results[benchmark_name].append(result)

            # store result
            with open(eval_path, "a") as fp:
                fp.write(
                    f"Benchmark: {benchmark_name}, Answer presence: {avg_answer_presence}, Search space size: {avg_neighborhood_sizes_items}, Parameters: {parameters}\n"
                )
            with open(detailed_eval_path, "w") as fp:
                fp.write(json.dumps(results, indent=4))

    # store caches
    if is_clocq:
        method.store_caches()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)
    params = sys.argv[1:]

    # define whether test or dev is run
    if "--test" in params:
        data_split = "test"
    elif "--dev" in params:
        data_split = "dev"
    else:
        data_split = "test"

    # required modules
    string_lib = StringLibrary(config.PATH_TO_STOPWORDS, config.TAGME_TOKEN, config.PATH_TO_TAGME_NER_CACHE)
    evaluation = Evaluation(string_lib)
    wikidata_search_cache = WikidataSearchCache(config.PATH_TO_WIKI_SEARCH_CACHE)

    # load kb (always needed for evaluation)
    if "--hdt" in params:
        kb_name = "hdt"
        kb = KnowledgeBaseHDT(config.PATH_TO_HDT_FILE, config.PATH_TO_KB_DICTS, string_lib)
    elif "--sparql" in params:
        kb_name = "sparql"
        kb = KnowledgeBaseSPARQL(config.PATH_TO_KB_DICTS, string_lib)
    elif "--dummy" in params:
        kb_name = "dummy"
        kb = KnowledgeBase(config.PATH_TO_KB_LIST, config.PATH_TO_KB_DICTS, max_items=10)
    else:
        kb_name = "clocq"
        kb = KnowledgeBase(config.PATH_TO_KB_LIST, config.PATH_TO_KB_DICTS)

    method_name = "results/clocq_" + data_split + "_" + kb_name
    clocq = CLOCQAlgorithm(
        kb,
        string_lib,
        method_name,
        config.NER,
        config.PATH_TO_STOPWORDS,
        config.PATH_TO_WIKI2VEC_MODEL,
        config.PATH_TO_WIKIPEDIA_MAPPINGS,
        config.PATH_TO_NORM_CACHE,
        wikidata_search_cache=wikidata_search_cache,
    )
    _run_method(clocq, method_name, config.CLOCQ_PARAMS, data_split, is_clocq=True)
