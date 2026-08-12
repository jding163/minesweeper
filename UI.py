import pygame
import pygame_gui
from settings import *
from game_state_manager import GSM
from sprites import BoardUI

pygame.init()
ui_font = pygame.font.SysFont(None, 50)



class CustomSlider(pygame_gui.elements.UIHorizontalSlider):
    def __init__(self, position, start_val, range, manager, container, object_id, textbox, size=None):
        if size is None:
            size = (container.relative_rect.width - 20, TILESIZE)
        super().__init__(
            relative_rect=pygame.Rect(position, size),
            start_value=start_val,
            value_range=range,
            manager=manager,
            container=container,
            object_id=object_id
        )
        self.textbox = textbox

    def update_text(self):
        self.textbox.set_text(str(int(self.get_current_value())))


class CustomSliderTextLine(pygame_gui.elements.UITextEntryLine):
    def __init__(self, position, manager, container, object_id):
        super().__init__(
            relative_rect=pygame.Rect(position, (container.relative_rect.width // 4, TILESIZE)),
            manager=manager,
            container=container,
            object_id=object_id
        )
        self.prev_text = ''

    def process_event(self, event):
        response = super().process_event(event)
        new_text = ''.join(c for c in self.text if c.isdigit())
        if new_text != self.text:
            self.set_text(new_text)
        return response

    def set_slider(self, parent):
        self.parent = parent

    def update_value(self):
        new_val = int(self.get_text())
        low, high = self.parent.value_range
        if low <= new_val <= high:
            self.parent.set_current_value(new_val)
        else:
            self.set_text(str(int(low))) if new_val < low else self.set_text(str(int(high)))


class DifficultyButton(pygame_gui.elements.UIButton):
    def __init__(self, manager, position, text, object_id, container, settings):
        super().__init__(
            relative_rect=pygame.Rect(position, (container.relative_rect.width - 20, TILESIZE)),
            text=text,
            manager=manager,
            container=container,
            object_id=object_id
        )
        self.settings = settings


class ReplaySlider(pygame_gui.elements.UIHorizontalSlider):
    slider_scale = 100

    def __init__(self, position, start_val, range, manager, container, object_id, size=None):
        if size is None:
            size = (container.get_width() - 20, TILESIZE)
        super().__init__(
            relative_rect=pygame.Rect(position, size),
            start_value=start_val,
            value_range=range,
            manager=manager,
            object_id=object_id
        )

    def update_range(self, new_range):
        self.value_range = new_range


class LeftPanel:
    """Left column: game settings and difficulty selection."""

    def __init__(self, manager, screen, game):
        self.manager = manager
        self.game = game
        self.height = screen.get_height()

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((0, 0), (LEFT_PANEL_WIDTH, self.height)),
            manager=self.manager,
            object_id='left_panel'
        )

        y = PANEL_PADDING
        self.title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (LEFT_PANEL_WIDTH - 2 * PANEL_PADDING, TILESIZE)),
            text='Settings',
            manager=self.manager,
            container=self.panel
        )
        y = self.title.relative_rect.bottom + PANEL_PADDING

        self.easy_button = DifficultyButton(
            self.manager, (PANEL_PADDING, y), 'Easy (9x9, 10)', 'easy_button',
            self.panel, EASY_SETTINGS
        )
        y = self.easy_button.relative_rect.bottom + 5
        self.intermediate_button = DifficultyButton(
            self.manager, (PANEL_PADDING, y), 'Intermediate (16x16, 40)', 'intermediate_button',
            self.panel, INTERMEDIATE_SETTINGS
        )
        y = self.intermediate_button.relative_rect.bottom + 5
        self.expert_button = DifficultyButton(
            self.manager, (PANEL_PADDING, y), 'Expert (30x16, 99)', 'expert_button',
            self.panel, EXPERT_SETTINGS
        )
        y = self.expert_button.relative_rect.bottom + 5
        self.custom_button = DifficultyButton(
            self.manager, (PANEL_PADDING, y), 'Custom', 'custom_button',
            self.panel, (GSM.rows, GSM.cols, GSM.mine_count)
        )
        y = self.custom_button.relative_rect.bottom + 20

        # Custom width
        self.w_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (20, TILESIZE)),
            text='W:',
            manager=self.manager,
            container=self.panel
        )
        self.w_text = CustomSliderTextLine(
            (self.w_label.relative_rect.right + 5, y),
            self.manager, self.panel, 'w_text'
        )
        self.w_slider = CustomSlider(
            (self.w_text.relative_rect.right + 5, y),
            GSM.rows, DIM_BOUNDARIES, self.manager, self.panel, 'w_slider', self.w_text,
            size=(LEFT_PANEL_WIDTH - self.w_text.relative_rect.right - 15, TILESIZE)
        )
        self.w_slider.update_text()
        self.w_text.set_slider(self.w_slider)
        y = self.w_slider.relative_rect.bottom + 5

        # Custom height
        self.h_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (20, TILESIZE)),
            text='H:',
            manager=self.manager,
            container=self.panel
        )
        self.h_text = CustomSliderTextLine(
            (self.h_label.relative_rect.right + 5, y),
            self.manager, self.panel, 'h_text'
        )
        self.h_slider = CustomSlider(
            (self.h_text.relative_rect.right + 5, y),
            GSM.cols, DIM_BOUNDARIES, self.manager, self.panel, 'h_slider', self.h_text,
            size=(LEFT_PANEL_WIDTH - self.h_text.relative_rect.right - 15, TILESIZE)
        )
        self.h_slider.update_text()
        self.h_text.set_slider(self.h_slider)
        y = self.h_slider.relative_rect.bottom + 5

        # Custom mines
        self.m_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (20, TILESIZE)),
            text='M:',
            manager=self.manager,
            container=self.panel
        )
        self.m_text = CustomSliderTextLine(
            (self.m_label.relative_rect.right + 5, y),
            self.manager, self.panel, 'm_text'
        )
        self.m_slider = CustomSlider(
            (self.m_text.relative_rect.right + 5, y),
            GSM.mine_count, (1, GSM.rows * GSM.cols), self.manager, self.panel, 'm_slider', self.m_text,
            size=(LEFT_PANEL_WIDTH - self.m_text.relative_rect.right - 15, TILESIZE)
        )
        self.m_slider.update_text()
        self.m_text.set_slider(self.m_slider)

    def update_mine_slider_range(self):
        new_max = int(self.w_slider.get_current_value() * self.h_slider.get_current_value())
        new_max = max(1, new_max)
        prev = int(self.m_slider.get_current_value())
        self.m_slider.value_range = (1, new_max)
        self.m_slider.set_current_value(prev if prev <= new_max else new_max)
        self.m_slider.update_text()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.easy_button:
                self.game.set_difficulty(EASY_SETTINGS)
                return True
            if event.ui_element == self.intermediate_button:
                self.game.set_difficulty(INTERMEDIATE_SETTINGS)
                return True
            if event.ui_element == self.expert_button:
                self.game.set_difficulty(EXPERT_SETTINGS)
                return True
            if event.ui_element == self.custom_button:
                self.game.apply_custom()
                return True

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element in (self.w_slider, self.h_slider, self.m_slider):
                event.ui_element.update_text()
                if event.ui_element in (self.w_slider, self.h_slider):
                    self.update_mine_slider_range()
                return True

        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element in (self.w_text, self.h_text, self.m_text):
                event.ui_element.update_value()
                if event.ui_element in (self.w_text, self.h_text):
                    self.update_mine_slider_range()
                return True

        return False

    def draw(self, screen):
        pass


