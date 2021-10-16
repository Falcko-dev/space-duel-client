import queue
import pygame, sys
import os
import datetime
import pygame_gui

out_queue_glob: queue.Queue
ping_glob = 0


class Bullet(pygame.sprite.Sprite):

	def __init__(self, parent, idle_image, start_pos, shooter):
		pygame.sprite.Sprite.__init__(self)
		self.parent = parent
		self.image = pygame.image.load(idle_image)
		self.rect = self.image.get_rect()
		self.shooter = shooter
		if self.shooter == 'you':
			self.rect.centerx = start_pos
			self.rect.centery = 920
		else:
			self.rect.centerx = 1500 - start_pos
			self.rect.centery = 80

	def update(self):
		if self.shooter == 'you':
			self.rect.centery -= 50
		else:
			self.rect.centery += 50
		self.parent.blit(self.image, self.rect)


class Spaceship(pygame.sprite.Sprite):

	def __init__(self, parent, idle_image, injury_image, explosion_image, bullets_group):
		pygame.sprite.Sprite.__init__(self)
		self.parent = parent
		self.__hp = 100

		self.idle = pygame.image.load(idle_image)
		self.wounded = pygame.image.load(injury_image)
		self.explosion = pygame.image.load(explosion_image)
		self.image = self.idle
		self.rect = self.image.get_rect()
		self.rect.center = [0, 0]

		self.bullets_group: pygame.sprite.Group = bullets_group

		self.image_reset_timer = 0

	@property
	def hp(self):
		return self.__hp

	@hp.setter
	def hp(self, value):
		self.__hp = value
		if self.hp <= 0:
			self.image = self.explosion
		else:
			self.image = self.wounded
		self.image_reset_timer = pygame.time.get_ticks()

	def set_pos(self, pos):
		if self.hp > 0:
			self.rect.center = pos

	def update(self):
		if self.image_reset_timer and pygame.time.get_ticks() - self.image_reset_timer <= 3:
			self.image = self.idle
		self.parent.blit(self.image, self.rect)


def ui_thread_inst(in_queue, out_queue):
	# Для handler-ов
	global out_queue_glob
	out_queue_glob = out_queue

	pygame.init()
	SCENE = pygame.display.set_mode((1500, 1000))
	UI_MANAGER = pygame_gui.UIManager((1500, 1000), 'Themes/General.json')

	FPS = 50
	clock = pygame.time.Clock()
	FILL_COLOR = (53, 24, 92)

	ships_group = pygame.sprite.Group()
	bullets_group = pygame.sprite.Group()

	out_queue.put({'type': 'enter_game'})
	while True:
		try:
			game_start_trigger = in_queue.get_nowait()
			if game_start_trigger == 'game_entered':
				break
		except queue.Empty:
			SCENE.fill(FILL_COLOR)
			pygame.display.update()
			clock.tick(FPS)

	print('Game started')
	server_events_toolkit = {'positions': place_ships,
							 'state': handle_state,
							 'new_bullet': lambda event, player, enemy: handle_new_bullet(event, bullets_group, SCENE),
							 'hp': handle_hp}
	image_files = [os.path.join('Sprites', i) for i in ('BlueShipIdle.png', 'BlueShipWounded.png', 'Explosion.png',
													   'RedShipIdle.png', 'RedShipWounded.png', 'Explosion.png')]
	player = Spaceship(SCENE, *image_files[:3], bullets_group)
	player.set_pos((500, 935))
	player_is_moving = False
	enemy = Spaceship(SCENE, *image_files[3:], bullets_group)
	enemy.set_pos((1000, 65))
	ships_group.add(player)
	ships_group.add(enemy)

	ping_label = pygame_gui.elements.UILabel(pygame.Rect((1380, 90, 90, 50)), 'Ping: ', UI_MANAGER)
	while True:
		# TODO: Сделать просмотр очереди событий, создание игровых объектов, реакцию на действия пользователя, добавление событий
		#  в очередь на отправку.
		#  Пули обновляются после кораблей.
		SCENE.fill(FILL_COLOR)
		try:
			server_event = in_queue.get_nowait()
			server_events_toolkit[server_event.split(';')[0]](server_event, player, enemy)
		except queue.Empty:
			pass

		inner_events = pygame.event.get()
		for i in inner_events:
			if i.type == pygame.QUIT:
				out_queue.put({'type': 'close_app'})
				sys.exit()
			elif i.type == pygame.KEYDOWN:
				if i.key in (pygame.K_RIGHT, pygame.K_LEFT):
					if not player_is_moving:
						player_is_moving = True
						if i.key == pygame.K_RIGHT:
							out_queue.put({'type': 'move', 'dir': 'r'})
						elif i.key == pygame.K_LEFT:
							out_queue.put({'type': 'move', 'dir': 'l'})
			elif i.type == pygame.KEYUP:
				if i.key in (pygame.K_RIGHT, pygame.K_LEFT):
					out_queue.put({'type': 'stop'})
					player_is_moving = False
				elif i.key == pygame.K_SPACE:
					out_queue.put({'type': 'shoot'})
			UI_MANAGER.process_events(i)
		bullets_group.update()
		ships_group.update()
		ping_label.set_text(f'Ping: {ping_glob}')
		UI_MANAGER.update(clock.tick(FPS))
		UI_MANAGER.draw_ui(SCENE)
		pygame.display.update()


def place_ships(event_string, player: Spaceship, enemy: Spaceship):
	global ping_glob
	parsed = event_string.split(';')[1:]
	player_x = int(parsed[0].split(':')[1])
	enemy_x = 1500 - int(parsed[1].split(':')[1])
	player.set_pos((player_x, 935))
	enemy.set_pos((enemy_x, 65))

	cur_datetime = datetime.datetime.utcnow()
	cur_time = cur_datetime.second * 1000000 + cur_datetime.microsecond
	ping_glob = (cur_time - int(parsed[-1])) // 1000

def handle_state(event_string, player, enemy):
	state_type = event_string.split(';')[1]
	if state_type == 'enemy_left':
		out_queue_glob.put({'type': 'close_app'})
		sys.exit()

def handle_new_bullet(bullet_string, bullets_group, scene):
	bullets_group.add(Bullet(scene, 'Sprites/Bullet.png', int(bullet_string.split(';')[1]), bullet_string.split(';')[-1]))

def handle_hp(event, player, enemy):
	cur_health = int(event.split(';')[1])
	player.hp = cur_health
