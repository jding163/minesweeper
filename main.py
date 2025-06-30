from settings import *
from sprites import *
import time
import pygame_gui
import sys
from game_state_manager import GSM
import UI
import controller as C
from player import Player
import solver
from solver import Solver
import solver_test
import multiprocessing


pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 50)
tile_font = pygame.font.Font(None, 12)  



def format_time(seconds):
    seconds = int(seconds)
    if seconds > 999:
        seconds = 999
    return f"{seconds:03}"





class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT+HEADER_HEIGHT))
        #self.screen = pygame.display.set_mode((1000,1000))

        pygame.display.set_caption('Minesweeper')
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)
        self.ui_manager = pygame_gui.UIManager(SCREEN_DIMS)
        #self.header_panel = UI.HeaderPanel(self.ui_manager)

        self.settings_button = UI.SettingsButton(
                manager=self.ui_manager,
        )
        self.settings_menu = UI.SettingsMenu(self.ui_manager, self.screen)
        self.win_text = 'You win!'




    
    def check_if_game_won(self):
        return C.game_won()

    def run(self):
        running = True
  
        # game loop 
        while running: 
            
        # for loop through the event queue   
            #clock.tick(60)
            time_delta = clock.tick(60) / 1000.0
            self.events()
            self.draw()
            self.check_if_game_won()


            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()

    def reset(self):
        GSM.set_game_state(True)
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)
        self.settings_menu.hide()
    def resize(self):
        self.screen = pygame.display.set_mode((GSM.width,GSM.height+HEADER_HEIGHT))
        self.ui_manager = pygame_gui.UIManager((GSM.width,GSM.height))
        self.settings_button = UI.SettingsButton(
                manager=self.ui_manager,
        )
        self.settings_menu = UI.SettingsMenu(self.ui_manager, self.screen)
    def draw(self):
        self.screen.fill((255,255,255))
        C.draw_board(self.screen)
        if GSM.get_game_state() and not self.first_click:
            self.elapsed_time = time.time()-self.start_time
            self.time_text = format_time(self.elapsed_time)
        time_surface = font.render(self.time_text, True, BLACK)
        time_rect = time_surface.get_rect(topright=(GSM.width,0))
        self.screen.blit(time_surface, time_rect)

        self.flag_text = str(GSM.mine_count - C.get_flag_count())
        flag_surface = font.render(self.flag_text, True, BLACK)
        flag_rect = flag_surface.get_rect()
        self.screen.blit(flag_surface, flag_rect)


        if self.check_if_game_won():
            win_surface = font.render(self.win_text, True, BLACK)
            win_rect = win_surface.get_rect(center=(GSM.width//2,GSM.height//2))
            self.screen.blit(win_surface, win_rect)

        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit(0)
            self.ui_manager.process_events(event)
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.settings_button:
                    C.handle_settings_button()
                elif event.ui_element == self.settings_menu.back_button:
                    C.handle_settings_back_button()
                elif event.ui_element == self.settings_menu.easy_button:
                    C.handle_easy_button()
                elif event.ui_element == self.settings_menu.intermediate_button:
                    C.handle_intermediate_button()
                elif event.ui_element == self.settings_menu.expert_button:
                    C.handle_expert_button()
                elif event.ui_element == self.settings_menu.custom_button:
                    C.handle_custom_button()

            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                C.handle_customization_sliders()
                C.update_minecount_slider()
            if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
                C.handle_customization_text(event)
            self.ui_manager.draw_ui(self.screen)


            mx, my = pygame.mouse.get_pos() 
            my -= HEADER_HEIGHT
            mx //= TILESIZE
            my //= TILESIZE
            C.update_mouse_pos(mx,my)
            if event.type == pygame.MOUSEBUTTONDOWN:

                if self.ui_manager.get_focus_set():
                    continue

                if GSM.get_game_state():
                    if event.button == 1:
                        #C.handle_board_click(mines=custom_mines)
                        #test -8425763037098422648, -8433645031250545356,-3837008816949211577
                        #C.handle_board_click(seed=8261430605045743384)
                        #C.handle_board_click(seed=-3471843042740411231)

                        C.handle_board_click()
                    
                    elif event.button == 3:
                        C.handle_board_right_click()
                

                

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    C.handle_keypress_r()
                elif event.key == pygame.K_n:
                    C.handle_keypress_n()
                elif event.key == pygame.K_m:
                    C.handle_keypress_m()
                elif event.key == pygame.K_q:
                    C.handle_keypress_q()

                elif event.key == pygame.K_w:
                    C.handle_keypress_w()
                #     prev = self.board.num_revealed
                #     self.board.chord_board()
                #     while self.board.num_revealed != prev:
                #         self.board.chord_board()
                #         prev = self.board.num_revealed

                elif event.key == pygame.K_e:
                    C.handle_keypress_e()
                elif event.key == pygame.K_t:
                    C.handle_keypress_t()

                    #C.handle_keypress_t()
                elif event.key == pygame.K_a:
                    C.handle_keypress_a()
                elif event.key == pygame.K_s:
                    C.handle_keypress_s()
                elif event.key == pygame.K_d:
                    C.handle_keypress_d()
                elif event.key == pygame.K_y:
                    C.handle_keypress_y()
                elif event.key == pygame.K_u:
                    C.handle_keypress_u()
                elif event.key == pygame.K_i:
                    Board.display_probs += 1
                    Board.display_probs %= 4
                elif event.key == pygame.K_o:
                    C.handle_keypress_o()
                elif event.key == pygame.K_p:
                    C.handle_keypress_p()
                elif event.key == pygame.K_l:
                    C.handle_keypress_l()
                elif event.key == pygame.K_b:
                    C.handle_keypress_b()
                elif event.key == pygame.K_k:
                    C.handle_keypress_k()
                    print(f'test: {C.test}')
                elif event.key == pygame.K_SPACE:
                    C.handle_keypress_space()
#b = merge_tester.SolverData()
def main():
    Tile.set_font(tile_font)

    b = solver_test.Solver()
    #b=Solver()
    p = Player()
    #p = merge_tester.Collector()
    C.set_player(p)
    C.set_board(b)
    g = Game()
    C.set_game(g)

    g.draw()
    g.run()

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # Important on macOS/Windows
    main()
