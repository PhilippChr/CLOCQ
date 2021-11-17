## TaskHandler
The TaskHandler was primarily designed to handle any incoming requests on the [website](clocq.mpi-inf.mpg.de).
However, it could also be used internally. The possible functions are exactly the same as for the [CLOCQ class](../CLOCQ.py).
It works as follows:
each usage of CLOCQ is given as a task. A task is represented as a json-object, and consists of the task-name and the parameters.
The task-name has to match exactly any of the function names provided in the [CLOCQ class](../CLOCQ.py), since a task is implemented as such.    
The TaskHandler takes as input a file with a list of such tasks, and writes the result for each task in a .jsonl file.


### Usage
An example usage can be found below:
```python
	from clocq.interface.CLOCQTaskHandler import CLOCQTaskHandler
	
	task_handler = CLOCQTaskHandler()
	
	input_path = "clocq/interface/tests/tasks_example.json"
	output_path = "clocq/interface/tests/tasks_example.jsonl"
	task_handler.process_tasks(input_path, output_path)
```


### Tasks
Example list of tasks that is given to the [CLOCQTaskHandler](CLOCQTaskHandler.py). For each possible task, there is one example, with the excpected input. Optional parameters are shown as such. In case a mandatory argument is missing (or some other problem occurs), the CLOCQTaskHandler will write an empty line for the task into the result file.
A runnable version (without comments) of the following example tasks is given [here](tests/tasks_example.json).

	[	
		// GET LABEL OF KB ITEM
		{
			"task": "get_label",
			"kb_item": "Q31043671"
		},
		// GET LABELS OF KB ITEM
		{
			"task": "get_labels",
			"kb_item": "Q31043671"
		},
		// GET ALIASES OF KB ITEM
		{
			"task": "get_aliases",
			"kb_item": "Q31043671"
		},
		// GET DESCRIPTION OF KB ITEM
		{
			"task": "get_description",
			"kb_item": "Q31043671"
		},
		// GET TYPES OF KB ITEM
		{
			"task": "get_types",
			"kb_item": "Q31043671"
		},
		// GET FREQUENCY OF KB ITEM
		{
			"task": "get_frequency",
			"kb_item": "Q31043671"
		},
		// GET THE 1-HOP NEIGHBORHOOD OF THE KB ITEM
		{
			"task": "get_neighborhood",
			"kb_item": "Q31043671",
			"p": 1000, // OPTIONAL
			"include_labels": true // OPTIONAL
		},
		// GET THE 2-HOP NEIGHBORHOOD OF THE KB ITEM
		{
			"task": "get_neighborhood_two_hop",
			"kb_item": "Q31043671",
			"p": 1000, // OPTIONAL
			"include_labels": true // OPTIONAL
		},
		// GET A CONNECTION BETWEEN THE KB ITEMS
		{
			"task": "connect",
			"kb_item1": "Q31043671",
			"kb_item2": "Q47774"
		},
		// GET THE CONNECTIVITY BETWEEN THE KB ITEMS
		{
			"task": "connect",
			"kb_item1": "Q31043671",
			"kb_item2": "Q47774"
		},
		// GET THE SEARCH SPACE FOR THE QUESTION
		{
			"task": "get_search_space",
			"question": "Who played Arya in Game of Thrones?",
			"parameters": {"p": 1000}, // OPTIONAL
			"include_labels": true // OPTIONAL
		}
	]