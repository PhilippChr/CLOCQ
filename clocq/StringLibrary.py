import json
import re
import time
import os

import requests
import spacy
import stanza


class StringLibrary:
    def __init__(self, path_to_stopwords, tagme_token="", path_to_tagme_ner_cache=None):
        # load stopwords
        with open(path_to_stopwords, "r") as fp:
            self.stopwords = fp.read().split("\n")

        # create session for faster connections
        self.request_session = requests.Session()

        # initialize TagME (default NER)
        self.path_to_tagme_ner_cache = path_to_tagme_ner_cache
        self._initialize_tagme_NER_cache()
        self.cache_changed = False
        self.tagme_token = tagme_token

    def _initialize_tagme_NER_cache(self):
        """
        Initialize a TagME NER cache, either from an existing
        file (if given), or as a runtime cache.
        """
        if self.path_to_tagme_ner_cache:
            with open(self.path_to_tagme_ner_cache, "r") as fp:
                self.tagme_NER_cache = json.load(fp)
        else:
            self.tagme_NER_cache = dict()

    def store_tagme_NER_cache(self):
        """Store the TagME NER cache on disk."""
        if self.path_to_tagme_ner_cache and self.cache_changed:
            with open(self.path_to_tagme_ner_cache, "w") as fp:
                json.dump(self.tagme_NER_cache, fp)

    def get_question_words(self, question, ner="tagme", nlp=None):
        """
        Extracts a list of question words from the question.
        Named entity phrases can be detected by the specified ner method.
        If 'ner' is set to False, each word is considered individually.
        Stopwords, symbols and punctuations are removed.
        """
        question_words = []
        # apply NER
        entity_spots = self._apply_NER(question, ner, nlp)
        for spot in entity_spots:
            if spot.lower() in self.stopwords:
                continue
            question = question.replace(spot, "")
            question_words.append(spot)
        # remove symbols
        question = (
            question.replace(",", "")
            .replace("!", "")
            .replace("?", "")
            .replace(".", "")
            .replace("'", "")
            .replace('"', "")
            .replace(":", "")
            .replace("’", "")
            .replace("{", "")
            .replace("}", "")
        )
        # expand the question by whitespaces to be able to find the stopwords
        question = (" " + question + " ").lower()
        # remove stopwords
        for stopword in self.stopwords:
            while " " + stopword + " " in question:
                question = question.replace(" " + stopword + " ", " ")
        # remove remaining s from plural or possesive expressions
        question = question.replace(" s ", " ")
        # remove double whitespaces
        while "  " in question:
            question = question.replace("  ", " ")
        # remove the whitespace(s) at the front and end
        question = question.strip()
        # get all question words
        question_words += question.split(" ")
        question_words = [question_word for question_word in question_words if question_word.strip()]
        return question_words

    def _apply_NER(self, question, ner="tagme", nlp=None):
        """
        Apply the given NER method on the question.
        Returns all detected entity mentions.
        """
        if ner is None:
            return []
        elif ner == "tagme":
            return self.tagme_NER(question)
        elif ner == "spacy":
            return self.spacy_NER(question, nlp)
        elif ner == "stanza":
            return self.stanza_NER(question, nlp)

    def tagme_NER(self, question, recursion_depth=0):
        """
        Apply the TagME NER method on the question.
        Returns all detected entity mentions.
        """
        # check whether result is there in cache
        if recursion_depth == 5:
            return []
        if self.tagme_NER_cache.get(question):
            return self.tagme_NER_cache[question]
        try:
            results = self.request_session.get(
                "https://tagme.d4science.org/tagme/spot?lang=en&gcube-token=" + self.tagme_token + "&text=" + question
            ).json()
            entity_spots = []
            for result in results["spots"]:
                entity_spots.append(result["spot"])
            # store result in cache
            self.tagme_NER_cache[question] = entity_spots
            self.cache_changed = True
            return entity_spots
        except:
            time.sleep(1)
            return self.tagme_NER(question, recursion_depth=recursion_depth+1)

    def spacy_NER(self, question, spacy_nlp):
        """
        Apply the spaCy NER method on the question.
        Returns all detected entity mentions.
        """
        doc = spacy_nlp(question)
        entities = list()
        for ent in doc.ents:
            entities.append(ent.text)
        return entities

    def stanza_NER(self, question, stanza_nlp):
        """
        Apply the stanza NER method on the question.
        Returns all detected entity mentions.
        """
        doc = stanza_nlp(question)
        entities = [entity.text for entity in doc.ents]
        return entities

    def tagme_NED(self, question, recursion_depth=0):
        """
        Apply the TagME NED method on the question.
        Returns all entities (Wikipedia links).
        """
        if recursion_depth == 5:
            return []
        try:
            results = self.request_session.get(
                "https://tagme.d4science.org/tagme/tag?lang=en&gcube-token=" + self.tagme_token + "&text=" + question
            ).json()
            entities = []
            for result in results["annotations"]:
                if result.get("title"):
                    entities.append(result["title"])
            return entities
        except:
            time.sleep(1)
            return self.tagme_NED(question, recursion_depth=recursion_depth+1)

    def convert_month_to_number(self, month):
        """Map the given month to a number."""
        return {
            "january": "01",
            "february": "02",
            "march": "03",
            "april": "04",
            "may": "05",
            "june": "06",
            "july": "07",
            "august": "08",
            "september": "09",
            "october": "10",
            "november": "11",
            "december": "12",
        }[month.lower()]

    def wikidata_url_to_wikidata_id(self, url):
        """Extract the Wikidata id from a Wikidata url."""
        if not url:
            return url
        if "XMLSchema#dateTime" in url or "XMLSchema#decimal" in url:
            date = url.split('"', 2)[1]
            date = date.replace("+", "")
            return date
        if not ("www.wikidata.org" in url):
            if self.is_year(url):
                return self.convert_year_to_timestamp(url)
            if self.is_date(url):
                return self.convert_date_to_timestamp(url)
            else:
                url = url.replace('"', "")
                return url
        else:
            url_array = url.split("/")
            # the Wikidata id is always in the last component of the id
            return url_array[len(url_array) - 1]

    def convert_year_to_timestamp(self, year):
        """Convert a year to a timestamp style."""
        return year + "-01-01T00:00:00Z"

    def convert_date_to_timestamp(self, date):
        """Convert a date from the Wikidata frontendstyle to timestamp style."""
        sdate = date.split(" ")
        # add the leading zero
        if len(sdate[0]) < 2:
            sdate[0] = "0" + sdate[0]
        return sdate[2] + "-" + self.convert_month_to_number(sdate[1]) + "-" + sdate[0] + "T00:00:00Z"

    def is_date(self, date):
        """Return if the given string is a date."""
        pattern = re.compile("^[0-9]+ [A-z]+ [0-9][0-9][0-9][0-9]$")
        if not (pattern.match(date.strip())):
            return False
        else:
            return True

    def is_year(self, year):
        """Return if the given string describes a year in the format YYYY."""
        pattern = re.compile("^[0-9][0-9][0-9][0-9]$")
        if not (pattern.match(year.strip())):
            return False
        else:
            return True

    def is_timestamp(self, timestamp):
        """Return if the given string is a timestamp."""
        pattern1 = re.compile('^"[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T00:00:00Z"')
        pattern2 = re.compile("^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T00:00:00Z")
        if pattern1.match(timestamp.strip()) or pattern2.match(timestamp.strip()):
            return True
        else:
            return False

    def get_year(self, timestamp):
        """Extract the year from the given timestamp."""
        return timestamp.split("-")[0]
