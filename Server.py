import asyncio
import websockets
import websockets.exceptions
import time


class Game:

	def __init__(self):
		self.ship1 = None
		self.ship2 = None
		self.bullets = []
		self.event_queue = asyncio.Queue()

	def add_ship(self, ws):
		if not(bool(self.ship1) and bool(self.ship2)):
			if not self.ship1:
				self.ship1 = Ship(787, ws)
			else:
				self.ship2 = Ship(387, ws)
		else:
			raise Exception


	async def lead_game(self):
		print('Leading the game...')
		await self.ship1.ws.send('game_entered')
		await self.ship2.ws.send('game_entered')
		print('Matchmaking message sent')
		toolkit = {'move': self.movement_handler}
		while True:
			try:
				received = asyncio.ensure_future(self.event_queue.get())
				while not received.done():
					# TODO: добавить перемещение пуль
					await asyncio.sleep(0.03)
			except websockets.exceptions.ConnectionClosed:
				print('Client fucked away!')
				alive_socket = [i for i in (self.ship1.ws, self.ship2.ws) if not i.closed][0]
				await alive_socket.send('state;enemy_left')
				await alive_socket.close()
				self.finish()
				break

			received = received.result()
			cur_ship = [i for i in (self.ship1, self.ship2) if i.ws == received[-1]][0]
			toolkit[received[0]](cur_ship, received)
			await self.ship1.ws.send(f'positions;you:{self.ship1.x};enemy:{self.ship2.x}')
			await self.ship2.ws.send(f'positions;you:{self.ship2.x};enemy:{self.ship1.x}')


	def movement_handler(self, ship, event):
		ship.move(event[1])

	def finish(self):
		del self.ship1
		del self.ship2
		self.bullets = []


class Ship:

	def __init__(self, x: int, ws):
		self.hp = 100
		self.__x = x
		self.ws = ws

	def move(self, direct: str):
		offsets = {'r': 50, 'l': -50}
		self.__x += offsets[direct]
		print(self.__x)

	@property
	def x(self):
		# Для нормальной обработки игровых событий на сервере и для однозначного отображения боя на клиенте достаточно знать
		# только горизонтальную координату.
		return self.__x


class EventProducer:

	def __init__(self):
		self.games = []

	async def listen(self, websocket, path):
		try:
			async for received in websocket:
				message = received.split(';')
				header = message[0]
				if header != 'enter_game':
					destin_game = [i for i in self.games if i.ship1.ws == websocket or i.ship2.ws == websocket][0]
					message.append(websocket)
					await destin_game.event_queue.put(message)
				else:
					print('Game entrance request received')
					# Добавляем игрока в игру
					# Ищем игры с неполным составом участников, а если нет таких, создаем новую
					waiting_games = [i for i in self.games if bool(i.ship1) != bool(i.ship2)]
					if waiting_games:
						cur_game = waiting_games[0]
					else:
						cur_game = Game()
						self.games.append(cur_game)
					cur_game.add_ship(websocket)
					# Если игра заполняется, запускаем ее
					if cur_game.ship1 and cur_game.ship2:
						asyncio.ensure_future(cur_game.lead_game())
		except websockets.exceptions.ConnectionClosedError:
			pass


async def main():
	producer = EventProducer()
	async with websockets.serve(producer.listen, '127.0.0.1', 9090):
		print('Ready')
		await asyncio.Future()

asyncio.run(main())