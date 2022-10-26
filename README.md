Beyond NED: Fast and Effective Search Space Reduction for   Complex Question Answering over Knowledge Bases
============

- [Description](#description)
- [Code](#code)
    - [System requirements](#system-requirements)
	- [Setup](#setup)
	- [Data](#data)
	- [Using CLOCQ](#using-clocq)
	- [Reproducing paper results](#reproducing-paper-results)
    - [Creation of CLOCQ KB](#creation-of-clocq-kb)
- [CLOCQ for entity linking](#clocq-for-entity-linking)
- [License](#license)

# Description
This repository contains the code and data for our [WSDM 2022 paper](https://arxiv.org/abs/2108.08597#) on search space reduction for KB-QA. In this work, we present a novel KB-index for efficient access to QA-relevant KB functionalities. Leveraging this KB-index, we establish a top-k processing framework, named **CLOCQ**, to disambiguate question words based on four relevance scores. CLOCQ makes use of global signals (connectivity in KB-graph, semantic coherence), and local signals (question relatedness, term-matching) to detect top-k KB-items for each question word. KB-facts involving the disambiguated items are retrieved and constitute the search space.

Since some question words might be more ambiguous than others, we propose a mechanism to automatically set an appropriate k for each question word individually.
Further, highly frequent KB-items like US might occur in millions of KB-facts. To this end, we propose a mechanism based on a pruning threshold p to keep only salient facts in the search space.

For more details, please refer to [the paper](https://arxiv.org/abs/2108.08597#) (will be published at [WSDM 2022](https://www.wsdm-conference.org/2022/)).  
There is also a website available: [https://clocq.mpi-inf.mpg.de](https://clocq.mpi-inf.mpg.de).

If you use this code, please cite:
```bibtex
@inproceedings{christmann2022beyond,
  title={Beyond NED: Fast and Effective Search Space Reduction for Complex Question Answering over Knowledge Bases},
  author={Christmann, Philipp and Saha Roy, Rishiraj and Weikum, Gerhard},
  booktitle={Proceedings of the Fifteenth ACM International Conference on Web Search and Data Mining},
  pages={172--180},
  year={2022}
}
```

# Code

## System requirements
All code was tested on Linux only.  
Note, that the CLOCQ KB-index requires ca. 370 GB of memory (RAM) to be loaded.
While loading the KB, the indexes are established, which takes roughly 2 hours.
It is therefore recommended to run all processes in the background (e.g. using nohup).  


## Setup 
To install the required libraries, it is recommended to create a virtual environment. The CLOCQ-code was developed for Python 3.8.


Using pip (recommended):

```bash
    conda create --name clocq python=3.8
    conda activate clocq
    pip install -e .
```

Next, CLOCQ needs to be initialized by downloading data:

```bash
    nohup bash initialize.sh &
```

Parameters, benchmarks, and file paths can be adjusted in the [config](clocq/config.py).

You will need to add a valid TagME token to the [config](clocq/config.py).  
Details on how you can obtain this token can be found [here](https://sobigdata.d4science.org/web/tagme/).

## Data
We tried CLOCQ on the following datasets:
1. [LC-QuAD2.0-CQ](benchmarks/LC_QuAD20_CQ.json): a set of more complex questions within the LC-QuAD 2.0 dataset. Complexity is loosely identified by the presence of multiple entities, (detected with TagME NER) and/or predicates where main verbs were used as proxy (detected with Stanza).

2. [ConvQuestions-FQ](benchmarks/ConvQuestions_FQ.json): while ConvQuestions was build for conversational QA, well-formed complete questions that exhibit several complex phenomena are also included.


If you would like to use your own benchmarks, you can see [this template](benchmarks/benchmark_format.json) to investigate the expected structure.
The new benchmark needs to be added to the 'BENCHMARKS' parameter in the [config](clocq/config.py) as a (<PATH_TO_BENCHMARK>, <BENCHMARK_NAME>) tuple (e.g. ("benchmarks/LC_QuAD20_CQ.json", "lcquad20cq")).


## Using CLOCQ
There are different possible setups for using CLOCQ within your project.
1. **Static usage of CLOCQ**:  
You can add a new benchmark tuple to the [config](clocq/config.py), and run the [Inference.py](clocq/Inference.py) script. The benchmark should be stored in [this format](benchmarks/benchmark_format.md). The results (search space and disambiguations) for each question are stored in a .json file.

```python
    # Add benchmark to clocq/config.py
    # ...
    BENCHMARKS = [
        ("benchmarks/benchmark_format.json", "benchmark_name")
    ]
    # ...
```

```python
    # Evaluate + store results (on test set)
    nohup python clocq/Inference.py --test --store &
```

```python
    # Evaluate + store results (on dev set)
    nohup python clocq/Inference.py --dev --store &
```


2. **Dynamic usage of CLOCQ - within a single script**:  
If your data is dynamic (e.g. in a realistic setup in which users can pose arbitrary questions at run-time), there is another possibility of using CLOCQ:
you can simply include the [CLOCQ](clocq/CLOCQ.py) class in your python scripts and make use of the provided functions. Note: each instance of the CLOCQInterface will load the whole KB. So make sure to create new instances only if really needed, and pass the reference otherwise. See [the CLOCQ class](clocq/CLOCQ.py) for an overview of all available functions. Example:

```python
    from clocq import CLOCQ
    
    TAGME_TOKEN = "<INSERT YOUR TOKEN HERE>"
    cl = CLOCQ(tagme_token=TAGME_TOKEN)
    
    res = cl.get_label("Q5")
    print(res)
    
    res = cl.get_search_space("who was the screenwriter for Crazy Rich Asians?")
    print(res.keys())
```

3. **Dynamic usage of CLOCQ - within a machine**:  
If multiple scripts require to access the CLOCQ code, a Server-Client setup is recommended. You can start an instance of the [CLOCQInterfaceServer](clocq/interface/CLOCQInterfaceServer.py) at an appropriate port on your localhost (or any other host). Once the server is started, multiple scripts can access CLOCQ in parallel using an instance of the [CLOCQInterfaceClient](clocq/interface/CLOCQInterfaceClient.py) class. [More details](clocq/interface/CLOCQ_Server.md)

4. TaskHandler **(NOT RECOMMENDED)**:  
This is used for handling external requests on the CLOCQ-website. [More details](clocq/interface/CLOCQ_TaskHandler.md)

## Reproducing paper results
Simply run:

```python
	nohup python clocq/Inference.py --test &
```

The results for both benchmarks will be stored in 'results/clocq_test_clocq.res'. The file 'results/clocq_test_clocq.json' holds per-question results for fine-grained analysis.
Additional logs can be found in 'results/clocq_test_clocq.txt'.

## Creation of CLOCQ KB
The CLOCQ KB makes use of the [wikidata-core-for-QA](https://github.com/PhilippChr/wikidata-core-for-QA) repo, which was a joint effort with [Magdalena Kaiser](https://people.mpi-inf.mpg.de/~mkaiser/) to prune irrelevant facts from Wikidata.
So given the latest .nt dump from Wikidata, the dump first needs to be pre-processed as indicated in the repo.  
  
After that, the CLOCQ KB-index can be applied.
This is done using the [csv_to_clocq script](clocq/knowledge_base/creation/csv_to_clocq.sh).


# CLOCQ for entity linking
If you want to use CLOCQ for entity linking, you may find [our pruning module](https://github.com/PhilippChr/CLOCQ-pruning-module/blob/master/README.md) helpful.
The original CLOCQ code is mainly designed for search space reduction, for which linking all mentions was found to be beneficial.
However, on entity linking tasks, this may easily reduce the precision.
Therefore, we proposed a module to prune disambiguated KB items, that are not required for entity linking, to adapt CLOCQ to the entity linking challenge of the [SMART 2022 Task](https://smart-task.github.io/2022/).


# License
The CLOCQ project by [Philipp Christmann](https://people.mpi-inf.mpg.de/~pchristm/), [Rishiraj Saha Roy](https://people.mpi-inf.mpg.de/~rsaharo/) and [Gerhard Weikum](https://people.mpi-inf.mpg.de/~weikum/) is licensed under [MIT license](LICENSE).

