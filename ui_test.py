### main.py
from settings import *
from sprites import *
import time
import pygame_gui
import sys
from game_state_manager import GSM
import UI
from screen_manager import ScreenManager

pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 50)
ui_manager = pygame_gui.UIManager((WIDTH, HEIGHT))
screen_manager = ScreenManager()
main_screen = None

def format_time(seconds):
    seconds = int(seconds)
    if seconds > 999:
        seconds = 999
    return f"{seconds:03}"

### managers/screen_manager.py
class ScreenManager:
    def __init__(self):
        self.current_screen = None

    def set_screen(self, screen):
        self.current_screen = screen

    def handle_events(self, events):
        if self.current_screen:
            self.current_screen.handle_events(events)

    def update(self, time_delta):
        if self.current_screen:
            self.current_screen.update(time_delta)

    def render(self, surface):
        if self.current_screen:
            self.current_screen.render(surface)


### screens/menu_screen.py
import pygame
import pygame_gui

class MenuScreen:
    def __init__(self, manager, screen_size, switch_callback):
        self.ui_manager = manager
        self.screen_size = screen_size
        self.switch_callback = switch_callback
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT+HEADER_HEIGHT))
        pygame.display.set_caption('Minesweeper')
        self.board = Board()
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(NUM_MINES)
        self.settings_button = UI.SettingsButton(
                manager=ui_manager,
                position=(WIDTH / 2-100 , 0)
            ).get()
        self.settings_menu = UI.SettingsMenu(ui_manager, (WIDTH, HEIGHT), {'volume': 50})
        





        #self.board.display_board()
    
    def run(self):
        running = True
  
        # game loop 
        while running: 
            
        # for loop through the event queue   
            #clock.tick(60)
            time_delta = clock.tick(60) / 1000.0
            self.events()
            self.render()
            if self.board.is_complete():
                self.board.reveal_board()
            ui_manager.update(time_delta)
            ui_manager.draw_ui(self.screen)
            pygame.display.update()

    def reset(self):
            self.board = Board()
            self.first_click = True
            self.time_text=DEFAULT_TIME
            GSM.set_game_state(True)
    def render(self,surface):
        self.screen.fill((255,255,255))
        self.board.draw(self.screen)
        if GSM.get_game_state() and not self.first_click:
            elapsed_time = time.time()-self.start_time
            self.time_text = format_time(elapsed_time)
        time_surface = font.render(self.time_text, True, (0,0,0))
        time_rect = time_surface.get_rect(topright=(WIDTH,0))
        self.screen.blit(time_surface, time_rect)

        self.flag_text = str(NUM_MINES - self.board.get_flag_count())
        flag_surface = font.render(self.flag_text, True, (0,0,0))
        flag_rect = flag_surface.get_rect()
        self.screen.blit(flag_surface, flag_rect)

        ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def update(self, time_delta):
        self.ui_manager.update(time_delta)

    def handle_events(self,events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                quit(0)
            ui_manager.process_events(event)

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.settings_button:
                    GSM.set_game_state(False)
                    self.settings_button.hide()
                    self.settings_menu.show()
                elif event.ui_object_id == 'back_button':
                    self.settings_menu.hide()
                    self.settings_button.show()
                    GSM.set_game_state(True)
            ui_manager.draw_ui(self.screen)

            if event.type == pygame.MOUSEBUTTONUP:
                if ui_manager.get_focus_set():
                    continue

                if GSM.get_game_state():
                    mx, my = pygame.mouse.get_pos() 
                    my -= HEADER_HEIGHT
                    mx //= TILESIZE
                    my //= TILESIZE



                    if event.button == 1:
                        if self.first_click:
                            self.board.populate([mx,my])
                            self.first_click = False
                            self.start_time = time.time()
                        if self.board.tiles[mx][my].is_revealed():
                            self.board.chord([mx,my])
                        self.board.reveal_tiles(mx,my)
                    
                    elif event.button == 3:
                        if not self.first_click:
                            self.board.toggle_flag_at_loc(mx,my)
                

                

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if not self.first_click:
                        self.board.reveal_board()
                if event.key == pygame.K_n:
                    self.reset()

                if event.key == pygame.K_l:
                    print(1)
                    print(self.first_click)
                    print(2)
                    print(GSM.get_game_state())


### screens/settings_screen.py
import pygame
import pygame_gui

class SettingsScreen:
    def __init__(self, manager, screen_size, switch_callback):
        self.ui_manager = manager
        self.screen_size = screen_size
        self.switch_callback = switch_callback

        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((screen_size[0] // 2 - 100, 400), (200, 50)),
            text='Back',
            manager=self.ui_manager,
            object_id='back_button'
        )

    def handle_events(self, events):
        for event in events:
            self.ui_manager.process_events(event)
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.back_button:
                    self.switch_callback("menu")

    def update(self, time_delta):
        self.ui_manager.update(time_delta)

    def render(self, surface):
        surface.fill((0, 0, 0))
        self.ui_manager.draw_ui(surface)




pygame.init()

SCREEN_SIZE = (800, 600)
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("Screen Navigation Example")
clock = pygame.time.Clock()

ui_manager = pygame_gui.UIManager(SCREEN_SIZE)
screen_manager = ScreenManager()

# Callback to switch screens
def switch_screen(screen_name):
    ui_manager.clear_and_reset()
    if screen_name == "menu":
        screen_manager.set_screen(MenuScreen(ui_manager, SCREEN_SIZE, switch_screen))
    elif screen_name == "settings":
        screen_manager.set_screen(SettingsScreen(ui_manager, SCREEN_SIZE, switch_screen))

# Set the root screen to be the main menu
screen_manager.set_screen(MenuScreen(ui_manager, SCREEN_SIZE, switch_screen))

running = True
while running:
    time_delta = clock.tick(60) / 1000.0
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False


    screen_manager.handle_events(events)
    screen_manager.update(time_delta)

    screen.fill((0, 0, 0))
    screen_manager.render(screen)
    pygame.display.update()

pygame.quit()
