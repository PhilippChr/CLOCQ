"""This file defines global variables that are used within
the different modules, like file paths, or specific parameters."""
import os

"""
ADJUST IF NEEDED
"""
NER = "tagme"
TAGME_TOKEN = "<INSERT_YOUR_TOKEN_HERE>" # TagME token: REQUIRED

# standard parameters for reproducing paper results
CLOCQ_PARAMS = [
    {
        # default
        "h_match": 0.4,
        "h_rel": 0.2,
        "h_conn": 0.3,
        "h_coh": 0.1,
        "d": 20,
        "k": "AUTO",
        "p_setting": 1000,
        "bm25_limit": False,
    },
    {
        # k=1, p=10,000
        "h_match": 0.4,
        "h_rel": 0.2,
        "h_conn": 0.3,
        "h_coh": 0.1,
        "d": 20,
        "k": 1,
        "p_setting": 10000,
        "bm25_limit": False,
    },
    {
        # k=5, p=100
        "h_match": 0.4,
        "h_rel": 0.2,
        "h_conn": 0.3,
        "h_coh": 0.1,
        "d": 20,
        "k": 5,
        "p_setting": 100,
        "bm25_limit": False,
    },
]

# benchmark paths
BENCHMARKS = [
    ("benchmarks/LC_QuAD20_CQ.json", "lcquad20cq"),
    ("benchmarks/ConvQuestions_FQ.json", "convquestionsfq")
]

# settings for CLOCQ server
HOST = "localhost"
PORT = 7778


"""
FILE PATHS: Only touch if really necessary
"""
ROOT_DIR = os.getcwd()
PATH_TO_DATA_FOLDER = os.path.join(ROOT_DIR, "data")

# CLOCQ-KB
PATH_TO_KB_LIST = os.path.join(PATH_TO_DATA_FOLDER, "kb", "CLOCQ_KB_list.txt")
PATH_TO_KB_DICTS = os.path.join(PATH_TO_DATA_FOLDER, "kb", "dicts")

# HDT path (only required when using HDT instead of CLOCQ-KB)
PATH_TO_HDT_FILE = ""

# stopwords
PATH_TO_STOPWORDS = os.path.join(PATH_TO_DATA_FOLDER, "stopwords.txt")

# wikipedia2VecRelevance paths
PATH_TO_WIKI2VEC_MODEL = os.path.join(PATH_TO_DATA_FOLDER, "enwiki_20180420_300d.pkl")
PATH_TO_WIKIPEDIA_MAPPINGS = os.path.join(PATH_TO_DATA_FOLDER, "kb", "dicts", "wikipedia_mappings.json")
PATH_TO_WIKIDATA_MAPPINGS = os.path.join(PATH_TO_DATA_FOLDER, "kb", "dicts", "wikidata_mappings.json")

# paths to caches (set to None to drop)
PATH_TO_NORM_CACHE = os.path.join(PATH_TO_DATA_FOLDER, "cache", "norm_cache.json")
PATH_TO_WIKI_SEARCH_CACHE = os.path.join(PATH_TO_DATA_FOLDER, "cache", "wikidata_search_cache.json")
PATH_TO_TAGME_NER_CACHE = os.path.join(PATH_TO_DATA_FOLDER, "cache", "tagme_ner_cache.json")


"""
STATIC PARAMETERS: DO NOT TOUCH
"""
# default CLOCQ parameters
DEF_NER = "tagme"
DEF_PARAMS = {
    "h_match": 0.4,
    "h_rel": 0.3,
    "h_conn": 0.2,
    "h_coh": 0.1,
    "d": 20,
    "k": "AUTO",
    "p_setting": 1000,
    "bm25_limit": False,
}
