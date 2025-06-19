import pygame
import pygame_gui
import sys 
from settings import *
from game_state_manager import GSM
from settings import *


class SettingsButton(pygame_gui.elements.UIButton):
    def __init__(self, manager):
        super().__init__(
            relative_rect=pygame.Rect((GSM.width * (7/16),0), (GSM.width//8, HEADER_HEIGHT-10)),
            text='Settings',
            manager=manager
        )
class CustomSlider(pygame_gui.elements.UIHorizontalSlider):
    def __init__(self,position, start_val, range, manager, container, object_id,textbox):
        super().__init__(
            relative_rect=pygame.Rect(position, (container.relative_rect.width // 2, TILESIZE)),
            start_value=start_val,
            value_range=range,
            manager=manager,
            container=container,
            object_id=object_id
        )
        self.textbox = textbox
    
    def update_text(self):
        self.textbox.set_text(str(self.get_current_value()))

class CustomSliderTextLine(pygame_gui.elements.UITextEntryLine):
    def __init__(self,position,manager, container, object_id):
        super().__init__(
            relative_rect=pygame.Rect(position, (container.relative_rect.width // 6, TILESIZE)),
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
    
    def set_slider(self,parent):
        self.parent = parent
    def update_value(self):
        new_val = int(self.get_text())
        if self.parent.value_range[0] <= new_val <= self.parent.value_range[1]:
            self.parent.set_current_value(int(self.get_text()))
        else:
            self.set_text(str(self.parent.value_range[0])) if new_val < self.parent.value_range[0] else self.set_text(str(self.parent.value_range[1]))
        

        
class HeaderPanel:
    def __init__(self, manager):
        self.manager = manager
        #self.screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
        #panel = pygame.Rect((SCREEN_WIDTH * (3/8), SCREEN_HEIGHT/ 4), (SCREEN_WIDTH // 4, SCREEN_HEIGHT// 2))
        panel = pygame.Rect((0,0), (GSM.width, HEADER_HEIGHT))

        self.settings_panel = pygame_gui.elements.UIPanel(
            relative_rect=panel,
            manager=self.manager,
            object_id='header_panel'
        )


class DifficultyButton(pygame_gui.elements.UIButton):
    def __init__(self, manager, position, text, object_id, container,settings):
        super().__init__(
            relative_rect=pygame.Rect(position, (SCREEN_WIDTH // 4, TILESIZE)),
            text=text,
            manager=manager,
            container=container,
            object_id=object_id
        )
        self.settings = settings #(h,w,m)
class SettingsMenu:
    def __init__(self, manager, parent):
        self.manager = manager
        self.parent = parent
        panel = pygame.Rect((0,0), (SCREEN_WIDTH // 4, SCREEN_HEIGHT))

        self.settings_panel = pygame_gui.elements.UIPanel(
            relative_rect=panel,
            manager=self.manager,
            object_id='settings_panel'
        )
        self.difficulty_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((panel.width // 4, 0), (panel.width // 2, TILESIZE)),
            text='Difficulty',
            manager=self.manager,
            container=self.settings_panel,
            object_id='difficulty_label'
        )
        self.easy_button = DifficultyButton(self.manager, (0, self.difficulty_label.relative_rect.bottom),'Easy (9x9, 10 mines)','easy_button',self.settings_panel,(9,9,10))
        self.intermediate_button = DifficultyButton(self.manager, (0, self.easy_button.relative_rect.bottom),'Intermediate (16x16, 40 mines)','intermediate_button',self.settings_panel,(16,16,40))
        self.expert_button = DifficultyButton(self.manager, (0, self.intermediate_button.relative_rect.bottom),'Expert (30x16, 99 mines)','expert_button',self.settings_panel,(16,30,99))
        self.custom_button = DifficultyButton(self.manager, (0, self.expert_button.relative_rect.bottom),'Custom','custom_button',self.settings_panel,(GSM.height/TILESIZE,GSM.width/TILESIZE,GSM.mine_count))

        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(pygame.Rect((panel.width // 4, panel.height-TILESIZE), (panel.width // 2, TILESIZE))),
            text='Back',
            manager=self.manager,
            container=self.settings_panel,
            object_id='back_button'
        )

        self.w_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((0, self.custom_button.relative_rect.bottom), (panel.width // 6, TILESIZE)),
            text='W: ',
            manager=self.manager,
            container=self.settings_panel,
            object_id='w_label'
        )
        self.w_text = CustomSliderTextLine((self.w_label.relative_rect.right, self.custom_button.relative_rect.bottom),self.manager,self.settings_panel,'w_text')
        w_pos = (self.w_label.relative_rect.right + panel.width // 6, self.custom_button.relative_rect.bottom)
        self.w_slider = CustomSlider(w_pos,GSM.rows,DIM_BOUNDARIES,self.manager,self.settings_panel,'w_slider',self.w_text)
        self.w_slider.update_text()
        self.w_text.set_slider(self.w_slider)


        self.h_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((0, self.w_text.relative_rect.bottom), (panel.width // 6, TILESIZE)),
            text='H: ',
            manager=self.manager,
            container=self.settings_panel,
            object_id='h_label'
        )
        self.h_text = CustomSliderTextLine((self.h_label.relative_rect.right, self.w_text.relative_rect.bottom),self.manager,self.settings_panel,'h_text')
        h_pos = (self.h_label.relative_rect.right + panel.width // 6, self.w_text.relative_rect.bottom)
        self.h_slider = CustomSlider(h_pos,GSM.cols,DIM_BOUNDARIES,self.manager,self.settings_panel,'h_slider',self.h_text)
        self.h_slider.update_text()
        self.h_text.set_slider(self.h_slider)

        self.m_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((0, self.h_text.relative_rect.bottom), (panel.width // 6, TILESIZE)),
            text='M: ',
            manager=self.manager,
            container=self.settings_panel,
            object_id='m_label'
        )
        self.m_text = CustomSliderTextLine((self.m_label.relative_rect.right, self.h_text.relative_rect.bottom),self.manager,self.settings_panel,'m_text')
        m_pos = (self.h_label.relative_rect.right + panel.width // 6, self.h_text.relative_rect.bottom)
        self.m_slider = CustomSlider(m_pos,GSM.mine_count,(1, GSM.rows*GSM.cols),self.manager,self.settings_panel,'m_slider',self.m_text)
        self.m_slider.update_text()
        self.m_text.set_slider(self.m_slider)
        self.back_button.relative_rect.bottom = self.settings_panel.relative_rect.bottom
        

        self.settings_panel.hide()

    def show(self):
        self.settings_panel.show()

    def hide(self):
        self.settings_panel.hide()
    def get(self):
        return self.settings_panel

        
         


