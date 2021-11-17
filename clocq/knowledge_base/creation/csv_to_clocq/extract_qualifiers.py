'''
Creates a dictionary that maps from unique predicate ID (e.g. P21-12)
to the qualifier information of the unique fact
'''

import json

PATH_TO_WIKIDATA_DUMP = "dumps/wikidata_clean.csv"
PATH_TO_OUT = "tmp_data/qualifiers.json"

qualifiers = dict()

# iterate through cleaned csv dump
with open(PATH_TO_WIKIDATA_DUMP, "r") as fp_in:
    count = -1
    line = fp_in.readline()
    while line:
        currentLine = line
        line = fp_in.readline()

        # extract + clean triple components
        s,p,o = currentLine.split(',', 2)
        o = o[:-1]
        count += 1

        # detect qualifier-information triple
        if s[0] == "P":
            if not qualifiers.get(s):
                qualifiers[s] = set()

            # add qualifier information
            p = p.split('-')[0]
            if o[0] == 'Q':
                o = o.split('-', 1)[0]
            qualifiers[s].add((p,o))

    # transform set to list to store it as json
    for q in qualifiers:
        q_set = qualifiers[q]
        q_list = list()
        for q_tup in q_set:
            p,o = q_tup
            q_list.append([p,o])
        qualifiers[q] = q_list

# store dictionary
with open(PATH_TO_OUT, 'w') as output:
    output.write(json.dumps(qualifiers, separators=(',',':')))

print('qualifiers extracted')
