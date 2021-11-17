## Server
In this setup, a Flask server is started to interact with CLOCQ.
The server can be used on the local machine (localhost), or within a virtual host. The host and port can be specified in the [config](../config.py).
Starting the server will take 2 hours roughly, for loading the KB.

### Starting the server
```bash
	nohup python clocq/interface/CLOCQInterfaceServer.py > clocq/interface/SERVER.out &
```

## Client
After the server has started, one can create clients to interact with CLOCQ.
The possible functionalities can be found in [CLOCQInterfaceClient.py](CLOCQInterfaceClient.py).
It is possible to use the CLOCQ algorithm, but one can also simply make use of the CLOCQ KB-index,
and query e.g. labels or types of specific entities.

### Using the client
```python
	from clocq import config
	from clocq.interface.CLOCQInterfaceClient import CLOCQInterfaceClient

	clocq = CLOCQInterfaceClient(host=config.HOST, port=config.PORT)

	kb_item = "Q5"
	res = clocq.get_label(kb_item)
	print(res)
```