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
import multiprocessing
from replay_manager import ReplayManager as rm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import asyncio
import multiprocessing
import threading

import copy

pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 50)
tile_font = pygame.font.Font(None, 12)  
num_samples = 200


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
        self.replay_slider = UI.ReplaySlider((self.screen.width * 3/4, self.screen.height - 3*TILESIZE),0,(0,1),self.ui_manager,self.screen,'replay_slider')
        self.pause_button = pygame_gui.elements.UIButton(relative_rect=(self.screen.width * 3/4, self.screen.height - 6*TILESIZE),text='Play/Pause',manager=self.ui_manager,object_id='pause_button')

        # print(self.screen.height)
        # print(self.replay_slider.relative_rect.y)
        self.win_text = 'You win!'
        self.game_over = False
        self.replay_mode = False
        self.replay_index = 0
        self.replay_log = []
        self.replay_start = 0
        self.replay_saved = False
        self.scrubbing_replay = False
        self.replay_paused = False
        self.replay_paused_time = 0



    def reset_replay_info(self):
        self.replay_index = 0
        self.replay_log = []
        self.replay_start = 0      

    def render_replay(self):
        self.first_click=False
        GSM.set_game_state(False)
        if self.replay_index == 0:
            self.replay_slider.update_range((0,(rm.replay_dur+0.02) * UI.ReplaySlider.slider_scale))

        if self.replay_paused:
            return

        elif self.replay_index < len(self.replay_log):
            elapsed = time.time() - self.replay_start
            replay_event = self.replay_log[self.replay_index]
            # print(self.replay_index)
            # print(len(self.replay_log))

            if elapsed >= replay_event['time']:
                C.process_replay_event(replay_event)
                self.replay_index += 1
                print(replay_event)
            self.elapsed_time = time.time()-self.replay_start
            self.time_text = format_time(self.elapsed_time)
            self.replay_slider.set_current_value(elapsed * UI.ReplaySlider.slider_scale)
            print(self.replay_slider.current_value)


        else:
            self.replay_mode = False
            #self.reset_replay_info()
            print('Replay complete')
            print(self.replay_slider.value_range)

    def seek_replay(self,target):
        C.load_replay_board()
        self.replay_index = 0
        for event in self.replay_log:
            if event['time'] <= target:
                self.replay_index += 1
                C.process_replay_event(event)
            else:
                break


    def check_if_game_won(self):
        return C.game_won()
    
    def check_if_game_over(self):
        return C.game_over()
    
    def run(self):
        running = True
  
        # game loop 
        while running: 

        # for loop through the event queue   
            #clock.tick(60)
            time_delta = clock.tick(60) / 1000.0


            self.events()
            if self.replay_mode:
                self.render_replay()
            self.draw()
            game_over = self.check_if_game_over()
            if game_over:
                self.check_if_game_won()
                if not self.replay_saved:
                    C.save_replay()
                    self.replay_saved = True
            self.game_over = game_over


            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()
            if C.future is not None:
                result = C.future.result()
                print(result)
                # for k,v in result.items():
                #     print(f'{k}: {v/num_samples}')

                C.future = None
                
    def reset(self):
        GSM.set_game_state(True)
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)
        self.settings_menu.hide()
        self.replay_saved = False
    # def resize(self):
    #     return
    #     self.screen = pygame.display.set_mode((GSM.width,GSM.height+HEADER_HEIGHT))
    #     self.ui_manager = pygame_gui.UIManager((GSM.width,GSM.height))
    #     self.settings_button = UI.SettingsButton(
    #             manager=self.ui_manager
    #     )
    #     self.settings_menu = UI.SettingsMenu(self.ui_manager, self.screen)
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
                elif event.ui_element == self.pause_button:
                    C.handle_pause_button()

            elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_object_id == 'replay_slider':
                    self.scrubbing_replay = True

                    self.seek_replay(self.replay_slider.get_current_value()/UI.ReplaySlider.slider_scale)
                else:
                    C.handle_customization_sliders(event)
                    C.update_minecount_slider()
            elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
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
                        #C.handle_board_click(seed=-1443323327528190823)

                        #C.handle_board_click(seed=-1569694061328666230)
                        #C.handle_board_click(seed=3180935053634563155)
                        #C.handle_board_click(seed=569029668483675204)
                        #C.handle_board_click(seed=4426209640626608113)

                        C.handle_board_click()
                    
                    elif event.button == 3:
                        C.handle_board_right_click()
                
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.scrubbing_replay:
                    self.scrubbing_replay = False

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
                    C.handle_keypress_t(timeout=60)

                    #C.handle_keypress_t()
                elif event.key == pygame.K_a:
                    C.handle_keypress_a()
                elif event.key == pygame.K_s:
                    C.handle_keypress_s()
                elif event.key == pygame.K_d:
                    C.handle_keypress_d()
                elif event.key == pygame.K_f:
                    C.handle_keypress_f()
                elif event.key == pygame.K_y:
                    C.handle_keypress_y()
                elif event.key == pygame.K_u:
                    C.handle_keypress_u()
                elif event.key == pygame.K_i:
                    BoardUI.display_probs += 1
                    BoardUI.display_probs %= 4
                elif event.key == pygame.K_o:
                    C.handle_keypress_o()
                elif event.key == pygame.K_p:
                    C.handle_keypress_p()
                elif event.key == pygame.K_l:
                    C.handle_keypress_l(filename='replay.npz')
                elif event.key == pygame.K_b:
                    # if self.future is None:
                    #future = self.executor.submit(C.handle_keypress_b,self.board,num_samples)
                    #board_copy = copy.deepcopy(self.board)
                    #t=threading.Thread(target=C.task)
                    t = threading.Thread(target=C.run_move_sim,args=(self.board,num_samples))
                    t.start()
                    #C.task_submit()
                    #future = C.handle_keypress_b(num_samples)
                    #self.future = future
                    # print(wins)
                    #self.future = future

                    # self.future = future
                    #p = multiprocessing.Process(target=C.handle_keypress_b,args=(num_samples,))
                    # p = threading.Thread(target=C.handle_keypress_b,args=(num_samples,))

                    # p.start()
                    #p.join()
                    # wins = self.executor.submit(C.handle_keypress_b(num_samples))
                    # print(wins)
                    # result = future.result()
                    # for k,v in result:
                    #     print(f'{k}: {v/num_samples}')
                    #t.join()
                elif event.key == pygame.K_v:
                    C.handle_keypress_v()
                elif event.key == pygame.K_x:
                    C.handle_keypress_x()
                elif event.key == pygame.K_z:
                    C.handle_keypress_z()
                elif event.key == pygame.K_c:
                    C.handle_keypress_c(8395227948706629321)
                elif event.key == pygame.K_k:
                    C.handle_keypress_k()
                elif event.key == pygame.K_SPACE:
                    C.handle_keypress_space()

def main():
    TileUI.font = tile_font
    #executor = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count() - 2)
    #p_executor = ThreadPoolExecutor(max_workers=6)
    p_executor = ProcessPoolExecutor(max_workers=6)

    Player.set_executor(p_executor)
    b=Solver()
    p = Player()
    C.set_player(p)
    C.set_board(b)
    C.set_executor(p_executor)
    g = Game()
    C.set_game(g)
    g.draw()
    g.run()
    #t_executor.submit(g.run())

if __name__ == "__main__":
    #multiprocessing.set_start_method("spawn") 
    #asyncio.run(main())
    main()

