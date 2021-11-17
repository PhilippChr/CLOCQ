'''
Create dictionaries mapping from CLOCQ-KB internal ID to Wikidata ID (and inverse).
'''

import pickle
import re

PATH_TO_WIKIDATA_DUMP = "tmp_data/distinct_nodes.csv"
ENT_PATTERN = re.compile('^Q[0-9]+$')
PRE_PATTERN = re.compile('^P[0-9]+$')

ents = dict()
inv_ents = list()
pres = dict()
inv_pres = [None]
literals = dict()
inv_literals = [None]

with open(PATH_TO_WIKIDATA_DUMP, "r") as fp_in:
    print('File opened')
    count = -1
    pre_count = 0
    # start entity_ids from 10000, leaving 10000 unique numbers for predicates
    ent_count = 9999
    lit_count = 0
    line = fp_in.readline()
    while line:
        item = line
        line = fp_in.readline()
        item = item[:-1]
        count += 1
        if item[0] == "Q" and re.match(ENT_PATTERN, item):
            if not ents.get(item):
                ent_count += 1
                ents[item] = ent_count
                inv_ents.append(item)
        elif item[0] == "P" and re.match(PRE_PATTERN, item):
            if not pres.get(item):
                pre_count += 1
                pres[item] = pre_count
                inv_pres.append(item)
        # skip too long strings
        elif len(item) < 40:
            if not literals.get(item):
                lit_count += 1
                literals[item] = lit_count
                inv_literals.append(item)

with open('dicts/entity_nodes.pickle', 'wb') as output:
    pickle.dump(ents, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/pred_nodes.pickle', 'wb') as output:
    pickle.dump(pres, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/literals.pickle', 'wb') as output:
    pickle.dump(literals, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/inverse_entity_nodes.pickle', 'wb') as output:
    pickle.dump(inv_ents, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/inverse_pred_nodes.pickle', 'wb') as output:
    pickle.dump(inv_pres, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/inverse_literals.pickle', 'wb') as output:
    pickle.dump(inv_literals, output, protocol=pickle.HIGHEST_PROTOCOL)

with open('dicts/HIGHEST_ID.txt', 'w') as fp:
    HIGHEST_ID = ent_count + 1
    out = str(HIGHEST_ID)
    fp.write(out)

print (ent_count)
print (pre_count)
print (lit_count)

print('Dicts extracted')