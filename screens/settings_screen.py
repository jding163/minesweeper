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
        surface.fill((50, 50, 50))
        self.ui_manager.draw_ui(surface)