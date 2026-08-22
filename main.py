from settings import *
from sprites import *
import time
import sys
import pygame_gui
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
    def __init__(self, board):
        self.board = board
        self._init_display()
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)
        self.win_text = 'You win!'
        self.game_over = False
        self.replay_mode = False
        self.replay_index = 0
        self.replay_log = []
        self.replay_start = 0
        self.replay_saved = False
        self.scrubbing_replay = False
        self.replay_paused = True
        self.replay_paused_time = 0
        self.replay_time = 0

    def _init_display(self):
        # Fixed window sized for the largest supported board.
        # screen_info = pygame.display.Info()
        # screen_w = screen_info.current_w
        # screen_h = screen_info.current_h
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Minesweeper')
        self.ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))

        self.left_panel = UI.LeftPanel(self.ui_manager, self.screen, self)
        self.middle_panel = UI.MiddlePanel(self.board, self.ui_manager, self.screen, self)
        self.right_panel = UI.RightPanel(self.ui_manager, self.screen, self)

    def refresh_panels(self):
        """Update panel contents after the board changes without resizing the window."""
        self.middle_panel.set_board(self.board)

    def reset_replay_info(self):
        self.replay_index = 0
        self.replay_log = []
        self.replay_start = 0
        self.replay_time = 0

    def render_replay(self, time_delta):
        self.first_click = False
        GSM.set_game_state(False)
        if self.replay_index == 0:
            self.middle_panel.replay_slider.update_range(
                (0, (rm.replay_dur + 0.02) * UI.ReplaySlider.slider_scale)
            )

        if not self.replay_paused:
            self.replay_time += time_delta

        while (self.replay_index < len(self.replay_log) and
               self.replay_log[self.replay_index]['time'] <= self.replay_time):
            C.process_replay_event(self.replay_log[self.replay_index])
            self.replay_index += 1

        self.time_text = format_time(self.replay_time)
        self.middle_panel.replay_slider.set_current_value(
            self.replay_time * UI.ReplaySlider.slider_scale
        )
        self.middle_panel.time_text = self.time_text

        if self.replay_index >= len(self.replay_log):
            self.replay_paused = True

    def seek_replay(self, target):
        C.load_replay_board()
        self.replay_index = 0
        self.replay_time = 0
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
        while running:
            time_delta = clock.tick(60) / 1000.0

            self.events()
            if self.replay_mode:
                self.middle_panel.show_replay_controls()
                self.render_replay(time_delta)
                self.replay_saved = True
            else:
                self.middle_panel.hide_replay_controls()
                game_over = self.check_if_game_over()
                if game_over:
                    self.check_if_game_won()
                    if not self.replay_saved:
                        C.save_replay()
                        self.replay_saved = True
                self.game_over = game_over
                if GSM.get_game_state() == GSM.running and not self.first_click:
                    self.elapsed_time = time.time() - self.start_time
                    self.time_text = format_time(self.elapsed_time)
                    self.middle_panel.time_text = self.time_text

            self.draw()

            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.update()

    def reset(self):
        GSM.set_game_state(GSM.fresh)
        self.first_click = True
        self.start_time = 0
        self.elapsed_time = 0
        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)
        self.middle_panel.time_text = self.time_text
        self.replay_saved = False
        self.replay_paused_time = 0
        self.replay_mode = False
        self.reset_replay_info()
        self.middle_panel.hide_replay_controls()

    def draw(self):
        self.screen.fill((255, 255, 255))
        self.left_panel.draw(self.screen)
        self.middle_panel.draw(self.screen)
        self.right_panel.draw(self.screen)

        if self.check_if_game_won() and not self.replay_mode:
            win_surface = UI.ui_font.render(self.win_text, True, BLACK)
            win_rect = win_surface.get_rect(
                center=(LEFT_PANEL_WIDTH + MAX_BOARD_WIDTH // 2, HEADER_HEIGHT + MAX_BOARD_HEIGHT // 2)
            )
            self.screen.blit(win_surface, win_rect)

        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit(0)

            self.ui_manager.process_events(event)

            if self.left_panel.handle_event(event):
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    self.ui_manager.set_focus_set(None)
                continue
            if self.middle_panel.handle_event(event):
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    self.ui_manager.set_focus_set(None)
                continue
            if self.right_panel.handle_event(event):
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    self.ui_manager.set_focus_set(None)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.ui_manager.get_focus_set():
                    continue

                mx = event.pos[0] - LEFT_PANEL_WIDTH + self.middle_panel.scroll_x
                my = event.pos[1] - HEADER_HEIGHT + self.middle_panel.scroll_y
                mx //= TILESIZE
                my //= TILESIZE
                # mx/my here are (column, row); controller expects (row, column)
                mx, my = my, mx
                C.update_mouse_pos(mx, my)

                if not C.mouse_pos_in_bounds():
                    continue

                if event.button == 1:
                    # C.handle_board_click()
                    C.handle_board_click(seed=0)
                elif event.button == 3:
                    C.handle_board_right_click()

            elif event.type == pygame.MOUSEBUTTONUP:
                if self.scrubbing_replay:
                    self.scrubbing_replay = False

            elif event.type == pygame.MOUSEWHEEL:
                self.scroll_board(event.x * TILESIZE, event.y * TILESIZE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    C.handle_keypress_r()
                elif event.key == pygame.K_n:
                    self.new_game()
                elif event.key == pygame.K_m:
                    C.handle_keypress_m()
                elif event.key == pygame.K_q:
                    C.handle_keypress_q()
                elif event.key == pygame.K_w:
                    self.solve_step()
                elif event.key == pygame.K_e:
                    self.suggestion()
                elif event.key == pygame.K_t:
                    self.autoplay()
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
                    self.toggle_probs()
                elif event.key == pygame.K_o:
                    C.handle_keypress_o()
                elif event.key == pygame.K_p:
                    C.handle_keypress_p()
                elif event.key == pygame.K_l:
                    self.load_board()
                elif event.key == pygame.K_b:
                    self.run_sim()
                elif event.key == pygame.K_v:
                    C.handle_keypress_v()
                elif event.key == pygame.K_x:
                    C.handle_keypress_x()
                elif event.key == pygame.K_z:
                    C.handle_keypress_z()
                elif event.key == pygame.K_c:
                    C.handle_keypress_c(8395227948706629321)
                elif event.key == pygame.K_k:
                    self.save_board()
                elif event.key == pygame.K_SPACE:
                    C.handle_keypress_space()

    # --- Panel callbacks -------------------------------------------------

    def set_difficulty(self, settings):
        GSM.set_board(settings)
        self.reset()
        C.reset_board()
        self.board = C.board
        self.refresh_panels()

    def apply_custom(self):
        # W controls board width (columns), H controls board height (rows).
        custom_settings = (
            int(self.left_panel.h_slider.get_current_value()),
            int(self.left_panel.w_slider.get_current_value()),
            int(self.left_panel.m_slider.get_current_value())
        )
        self.set_difficulty(custom_settings)

    def toggle_replay_pause(self):
        C.handle_pause_button()

    def solve_step(self):
        C.handle_keypress_w()

    def suggestion(self):
        C.handle_keypress_e()

    def autoplay(self):
        C.handle_keypress_t()

    def toggle_probs(self):
        BoardUI.display_probs += 1
        BoardUI.display_probs %= 2

    def run_sim(self):
        C.run_move_sim(self.board, num_samples)

    def new_game(self):
        C.handle_keypress_n()
        self.board = C.board
        self.refresh_panels()

    def save_board(self):
        C.handle_keypress_k()

    def load_board(self):
        C.handle_keypress_l()
        self.board = C.board
        self.first_click = False
        self.refresh_panels()

    def reveal_all(self):
        C.handle_keypress_r()

    def scroll_board(self, dx, dy):
        self.middle_panel.scroll(dx, dy)


def main():
    TileUI.font = tile_font
    p_executor = ThreadPoolExecutor(max_workers=3)
    Player.set_executor(p_executor)

    b = Solver()
    p = Player()
    C.set_player(p)
    C.set_board(b)

    g = Game(b)
    C.set_game(g)

    g.draw()
    g.run()


if __name__ == "__main__":
    main()
