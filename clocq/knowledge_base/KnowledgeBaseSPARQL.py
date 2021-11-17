import json
import pickle
import random
import re
import time
import requests

from config import PATH_TO_KB_DICTS


class KnowledgeBaseSPARQL:
    def __init__(self, path_to_kb_dicts, string_lib):
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        self.string_lib = string_lib
        self.request_wikidata = requests.Session()
        # load dictionaries: integer -> Wikidata ID/literal
        # the name of the dictionaries is fix
        try:
            with open(path_to_kb_dicts + "/labels.json", "r") as infile:
                self.labels_dict = json.load(infile)
            print("Dictionaries successfully loaded.")
        except:
            raise Exception("Paths to dictionaries are invalid! You might have changed the names of the dictionaries!")

    def item_to_single_label(self, item):
        if item is None:
            return "None"
        labels = self.labels_dict.get(item)
        if not labels:
            return "None"
        first_label = next(
            (label for label in labels if not (self.ENT_PATTERN.match(label) or self.PRE_PATTERN.match(label))),
            labels[0]
        )
        return first_label

    def connectivity_check(self, entity1, entity2):
        try:
            statements1 = self._get_all_statements_with_entity(entity1)
            statements2 = self._get_all_statements_with_entity(entity2)
            ngb_items_1 = self._facts_to_item_set(ngb_facts_1)
            ngb_items_2 = self._facts_to_item_set(ngb_facts_2)
            if item1 in ngb_items_2:
                return 1.0
            intersection = ngb_items_1 & ngb_items_2
            res = [i for i in list(intersection) if i[0] != "P"]
            if res:
                return 0.5
            return 0
        except:
            return 0

    def get_neighborhood(self, item, p=1000, include_labels=False):
        try:
            statements = self.get_all_statements_with_entity(item)
            return statements
        except:
            return list()

    def extract_search_space(self, kb_item_tuple, p=1000, include_labels=False):
        context_graph = list()
        for item in kb_item_tuple:
            search_space += self.get_neighborhood(item, p=p, include_labels=include_labels)
        return search_space

    def _facts_to_item_set(self, facts):
        items = set()
        for fact in facts:
            items.update(fact)
        return items

    # {'qualifier_statement' : 'wds:Q36228363-6453800E-BD6E-4013-835C-EF192AB2BB53', 'entity':	{'id': '', 'label': ''}, 'object': {'id': '', 'label': ''}, 'predicate':	{'id': '', 'label': ''}, 'qualifiers': 	[{'qualifier_predicate': {'id': '', 'label': ''}, 'qualifier_object': {'id': '', 'label': ''}},...]}
    def _join_statements_with_new_qualifier(
        self,
        statements,
        qualifier_statement,
        qualifier_predicate,
        qualifier_predicateLabel,
        qualifier_object,
        qualifier_objectLabel,
    ):
        for statement in statements:
            if statement["qualifier_statement"] == qualifier_statement:
                statement["qualifiers"].append(
                    {
                        "qualifier_predicate": {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(qualifier_predicate),
                            "label": qualifier_predicateLabel,
                        },
                        "qualifier_object": {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(qualifier_object),
                            "label": qualifier_objectLabel,
                        },
                    }
                )
        return False

    # entity:	the entity to fetch the properties from
    def _query_statements_with_entity_as_subject(self, entity_id):
        pattern = re.compile("^Q[0-9]+")
        if not (pattern.match(entity_id.strip())):
            return []

        # try to fetch the query from the cache
        query_name = "statements_with_entity_as_subject:" + str(entity_id)

        query = "SELECT DISTINCT ?subject ?subjectLabel ?predicate ?predicateLabel ?object ?objectLabel ?qualifier_statement ?qualifier_predicate ?qualifier_predicateLabel ?qualifier_object ?qualifier_objectLabel {"
        query += "  VALUES (?subject) {( wd:" + entity_id + ")}"
        query += "  VALUES (?object_types) {(wikibase:WikibaseItem) (wikibase:Time) (wikibase:String) (wikibase:Quantity) (wikibase:Url)}"

        query += "  ?subject ?p ?qualifier_statement . "
        query += "  ?qualifier_statement ?ps ?object . "

        query += "  ?predicate wikibase:claim ?p. "
        query += "  ?predicate wikibase:statementProperty ?ps. "

        query += "  ?predicate wikibase:propertyType  ?object_types. "

        query += "  OPTIONAL { "
        query += "    ?qualifier_statement ?pq ?qualifier_object . "
        query += "    ?qualifier_predicate wikibase:qualifier ?pq . "
        query += "  } "

        query += '  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" } '
        query += "} ORDER BY ?subjectLabel ?predicateLabel ?objectLabel "

        res = self.request_wikidata.get(
            "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=" + query
        )
        if not res:
            # print (query)
            return []
        else:
            statements = []
            if len(res.json()["results"]["bindings"]) > 0:
                for binding in res.json()["results"]["bindings"]:

                    # fetch the values from the statement
                    qualifier_statement = binding["qualifier_statement"]["value"]

                    # check if a qualifier was found:
                    if binding.get("qualifier_predicate"):
                        qualifier_predicate_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_predicate"]["value"]
                        )
                        qualifier_predicate_label = binding["qualifier_predicateLabel"]["value"]

                        qualifier_object_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_object"]["value"]
                        )
                        qualifier_object_label = binding["qualifier_objectLabel"]["value"]

                        # try to join the qualifiers of the statements
                        if not self._join_statements_with_new_qualifier(
                            statements,
                            qualifier_statement,
                            qualifier_predicate_id,
                            qualifier_predicate_label,
                            qualifier_object_id,
                            qualifier_object_label,
                        ):

                            # prepare all attributes of the statement
                            entity = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                                "label": binding["subjectLabel"]["value"],
                            }
                            predicate = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                                "label": binding["predicateLabel"]["value"],
                            }
                            object_ = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                                "label": binding["objectLabel"]["value"],
                            }
                            qualifier = {
                                "qualifier_predicate": {
                                    "id": qualifier_predicate_id,
                                    "label": qualifier_predicate_label,
                                },
                                "qualifier_object": {"id": qualifier_object_id, "label": qualifier_object_label},
                            }

                            # add the statement to the list
                            statements.append(
                                {
                                    "qualifier_statement": qualifier_statement,
                                    "entity": entity,
                                    "object": object_,
                                    "predicate": predicate,
                                    "qualifiers": [qualifier],
                                }
                            )
                    else:
                        # prepare all attributes of the statement
                        entity = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                            "label": binding["subjectLabel"]["value"],
                        }
                        predicate = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                            "label": binding["predicateLabel"]["value"],
                        }
                        object_ = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                            "label": binding["objectLabel"]["value"],
                        }

                        # add the statement to the list
                        statements.append(
                            {
                                "qualifier_statement": qualifier_statement,
                                "entity": entity,
                                "object": object_,
                                "predicate": predicate,
                                "qualifiers": [],
                            }
                        )
            return statements

    def _query_statements_with_entity_as_object(self, entity_id):
        pattern = re.compile("^Q[0-9]+")
        if not (pattern.match(entity_id.strip())):
            return []

        # try to fetch the query from the cache
        query_name = "statements_with_entity_as_object:" + str(entity_id)

        # query the other direction (only wikibase item allowed!)
        query = " SELECT DISTINCT ?subject ?subjectLabel ?predicate ?predicateLabel ?object ?objectLabel ?qualifier_statement ?qualifier_predicate ?qualifier_predicateLabel ?qualifier_object ?qualifier_objectLabel {"
        query += "   VALUES (?object) {(wd:" + entity_id + ")}"

        query += "   ?subject ?p ?qualifier_statement . "
        query += "   ?qualifier_statement ?ps ?object . "

        query += "   ?predicate wikibase:claim ?p. "
        query += "   ?predicate wikibase:statementProperty ?ps. "

        query += "   OPTIONAL{"
        query += "   	?qualifier_statement ?pq ?qualifier_object . "
        query += "   	?qualifier_predicate wikibase:qualifier ?pq .} "

        query += '   SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }'
        query += " }"

        res = self.request_wikidata.get(
            "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=" + query
        )
        if not res:
            # print (query)
            return []

        else:
            statements = []
            if len(res.json()["results"]["bindings"]) > 0:
                for binding in res.json()["results"]["bindings"]:
                    # print "hi" + str(entity_id)
                    # fetch the values from the statement
                    qualifier_statement = binding["qualifier_statement"]["value"]

                    # check if a qualifier was found:
                    if binding.get("qualifier_predicate"):
                        qualifier_predicate_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_predicate"]["value"]
                        )
                        qualifier_predicate_label = binding["qualifier_predicateLabel"]["value"]

                        qualifier_object_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_object"]["value"]
                        )
                        qualifier_object_label = binding["qualifier_objectLabel"]["value"]

                        # try to join the qualifiers of the statements
                        if not self._join_statements_with_new_qualifier(
                            statements,
                            qualifier_statement,
                            qualifier_predicate_id,
                            qualifier_predicate_label,
                            qualifier_object_id,
                            qualifier_object_label,
                        ):

                            # prepare all attributes of the statement
                            entity = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                                "label": binding["subjectLabel"]["value"],
                            }
                            predicate = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                                "label": binding["predicateLabel"]["value"],
                            }
                            object_ = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                                "label": binding["objectLabel"]["value"],
                            }
                            qualifier = {
                                "qualifier_predicate": {
                                    "id": qualifier_predicate_id,
                                    "label": qualifier_predicate_label,
                                },
                                "qualifier_object": {"id": qualifier_object_id, "label": qualifier_object_label},
                            }

                            # add the statement to the list
                            statements.append(
                                {
                                    "qualifier_statement": qualifier_statement,
                                    "entity": entity,
                                    "object": object_,
                                    "predicate": predicate,
                                    "qualifiers": [qualifier],
                                }
                            )
                    else:
                        # prepare all attributes of the statement
                        entity = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                            "label": binding["subjectLabel"]["value"],
                        }
                        predicate = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                            "label": binding["predicateLabel"]["value"],
                        }
                        object_ = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                            "label": binding["objectLabel"]["value"],
                        }

                        # add the statement to the list
                        statements.append(
                            {
                                "qualifier_statement": qualifier_statement,
                                "entity": entity,
                                "object": object_,
                                "predicate": predicate,
                                "qualifiers": [],
                            }
                        )

            return statements

    def _query_statements_with_entity_as_qualifier_object(self, entity_id):
        pattern = re.compile("^Q[0-9]+")
        if not (pattern.match(entity_id.strip())):
            return []

        # try to fetch the query from the cache
        query_name = "statements_with_entity_as_qualifier_object:" + str(entity_id)

        # query the other direction (only wikibase item allowed!)
        query = " SELECT DISTINCT ?subject ?subjectLabel ?predicate ?predicateLabel ?object ?objectLabel ?qualifier_statement ?qualifier_predicate ?qualifier_predicateLabel ?qualifier_object ?qualifier_objectLabel {"
        query += "   VALUES (?qualifier_object) {(wd:" + entity_id + ")}"

        query += "   ?subject ?p ?qualifier_statement . "
        query += "   ?qualifier_statement ?ps ?object . "

        query += "   ?predicate wikibase:claim ?p. "
        query += "   ?predicate wikibase:statementProperty ?ps. "

        query += "   ?qualifier_statement ?pq ?qualifier_object . "
        query += "   ?qualifier_predicate wikibase:qualifier ?pq . "

        query += '   SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }'
        query += " }"

        # print(query)
        res = self.request_wikidata.get(
            "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=" + query
        )
        if not res:
            # print (query)
            return []

        else:
            statements = []
            if len(res.json()["results"]["bindings"]) > 0:
                for binding in res.json()["results"]["bindings"]:

                    # fetch the values from the statement
                    qualifier_statement = binding["qualifier_statement"]["value"]

                    # check if a qualifier was found:
                    if binding.get("qualifier_predicate"):
                        qualifier_predicate_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_predicate"]["value"]
                        )
                        qualifier_predicate_label = binding["qualifier_predicateLabel"]["value"]

                        qualifier_object_id = self.string_lib.wikidata_url_to_wikidata_id(
                            binding["qualifier_object"]["value"]
                        )
                        qualifier_object_label = binding["qualifier_objectLabel"]["value"]

                        # try to join the qualifiers of the statements
                        if not self._join_statements_with_new_qualifier(
                            statements,
                            qualifier_statement,
                            qualifier_predicate_id,
                            qualifier_predicate_label,
                            qualifier_object_id,
                            qualifier_object_label,
                        ):

                            # prepare all attributes of the statement
                            entity = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                                "label": binding["subjectLabel"]["value"],
                            }
                            predicate = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                                "label": binding["predicateLabel"]["value"],
                            }
                            object_ = {
                                "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                                "label": binding["objectLabel"]["value"],
                            }
                            qualifier = {
                                "qualifier_predicate": {
                                    "id": qualifier_predicate_id,
                                    "label": qualifier_predicate_label,
                                },
                                "qualifier_object": {"id": qualifier_object_id, "label": qualifier_object_label},
                            }

                            # add the statement to the list
                            statements.append(
                                {
                                    "qualifier_statement": qualifier_statement,
                                    "entity": entity,
                                    "object": object_,
                                    "predicate": predicate,
                                    "qualifiers": [qualifier],
                                }
                            )
                    else:
                        # prepare all attributes of the statement
                        entity = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["subject"]["value"]),
                            "label": binding["subjectLabel"]["value"],
                        }
                        predicate = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["predicate"]["value"]),
                            "label": binding["predicateLabel"]["value"],
                        }
                        object_ = {
                            "id": self.string_lib.wikidata_url_to_wikidata_id(binding["object"]["value"]),
                            "label": binding["objectLabel"]["value"],
                        }

                        # add the statement to the list
                        statements.append(
                            {
                                "qualifier_statement": qualifier_statement,
                                "entity": entity,
                                "object": object_,
                                "predicate": predicate,
                                "qualifiers": [],
                            }
                        )

            return statements

    def _get_all_statements_with_entity(self, entity_id):
        statements = list()
        statements1 = self.__query_statements_with_entity_as_subject(entity_id)
        statements2 = self.__query_statements_with_entity_as_object(entity_id)
        statements3 = self.__query_statements_with_entity_as_qualifier_object(entity_id)
        if statements1:
            statements += self._clean_statements(statements1)
        if statements2:
            statements += self._clean_statements(statements2)
        if statements3:
            statements += self._clean_statements(statements3)
        return statements

    def _clean_statements(self, statements):
        cleaned_statements = list()
        for statement in statements:
            new_statement_set = self._statement_to_item_set(statement)
            new_statement = list(new_statement_set)
            cleaned_statements.append(new_statement)
        return cleaned_statements

    def _statement_to_item_set(self, statement):
        entity_set = set([statement["entity"]["id"], statement["predicate"]["id"], statement["object"]["id"]])
        if statement.get("qualifiers"):
            for qualifier in statement.get("qualifiers"):
                entity_set.add(qualifier["qualifier_predicate"]["id"])
                entity_set.add(qualifier["qualifier_object"]["id"])
        return entity_set
