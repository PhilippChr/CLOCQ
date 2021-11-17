import json

from clocq.CLOCQ import CLOCQ

class CLOCQTaskHandler:
	def __init__(self, dev=False):
		self.clocq = CLOCQ(dev=dev)

	def process_tasks(self, input_path, output_path):
		""" 
		Load the list of tasks from the input file, and write the output into the output file.
		Each line in the output is a json object (.jsonl format).
		"""
		with open(input_path, "r") as fp:
			tasks = json.load(fp)
		# process tasks
		with open(output_path, "a") as output_file:
			for task in tasks:
				self._process_task(task, output_file)

	def _process_task(self, task, output_file):
		"""
		Process the given task and write the output into the file.
		"""
		method = getattr(self.clocq, task["task"])
		args = {key: task[key] for key in task if not key == "task"}
		res = method(**args)
		output_file.write(json.dumps(res))
		output_file.write("\n")


"""
MAIN
"""
if __name__ == "__main__":
	task_handler = CLOCQTaskHandler(dev=True)
	
	input_path = "clocq/interface/tasks_example.json"
	output_path = "clocq/interface/tasks_example.jsonl"
	task_handler.process_tasks(input_path, output_path)