class MiddlePanel:
    """Center column: board, timer, mine count, and replay controls."""

    def __init__(self, board, manager, screen, game):
        self.board = board
        self.manager = manager
        self.screen = screen
        self.game = game
        self.board_ui = BoardUI(board)

        self.time_text = DEFAULT_TIME
        self.flag_text = str(GSM.mine_count)

        self.scroll_x = 0
        self.scroll_y = 0
        self.recenter_scroll()

        # Replay controls sit near the bottom of the fixed board area.
        replay_x = LEFT_PANEL_WIDTH + PANEL_PADDING
        replay_y = HEADER_HEIGHT + MAX_BOARD_HEIGHT - 2 * TILESIZE - PANEL_PADDING
        self.replay_slider = ReplaySlider(
            (replay_x, replay_y), 0, (0, 1),
            self.manager, self.screen, 'replay_slider',
            size=(MAX_BOARD_WIDTH - 20, TILESIZE)
        )
        self.pause_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((replay_x, replay_y + TILESIZE + 5), (100, TILESIZE)),
            text='Play/Pause',
            manager=self.manager,
            object_id='pause_button'
        )
        self.hide_replay_controls()

    def set_board(self, board):
        self.board = board
        self.board_ui = BoardUI(board)
        self.recenter_scroll()

    def recenter_scroll(self):
        """Center smaller boards; start at top-left for boards larger than the viewport."""
        board_w = self.board.rows * TILESIZE
        board_h = self.board.cols * TILESIZE
        self.scroll_x = (board_w - BOARD_VIEWPORT_WIDTH) // 2 if board_w < BOARD_VIEWPORT_WIDTH else 0
        self.scroll_y = (board_h - BOARD_VIEWPORT_HEIGHT) // 2 if board_h < BOARD_VIEWPORT_HEIGHT else 0

    def can_scroll(self):
        return (self.board.rows * TILESIZE > BOARD_VIEWPORT_WIDTH or
                self.board.cols * TILESIZE > BOARD_VIEWPORT_HEIGHT)

    def scroll(self, dx, dy):
        if not self.can_scroll():
            return
        board_w = self.board.rows * TILESIZE
        board_h = self.board.cols * TILESIZE
        max_x = max(0, board_w - BOARD_VIEWPORT_WIDTH)
        max_y = max(0, board_h - BOARD_VIEWPORT_HEIGHT)
        self.scroll_x = max(0, min(max_x, self.scroll_x + dx))
        self.scroll_y = max(0, min(max_y, self.scroll_y + dy))

    def show_replay_controls(self):
        self.replay_slider.show()
        self.pause_button.show()

    def hide_replay_controls(self):
        self.replay_slider.hide()
        self.pause_button.hide()

    def draw(self, screen):
        self.board_ui.draw(screen, (self.scroll_x, self.scroll_y))

        # Timer in the middle panel header, locked to the right edge of the board area
        time_surface = ui_font.render(self.time_text, True, BLACK)
        time_rect = time_surface.get_rect(
            topright=(LEFT_PANEL_WIDTH + MAX_BOARD_WIDTH - PANEL_PADDING, 0)
        )
        screen.blit(time_surface, time_rect)

        # Mine counter, locked to the left edge of the middle panel header
        self.flag_text = str(GSM.mine_count - self.board.flag_count)
        flag_surface = ui_font.render(self.flag_text, True, BLACK)
        flag_rect = flag_surface.get_rect(topleft=(LEFT_PANEL_WIDTH + PANEL_PADDING, 0))
        screen.blit(flag_surface, flag_rect)

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.pause_button:
                self.game.toggle_replay_pause()
                return True
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_object_id == 'replay_slider':
                seconds = self.replay_slider.get_current_value() / ReplaySlider.slider_scale
                self.game.seek_replay(seconds)
                return True
        return False


