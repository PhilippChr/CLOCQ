'''
Create the KB list. From the structure of statements
ENTITY - PREDICATE - ENTITY/LITERAL [PREDICATE - ENTITY/LITERAL]*
the end of a fact can be inferred without an explicit delimiter.
'''

import time
import pickle
import json
import numpy as np
import re

PATH_TO_WIKIDATA_DUMP = "dumps/wikidata_clean.csv"
PATH_TO_OUT = "dumps/CLOCQ_KB_list.csv"

ENT_PATTERN = re.compile('^Q[0-9]+$')
PRE_PATTERN = re.compile('^P[0-9]+$')

def compress(item):
    if item[0] == "Q" and re.match(ENT_PATTERN, item):
        return str(entity_nodes[item])
    elif item[0] == "P" and re.match(PRE_PATTERN, item):
        return str(pred_nodes[item])
    elif len(item) < 40:
        return str(-literals[item])
    else:
        print("fail")
        print(item)
        return "None"

with open('dicts/entity_nodes.pickle', 'rb') as file:
    entity_nodes = pickle.load(file)

with open('dicts/pred_nodes.pickle', 'rb') as file:
    pred_nodes = pickle.load(file)

with open('dicts/literals.pickle', 'rb') as file:
    literals = pickle.load(file)

with open('tmp_data/qualifiers.json', 'r') as input_file:
    qualifiers = json.load(input_file)

print('Opened data')

with open(PATH_TO_WIKIDATA_DUMP, "r") as fp_in:
    with open(PATH_TO_OUT, 'a') as output:
        print('file opened')
        counter = 0
        line = fp_in.readline()
        while line:
            currentLine = line
            line = fp_in.readline()
            fact = None
            s,p,o = currentLine.split(',', 2)

            o = o[:-1]
            if o[0] == 'Q':
                o = o.split('-', 1)[0]
            counter += 1

            if s[0] == "Q":
                fact = (s, p.split('-')[0], o)
                if qualifiers.get(p):
                    fact = fact + tuple([qualifier for qualifier in qualifiers[p]])
                    del qualifiers[p]

            # remove strings with >= 40 chars
            if not re.match(ENT_PATTERN, o) and len(o) >= 40:
                fact = None
                continue

            if fact:
                s,p,o = fact[0:3]
                output.write(compress(s) + "\n")
                output.write(compress(p) + "\n")
                output.write(compress(o) + "\n")

                if len(fact) > 3:
                    quals = fact[3:]
                    for qual in quals:
                        qp,qo = qual
                        # remove strings with >= 40 chars
                        if not re.match(ENT_PATTERN, qo) and len(qo) >= 40:
                            continue
                        output.write(compress(qp) + "\n")
                        output.write(compress(qo) + "\n")
                fact = None
print('CLOCQ-KB list created')
