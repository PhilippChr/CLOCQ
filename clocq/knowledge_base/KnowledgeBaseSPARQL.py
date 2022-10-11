import json
import pickle
import random
import re
import time
import requests

from string import Template


class IncorrectTypeException(Exception):
    pass

class BadResponseException(Exception):
    pass

class KnowledgeBaseSPARQL:
    def __init__(self, path_to_kb_dicts, string_lib):
        self.ENT_PATTERN = re.compile("^Q[0-9]+$")
        self.PRE_PATTERN = re.compile("^P[0-9]+$")
        self.string_lib = string_lib
        self.request_wikidata = requests.Session()
        # load dictionaries: integer -> Wikidata ID/literal
        # the name of the dictionaries is fix
        try:
            with open(path_to_kb_dicts + "/HIGHEST_ID.txt", "r") as fp:
                HIGHEST_ID = fp.readline().strip()
                self.HIGHEST_ID = int(HIGHEST_ID)
            with open(path_to_kb_dicts + "/inverse_entity_nodes.pickle", "rb") as fp:
                self.inv_ents = pickle.load(fp)
            with open(path_to_kb_dicts + "/inverse_pred_nodes.pickle", "rb") as fp:
                self.inv_pres = pickle.load(fp)
            with open(path_to_kb_dicts + "/inverse_literals.pickle", "rb") as fp:
                self.inv_lits = pickle.load(fp)
            with open(path_to_kb_dicts + "/labels.pickle", "rb") as fp:
                self.labels_dict = pickle.load(fp)
            print("Dictionaries successfully loaded.")
        except:
            raise Exception("Paths to dictionaries are invalid! You might have changed the names of the dictionaries!")

        self.query_template = Template("""
            SELECT DISTINCT ?subject ?subjectLabel ?predicate ?predicateLabel ?object ?objectLabel ?qualifier_statement ?qualifier_predicate ?qualifier_predicateLabel ?qualifier_object ?qualifier_objectLabel {
                VALUES ($position) {($binding)}

                ?subject ?p ?qualifier_statement .
                ?qualifier_statement ?ps ?object .

                ?predicate wikibase:claim ?p .
                ?predicate wikibase:statementProperty ?ps .

                $optional {
                    ?qualifier_statement ?pq ?qualifier_object .
                    ?qualifier_predicate wikibase:qualifier ?pq .
                }

                SERVICE wikibase:label { bd:serviceParam wikibase:language 'en' }
            }
        """)
        self.sparql_headers = {'User-Agent': 'CLOCQ-experiment/1.0 (https://clocq.mpi-inf.mpg.de; pchristm@mpi-inf.mpg.de)'}
        self.sparql_endpoint = "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query="

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

    def _is_entity(self, integer_encoded_item):
        """Return whether encoded item is entity."""
        return integer_encoded_item >= 10000

    def _is_predicate(self, integer_encoded_item):
        """Return whether encoded item is predicate."""
        return integer_encoded_item > 0 and integer_encoded_item < 10000

    def _is_literal(self, integer_encoded_item):
        """Return whether encoded item is literal."""
        return integer_encoded_item < 0

    def _integer_to_item(self, integer_encoded_item):
        """Decode the integer to the KB-item."""
        if self._is_entity(integer_encoded_item):
            return self.inv_ents[integer_encoded_item - 10000]
        elif self._is_predicate(integer_encoded_item):
            return self.inv_pres[integer_encoded_item]
        elif self._is_literal(integer_encoded_item):
            return self.inv_lits[-integer_encoded_item]
        else:
            raise Exception("Failure in _integer_to_item with integer_encoded_item: " + str(integer_encoded_item))

    def connectivity_check(self, item1, item2):
        """
        Check connectivity between the two items.
        Returns:    1   if items in 1-hop,
                    0.5 if items in 2-hop,
                    0   else
        """
        statements1 = self.get_neighborhood(item1)
        statements2 = self.get_neighborhood(item2)
        ngb_items_1 = self._facts_to_item_set(statements1)
        ngb_items_2 = self._facts_to_item_set(statements2)
        if len(ngb_items_1) < len(ngb_items_2):
            if item2 in ngb_items_1:
                return 1.0
        else:
            if item1 in ngb_items_2:
                return 1.0
        intersection = ngb_items_1 & ngb_items_2
        res = [i for i in list(intersection) if i[0] != "P"]
        if res:
            return 0.5
        return 0

    def distance(self, item1, item2, depth=0):
        """Compute the distance between the two items."""
        if depth == 7: # fallback to avoid getting stuck in recursion
            return 7
        conn = self.connectivity_check(item1, item2)
        if conn == 1.0:
            return 1
        elif conn == 0.5:
            return 2
        statements1 = self.get_neighborhood(item1)
        statements2 = self.get_neighborhood(item2)
        ngb_items_1 = self._facts_to_item_set(statements1)
        ngb_items_2 = self._facts_to_item_set(statements2)
        if len(ngb_items_1) + len(ngb_items_2) == 0: return 0
        if len(ngb_items_1) < len(ngb_items_2):
            if len(ngb_items_1) > 0: 
                return min([self.distance(item, item2, depth=depth+1) for item in ngb_items_1]) + 1
            else:
                return min([self.distance(item, item1, depth=depth+1) for item in ngb_items_2]) + 1
        else:
            if len(ngb_items_2) > 0:
                return min([self.distance(item, item1, depth=depth+1) for item in ngb_items_2]) + 1
            else:
                return min([self.distance(item, item2, depth=depth+1) for item in ngb_items_1]) + 1

    def get_neighborhood(self, item, p=1000, include_labels=False):
        """Retrieve 1-hop KB neighborhood of the KB-item."""
        if self.ENT_PATTERN.match(item):
            statements = self._get_all_statements_with_entity(item)
        elif self.PRE_PATTERN.match(item):
            statements = self._get_all_statements_with_predicate(item)
        else:
            return list()
        if statements == False:
            raise BadResponseException()
        return statements

    def connect(self, item1, item2, hop=None):
        """Return a list of 1-hop paths or 2-hop paths between the items."""
        if not hop:
            hop = self.connectivity_check(item1, item2)
        if hop == 1:
            return self._find_connections_1_hop(item1, item2)
        elif hop == 0.5:
            return self._find_connections_2_hop(item1, item2)
        else:
            return None

    def _find_connections_1_hop(self, item1, item2):
        """Return a list of facts with item1 and item2."""
        neighborhood1 = self.get_neighborhood(item1)
        neighborhood2 = self.get_neighborhood(item2)
        len1 = len(neighborhood1)
        len2 = len(neighborhood2)
        connections = list()
        if len1 > len2:
            for fact in neighborhood2:
                if item1 in fact:
                    connections.append(fact)
        else:
            for fact in neighborhood1:
                if item2 in fact:
                    connections.append(fact)
        return connections

    def _find_connections_2_hop(self, item1, item2):
        """
        Return a list of facts with item1 and item_between_item1_and_item2,
        and a list of facts with item_between_item1_and_item2 and item2.
        """
        connections = list()
        neighbors1 = set([item for fact in self.get_neighborhood(item1) for item in fact])
        neighbors2 = set([item for fact in self.get_neighborhood(item2) for item in fact])
        items_in_the_middle = neighbors1 & neighbors2
        if not items_in_the_middle:
            return connections
        for item_in_the_middle in items_in_the_middle:
            # skip extremely frequent items
            if sum(self.get_frequency(item_in_the_middle)) > 100000:
                continue
            connections1 = self._find_connections_1_hop(item1, item_in_the_middle)
            connections2 = self._find_connections_1_hop(item_in_the_middle, item2)
            connection = [connections1, connections2]
            connections.append(connection)
        return connections

    def get_frequency(self, item):
        def _process_res(res):
            if not res:
                return 0
            else:
                count = res.json()["results"]["bindings"][0]["count"]["value"]
                return count
        # for entity
        if item[0] == "Q":
            # entity as subject
            query = f"""SELECT (COUNT(*) as ?count) WHERE {{
                            wd:{item} ?p ?o
                        }}"""
            res = self.request_wikidata.get(self.sparql_endpoint + query)
            count1 = int(_process_res(res))

            # entity as object/qualifier object
            query = f"""SELECT (COUNT(*) as ?count) WHERE {{
                            ?s ?p wd:{item}
                        }}"""
            res = self.request_wikidata.get(self.sparql_endpoint + query)
            count2 = int(_process_res(res))
            return [count1, count2]
        else:
            # predicate as main predicate
            query = f"""SELECT (COUNT(*) as ?count) WHERE {{
                            ?s wdt:{item} ?o
                        }}"""
            res = self.request_wikidata.get(self.sparql_endpoint + query)
            count1 = int(_process_res(res))

            # predicate as qualifier predicate
            query = f"""SELECT (COUNT(*) as ?count) WHERE {{
                            ?s p:{item} ?o
                        }}"""
            res = self.request_wikidata.get(self.sparql_endpoint + query)
            count2 = int(_process_res(res))
            return [0, count1+count2]

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

    def _query_statements_with_entity_as_subject(self, entity_id):
        query = self.query_template.substitute(position="?subject", binding=f"wd:{entity_id}", optional="OPTIONAL")
        statements = self._process_query(query, f"Facts with {entity_id} as subject empty")
        return statements

    def _query_statements_with_entity_as_object(self, entity_id):
        query = self.query_template.substitute(position="?object", binding=f"wd:{entity_id}", optional="OPTIONAL")
        statements = self._process_query(query, f"Facts with {entity_id} as object empty")
        return statements

    def _query_statements_with_entity_as_qualifier_object(self, entity_id):
        query = self.query_template.substitute(position="?qualifier_object", binding=f"wd:{entity_id}", optional="")
        statements = self._process_query(query, f"Facts with {entity_id} as qualifier_object empty")
        return statements

    def _query_statements_with_predicate_as_predicate(self, predicate_id):
        query = self.query_template.substitute(position="?predicate", binding=f"wd:{predicate_id}", optional="OPTIONAL")
        statements = self._process_query(query, f"Facts with {predicate_id} as predicate empty")
        return statements

    def _query_statements_with_predicate_as_qualifier_predicate(self, predicate_id):
        query = self.query_template.substitute(position="?qualifier_predicate", binding=f"wd:{predicate_id}", optional="")
        statements = self._process_query(query, f"Facts with {predicate_id} as qualifier_predicate empty")
        return statements

    def _get_all_statements_with_entity(self, entity_id):
        statements = list()
        try:
            statements1 = self._query_statements_with_entity_as_subject(entity_id)
            statements2 = self._query_statements_with_entity_as_object(entity_id)
            statements3 = self._query_statements_with_entity_as_qualifier_object(entity_id)
        except BadResponseException as e:
            return False
        if statements1:
            statements += self._clean_statements(statements1)
        if statements2:
            statements += self._clean_statements(statements2)
        if statements3:
            statements += self._clean_statements(statements3)
        return statements

    def _get_all_statements_with_predicate(self, predicate_id):
        statements = list()
        try:
            statements1 = self._query_statements_with_predicate_as_predicate(predicate_id)
            statements2 = self._query_statements_with_predicate_as_qualifier_predicate(predicate_id)
        except BadResponseException as e:
            return False
        if statements1:
            statements += self._clean_statements(statements1)
        if statements2:
            statements += self._clean_statements(statements2)
        return statements

    def _clean_statements(self, statements):
        cleaned_statements = list()
        for statement in statements:
            new_statement_set = self._statement_to_item_set(statement)
            new_statement = list(new_statement_set)
            cleaned_statements.append(new_statement)
        return cleaned_statements

    def _statement_to_item_set(self, statement):
        return set(statement)

    def _process_query(self, query, error_message="Error when processing query!"):
        try:
            res = None
            res = self.request_wikidata.get(self.sparql_endpoint + query, headers=self.sparql_headers)
            json.loads(res.content)["results"]["bindings"]
        except:
            if res and res.status_code == 500 and "TimeoutException" in res.content:
                print(error_message + ": timeout for the query")
            elif res == None:
                raise BadResponseException(error_message)
            else:
                raise BadResponseException(error_message)

        statements = self._parse_result(json.loads(res.content))
        return statements

    def _parse_result(self, result_json):
        statements = []
        if len(result_json["results"]["bindings"]) > 0:
            for binding in result_json["results"]["bindings"]:
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
                    statements.append({
                        "qualifier_statement": qualifier_statement,
                        "entity": entity,
                        "object": object_,
                        "predicate": predicate,
                        "qualifiers": [],
                    }) 

        # obtain facts
        facts = list()
        for statement in statements:
            fact = [statement["entity"]["id"], statement["predicate"]["id"], statement["object"]["id"]]
            for qualifier in statement["qualifiers"]:
                fact += [qualifier["qualifier_predicate"]["id"], qualifier["qualifier_object"]["id"]]
            facts.append(fact)
        return facts

