import datetime
import json
import os
import sys
import time

from flask import Flask, jsonify, render_template, request, session

from clocq import config

from clocq.CLOCQAlgorithm import CLOCQAlgorithm
from clocq.knowledge_base.KnowledgeBase import KnowledgeBase
from clocq.StringLibrary import StringLibrary
from clocq.WikidataSearchCache import WikidataSearchCache

"""Flask config"""
app = Flask(__name__, static_folder="templates/static")
# Set the secret key to some random bytes.
app.secret_key = os.urandom(32)
app.permanent_session_lifetime = datetime.timedelta(days=365)

"""Load modules"""
string_lib = StringLibrary(config.PATH_TO_STOPWORDS, config.TAGME_TOKEN, config.PATH_TO_TAGME_NER_CACHE)
wikidata_search_cache = WikidataSearchCache(config.PATH_TO_WIKI_SEARCH_CACHE)
kb = KnowledgeBase(config.PATH_TO_KB_LIST, config.PATH_TO_KB_DICTS, max_items=10)

"""Initialize CLOCQ"""
method_name = "clocq_server"
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

"""Routes"""
@app.route("/test", methods=["GET"])
def test():
    return "Test successful!"


@app.route("/neighborhood", methods=["POST"])
def neighborhood():
    json_dict = request.json
    item_id = json_dict.get("item")
    if item_id is None:
        return jsonify([])
    include_labels = json_dict.get("include_labels")
    if include_labels is None:
        include_labels = True
    p = json_dict.get("p")
    if p is None:
        p = 1000
    facts = kb.get_neighborhood(item_id, p=p, include_labels=include_labels)
    if not facts:
        facts = []
    return jsonify(facts)


@app.route("/two_hop_neighborhood", methods=["POST"])
def two_hop_neighborhood():
    json_dict = request.json
    item_id = json_dict.get("item")
    if item_id is None:
        return jsonify([])
    include_labels = json_dict.get("include_labels")
    if include_labels is None:
        include_labels = True
    p = json_dict.get("p")
    if p is None:
        p = 1000
    facts = kb.get_neighborhood_two_hop(item_id, p=p, include_labels=include_labels)
    if not facts:
        facts = []
    return jsonify(facts)


@app.route("/connect", methods=["POST"])
def find_all_connections():
    json_dict = request.json
    item1 = json_dict.get("item1")
    if item1 is None:
        return jsonify(None)
    item2 = json_dict.get("item2")
    if item2 is None:
        return jsonify(None)
    hop = json_dict.get("hop")
    return jsonify(kb.find_all_connections(item1, item2, hop=hop))


@app.route("/connectivity_check", methods=["POST"])
def connectivity_check():
    json_dict = request.json
    item1 = json_dict.get("item1")
    if item1 is None:
        return jsonify(None)
    item2 = json_dict.get("item2")
    if item2 is None:
        return jsonify(None)
    return str(kb.connectivity_check(item1, item2))


@app.route("/item_to_types", methods=["POST"])
def item_to_types():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return jsonify(None)
    return jsonify(kb.item_to_types(item))


@app.route("/item_to_label", methods=["POST"])
def item_to_label():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return None
    return jsonify(kb.item_to_single_label(item))


@app.route("/item_to_labels", methods=["POST"])
def item_to_labels():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return None
    return jsonify(kb.item_to_labels(item))


@app.route("/item_to_aliases", methods=["POST"])
def item_to_aliases():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return None
    return jsonify(kb.item_to_aliases(item))


@app.route("/item_to_description", methods=["POST"])
def item_to_description():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return None
    return jsonify(kb.item_to_description(item))


@app.route("/frequency", methods=["POST"])
def frequency():
    json_dict = request.json
    item = json_dict.get("item")
    if item is None:
        return None
    return jsonify(kb.frequency(item))


@app.route("/search_space", methods=["POST"])
def search_space():
    json_dict = request.json
    # load question
    question = json_dict.get("question")
    if question is None:
        return None
    # load parameters
    parameters = json_dict.get("parameters")
    if parameters is None:
        parameters = config.DEF_PARAMS
    else:
        new_parameters = config.DEF_PARAMS
        for key in parameters:
            new_parameters = parameters[key]
        parameters = new_parameters
    # include labels of search space?
    include_labels = json_dict.get("include_labels")
    if include_labels is None:
        include_labels = True
    # compute result (search space and disambiguation results)
    result = clocq.get_seach_space(question, parameters=parameters, include_labels=include_labels)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, threaded=True)
