import queue
import pygame, sys
import os
import datetime
import pygame_gui

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
		self.cur_image = self.idle
		self.rect = self.cur_image.get_rect()
		self.rect.center = [0, 0]

		self.bullets_group: pygame.sprite.Group = bullets_group

		self.image_reset_timer = 0

	def show_anim(self, sprite):
		self.cur_image = sprite
		self.image_reset_timer = pygame.time.get_ticks()

	@property
	def hp(self):
		return self.__hp

	@hp.setter
	def hp(self, value):
		self.__hp = value
		if self.hp <= 0:
			self.show_anim(self.explosion)
		else:
			self.show_anim(self.wounded)

	def set_pos(self, pos):
		if self.hp > 0:
			self.rect.center = pos

	def update(self):
		a = pygame.time.get_ticks()
		if self.image_reset_timer and a - self.image_reset_timer >= 180:
			if self.cur_image != self.explosion:
				self.cur_image = self.idle
				self.image_reset_timer = 0
		self.parent.blit(self.cur_image, self.rect)


class Game:

	def __init__(self, in_queue, out_queue):
		self.out_queue = out_queue
		self.in_queue = in_queue
		pygame.init()
		self.SCENE = pygame.display.set_mode((1500, 1000))
		self.UI_MANAGER = pygame_gui.UIManager((1500, 1000), 'Themes/General.json')
		self.FPS = 50
		self.clock = pygame.time.Clock()
		self.FILL_COLOR = (53, 24, 92)
		self.ships_group = pygame.sprite.Group()
		self.bullets_group = pygame.sprite.Group()

		self.out_queue.put({'type': 'enter_game'})

	def ui_thread_inst(self):
		while True:
			try:
				game_start_trigger = self.in_queue.get_nowait()
				if game_start_trigger == 'game_entered':
					break
			except queue.Empty:
				self.SCENE.fill(self.FILL_COLOR)
				pygame.display.update()
				self.clock.tick(self.FPS)

		print('Game started')
		server_events_toolkit = {'positions': self.battle_place_ships,
								 'state': self.battle_handle_state,
								 'new_bullet': self.battle_handle_new_bullet,
								 'hp': self.battle_handle_hp}
		image_files = [os.path.join('Sprites', i) for i in ('BlueShipIdle.png', 'BlueShipWounded.png', 'Explosion.png',
														   'RedShipIdle.png', 'RedShipWounded.png', 'Explosion.png')]
		self.player = Spaceship(self.SCENE, *image_files[:3], self.bullets_group)
		self.player.set_pos((500, 935))
		player_is_moving = False
		self.enemy = Spaceship(self.SCENE, *image_files[3:], self.bullets_group)
		self.enemy.set_pos((1000, 65))
		self.ships_group.add(self.player)
		self.ships_group.add(self.enemy)

		ping_label = pygame_gui.elements.UILabel(pygame.Rect((1380, 90, 90, 50)), 'Ping: ', self.UI_MANAGER)
		while True:
			# TODO: Сделать просмотр очереди событий, создание игровых объектов, реакцию на действия пользователя, добавление событий
			#  в очередь на отправку.
			#  Пули обновляются после кораблей.
			self.SCENE.fill(self.FILL_COLOR)
			try:
				server_event = self.in_queue.get_nowait()
				server_events_toolkit[server_event.split(';')[0]](server_event)
			except queue.Empty:
				pass

			inner_events = pygame.event.get()
			for i in inner_events:
				if i.type == pygame.QUIT:
					self.out_queue.put({'type': 'close_app'})
					sys.exit()
				elif i.type == pygame.KEYDOWN:
					if i.key in (pygame.K_RIGHT, pygame.K_LEFT):
						if not player_is_moving:
							player_is_moving = True
							if i.key == pygame.K_RIGHT:
								self.out_queue.put({'type': 'move', 'dir': 'r'})
							elif i.key == pygame.K_LEFT:
								self.out_queue.put({'type': 'move', 'dir': 'l'})
				elif i.type == pygame.KEYUP:
					if i.key in (pygame.K_RIGHT, pygame.K_LEFT):
						self.out_queue.put({'type': 'stop'})
						player_is_moving = False
					elif i.key == pygame.K_SPACE:
						self.out_queue.put({'type': 'shoot'})
				self.UI_MANAGER.process_events(i)
			self.bullets_group.update()
			self.ships_group.update()
			ping_label.set_text(f'Ping: {ping_glob}')
			self.UI_MANAGER.update(self.clock.tick(self.FPS))
			self.UI_MANAGER.draw_ui(self.SCENE)
			pygame.display.update()

	def battle_place_ships(self, event_string):
		global ping_glob
		parsed = event_string.split(';')[1:]
		player_x = int(parsed[0].split(':')[1])
		enemy_x = 1500 - int(parsed[1].split(':')[1])
		self.player.set_pos((player_x, 935))
		self.enemy.set_pos((enemy_x, 65))

		cur_datetime = datetime.datetime.utcnow()
		cur_time = cur_datetime.second * 1000000 + cur_datetime.microsecond
		ping_glob = (cur_time - int(parsed[-1])) // 1000

	def battle_handle_state(self, event_string):
		state_type = event_string.split(';')[1]
		if state_type == 'enemy_left':
			self.out_queue.put({'type': 'close_app'})
			sys.exit()

	def battle_handle_new_bullet(self, bullet_string):
		self.bullets_group.add(Bullet(self.SCENE, 'Sprites/Bullet.png', int(bullet_string.split(';')[1]), bullet_string.split(';')[-1]))

	def battle_handle_hp(self, event):
		player_new_hp = int(event.split(';')[1])
		if player_new_hp < self.player.hp:
			self.player.hp = player_new_hp
		enemy_new_hp = int(event.split(';')[2])
		if enemy_new_hp < self.enemy.hp:
			self.enemy.hp = enemy_new_hp
