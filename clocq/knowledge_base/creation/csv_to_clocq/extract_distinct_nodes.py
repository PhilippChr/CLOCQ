'''
Extracts all distinct items from the KB.
Unique predicate IDs are not considered here,
i.e. P21-1 and P21-2 are treated as identical.
to the qualifier information of the unique fact
'''

import time
import pickle
import numpy as np

PATH_TO_WIKIDATA_DUMP = "dumps/wikidata_clean.csv"
PATH_TO_OUT = "tmp_data/distinct_nodes.csv"

items = set()

with open(PATH_TO_WIKIDATA_DUMP, "r") as fp_in:
    with open(PATH_TO_OUT, "a") as fp_out:
        count = -1
        line = fp_in.readline()
        res = ""
        while line:
            ids = line
            line = fp_in.readline()
            ids = ids[:-1]
            ids = ids.split(",", 2)
            if len(ids) > 3:
                print ("Too many items!!")
            for item in ids:
                count += 1

                if len(item) < 1:
                    continue
                if item[0] == "Q" or item[0] == "P":
                    item = item.split('-')[0]
                    if item in items:
                        continue
                    else:
                        items.add(item)
                        res += item + "\n" 
                elif len(item) < 40:
                    if item in items:
                        continue
                    else:
                        items.add(item)
                        res += item + "\n" 

                if count % 1000000 == 0:
                    fp_out.write(res)
                    res = ""
                    count = 0
        fp_out.write(res)    

print("distinct nodes extracted")