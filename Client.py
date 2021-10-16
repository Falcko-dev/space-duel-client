from PlayLib import *
import threading
import asyncio
import websockets, websockets.exceptions
import queue
import sys

input_queue = queue.Queue()
output_queue = queue.Queue()


class Communicator:
	def __init__(self):
		self.uri = 'ws://127.0.0.1:9090'
		# self.uri = 'ws://space-duel-online.herokuapp.com:80'
		self.closed = False

	async def communicate(self):
		self.ws = await websockets.connect(self.uri)
		print('Connected!')

	async def receive_from_ui(self):
		toolkit = {'move': self.move_handler,
				   'enter_game': self.start_handler,
				   'close_app': self.close_app_handler,
				   'stop': self.stop_handler,
				   'shoot': self.shoot_handler}
		while True:
			try:
				outcome_event = await asyncio.get_running_loop().run_in_executor(None, output_queue.get)
				# Обрабатываем запрос от графического потока
				await toolkit[outcome_event['type']](outcome_event)
			except queue.Empty:
				pass

	async def receive_from_server(self):
		while True:
			try:
				if not self.closed:
					event = await self.ws.recv()
					input_queue.put(event)
			except websockets.exceptions.ConnectionClosedOK:
				sys.exit()


	async def move_handler(self, command):
		if command['dir'] in ('r', 'l'):
			await self.ws.send(f'move;{command["dir"]}')

	async def start_handler(self, command):
		print('Starting the game...')
		await self.ws.send('enter_game')

	async def close_app_handler(self, command):
		self.closed = True
		await self.ws.close()
		sys.exit()

	async def stop_handler(self, command):
		await self.ws.send('stop')

	async def shoot_handler(self, command):
		await self.ws.send('shoot')


async def net_thread_inst():
	communicator = Communicator()
	await communicator.communicate()
	await asyncio.gather(communicator.receive_from_server(), communicator.receive_from_ui())


ui_thread = threading.Thread(target=ui_thread_inst, args=(input_queue, output_queue))
ui_thread.start()
asyncio.run(net_thread_inst())