class RightPanel:
    """Right column: analysis and helper actions."""

    def __init__(self, manager, screen, game):
        self.manager = manager
        self.game = game
        self.height = screen.get_height()

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(
                (LEFT_PANEL_WIDTH + MAX_BOARD_WIDTH, 0),
                (RIGHT_PANEL_WIDTH, self.height)
            ),
            manager=self.manager,
            object_id='right_panel'
        )

        y = PANEL_PADDING
        self.title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (RIGHT_PANEL_WIDTH - 2 * PANEL_PADDING, TILESIZE)),
            text='Analysis',
            manager=self.manager,
            container=self.panel
        )
        y = self.title.relative_rect.bottom + PANEL_PADDING

        def make_button(text, object_id):
            nonlocal y
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((PANEL_PADDING, y), (RIGHT_PANEL_WIDTH - 2 * PANEL_PADDING, TILESIZE)),
                text=text,
                manager=self.manager,
                container=self.panel,
                object_id=object_id
            )
            y = btn.relative_rect.bottom + 5
            return btn

        self.solve_button = make_button('Solve Step', 'solve_button')
        self.suggest_button = make_button('Suggestion', 'suggest_button')
        self.autoplay_button = make_button('Autoplay', 'autoplay_button')
        self.probs_button = make_button('Toggle Probs', 'probs_button')
        self.sim_button = make_button('Run Sim', 'sim_button')
        self.new_button = make_button('New Game', 'new_button')
        self.save_button = make_button('Save Board', 'save_button')
        self.load_button = make_button('Load Board', 'load_button')
        self.reveal_button = make_button('Reveal All', 'reveal_button')

        y += 15
        self.scroll_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (RIGHT_PANEL_WIDTH - 2 * PANEL_PADDING, TILESIZE)),
            text='Scroll',
            manager=self.manager,
            container=self.panel
        )
        y = self.scroll_label.relative_rect.bottom + 5

        btn_w = (RIGHT_PANEL_WIDTH - 2 * PANEL_PADDING - 10) // 2
        self.scroll_up_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((PANEL_PADDING + btn_w // 2 + 5, y), (btn_w, TILESIZE)),
            text='Up',
            manager=self.manager,
            container=self.panel,
            object_id='scroll_up_button'
        )
        y = self.scroll_up_button.relative_rect.bottom + 5
        self.scroll_left_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((PANEL_PADDING, y), (btn_w, TILESIZE)),
            text='Left',
            manager=self.manager,
            container=self.panel,
            object_id='scroll_left_button'
        )
        self.scroll_right_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((PANEL_PADDING + btn_w + 10, y), (btn_w, TILESIZE)),
            text='Right',
            manager=self.manager,
            container=self.panel,
            object_id='scroll_right_button'
        )
        y = self.scroll_left_button.relative_rect.bottom + 5
        self.scroll_down_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((PANEL_PADDING + btn_w // 2 + 5, y), (btn_w, TILESIZE)),
            text='Down',
            manager=self.manager,
            container=self.panel,
            object_id='scroll_down_button'
        )

    def handle_event(self, event):
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return False

        callbacks = {
            self.solve_button: self.game.solve_step,
            self.suggest_button: self.game.suggestion,
            self.autoplay_button: self.game.autoplay,
            self.probs_button: self.game.toggle_probs,
            self.sim_button: self.game.run_sim,
            self.new_button: self.game.new_game,
            self.save_button: self.game.save_board,
            self.load_button: self.game.load_board,
            self.reveal_button: self.game.reveal_all,
            self.scroll_up_button: lambda: self.game.scroll_board(0, -TILESIZE),
            self.scroll_down_button: lambda: self.game.scroll_board(0, TILESIZE),
            self.scroll_left_button: lambda: self.game.scroll_board(-TILESIZE, 0),
            self.scroll_right_button: lambda: self.game.scroll_board(TILESIZE, 0),
        }

        cb = callbacks.get(event.ui_element)
        if cb is not None:
            cb()
            return True
        return False

    def draw(self, screen):
        pass
