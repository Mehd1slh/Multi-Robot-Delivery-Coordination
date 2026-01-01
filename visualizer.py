import pygame
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.model import WarehouseModel
# import agents just safety, we will use string checks for drawing
from src.agents import RobotAgent, ShelfAgent, PackingStationAgent, ChargingStationAgent

# CONFIGURATION 
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900 
SIDEBAR_WIDTH = 300
FPS = 60

# Colors
COLOR_BG = (255, 255, 255)
COLOR_GRID = (230, 230, 230)
COLOR_SIDEBAR = (40, 44, 52)
COLOR_BUTTON = (70, 130, 180)
COLOR_BUTTON_HOVER = (100, 149, 237)
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_SLIDER_BG = (100, 100, 100)
COLOR_SLIDER_HANDLE = (200, 200, 200)

# UI COMPONENTS

class Button:
    def __init__(self, x, y, width, height, text, callback, param=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.param = param
        self.is_hovered = False

    def draw(self, screen, font):
        color = COLOR_BUTTON_HOVER if self.is_hovered else COLOR_BUTTON
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        text_surf = font.render(self.text, True, COLOR_TEXT_WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                if self.param: self.callback(self.param)
                else: self.callback()

class Slider:
    def __init__(self, x, y, width, min_val, max_val, initial, label):
        self.rect = pygame.Rect(x, y, width, 20)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.label = label
        self.dragging = False
        
    def draw(self, screen, font):
        # Draw Label
        label_surf = font.render(f"{self.label}: {self.value}", True, COLOR_TEXT_WHITE)
        screen.blit(label_surf, (self.rect.x, self.rect.y - 25))
        
        # Draw Bar
        pygame.draw.rect(screen, COLOR_SLIDER_BG, self.rect, border_radius=5)
        
        # Draw Handle
        handle_x = self.rect.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
        handle_rect = pygame.Rect(handle_x - 10, self.rect.y - 5, 20, 30)
        pygame.draw.rect(screen, COLOR_SLIDER_HANDLE, handle_rect, border_radius=5)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            handle_x = self.rect.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
            handle_rect = pygame.Rect(handle_x - 10, self.rect.y - 5, 20, 30)
            if handle_rect.collidepoint(event.pos):
                self.dragging = True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
            
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel_x = event.pos[0] - self.rect.x
            ratio = max(0, min(1, rel_x / self.rect.width))
            self.value = int(self.min_val + ratio * (self.max_val - self.min_val))
            return True # Value changed
        return False

# VISUALIZER CLASS
class WarehouseVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Smart Warehouse: Control Center")
        self.clock = pygame.time.Clock()
        
        self.font_title = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_ui = pygame.font.SysFont("Arial", 16)

        # Config Params
        self.n_robots = 5
        self.coordination = "greedy"
        self.animation_speed = 0.15

        # Init Model
        self.reset_model()
        
        self.running = True
        self.paused = False
        self.needs_step = True
        
        # UI Elements
        self.buttons = []
        self.slider_robots = None
        self.init_ui()
        self.update_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def reset_model(self):
        self.model = WarehouseModel(n_robots=self.n_robots, coordination_type=self.coordination)
        self.smooth_positions = {}
        self.needs_step = True

    def init_ui(self):
        # 1. Mechanism Toggle
        self.btn_mech = Button(0, 0, 250, 40, f"Mode: {self.coordination.upper()}", self.cycle_mechanism)
        
        # 2. Main Controls
        self.btn_pause = Button(0, 0, 120, 40, "Pause/Play", self.toggle_pause)
        self.btn_reset = Button(0, 0, 120, 40, "Reset", self.reset_model)

        # 3. Speed Controls (Added Back)
        self.btn_slower = Button(0, 0, 120, 40, "Slower", self.decrease_speed)
        self.btn_faster = Button(0, 0, 120, 40, "Faster", self.increase_speed)
        
        # Combine all buttons
        self.buttons = [self.btn_mech, self.btn_pause, self.btn_reset, self.btn_slower, self.btn_faster]
        
        # 4. Robot Slider
        self.slider_robots = Slider(0, 0, 250, 1, 10, self.n_robots, "Robots")

    def reposition_ui(self):
        bx = self.window_w - SIDEBAR_WIDTH + 25
        by = 100
        
        # Mechanism Button
        self.btn_mech.rect.topleft = (bx, by)
        
        # Slider
        self.slider_robots.rect.topleft = (bx, by + 70)
        
        # Pause / Reset (Row 1)
        self.btn_pause.rect.topleft = (bx, by + 140)
        self.btn_reset.rect.topleft = (bx + 130, by + 140)
        
        # Slower / Faster (Row 2 - Added Back)
        self.btn_slower.rect.topleft = (bx, by + 190)
        self.btn_faster.rect.topleft = (bx + 130, by + 190)

    def cycle_mechanism(self):
        modes = ["greedy", "cnp", "auction"]
        curr_idx = modes.index(self.coordination)
        self.coordination = modes[(curr_idx + 1) % len(modes)]
        self.btn_mech.text = f"Mode: {self.coordination.upper()}"
        self.reset_model()

    def toggle_pause(self):
        self.paused = not self.paused

    def decrease_speed(self):
        self.animation_speed = max(0.01, self.animation_speed - 0.05)

    def increase_speed(self):
        self.animation_speed = min(1.0, self.animation_speed + 0.05)

    def update_layout(self, w, h):
        self.window_w = w
        self.window_h = h
        
        available_width = w - SIDEBAR_WIDTH
        grid_w_cells = self.model.grid.width
        grid_h_cells = self.model.grid.height
        
        scale_x = available_width // grid_w_cells
        scale_y = h // grid_h_cells
        self.cell_size = min(scale_x, scale_y)
        
        grid_pixel_width = self.cell_size * grid_w_cells
        grid_pixel_height = self.cell_size * grid_h_cells
        
        self.offset_x = (available_width - grid_pixel_width) // 2
        self.offset_y = (h - grid_pixel_height) // 2
        
        self.reposition_ui()

    def draw_sidebar(self):
        # Background
        sidebar_rect = pygame.Rect(self.window_w - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, self.window_h)
        pygame.draw.rect(self.screen, COLOR_SIDEBAR, sidebar_rect)
        
        # Title
        title = self.font_title.render("Configuration", True, COLOR_TEXT_WHITE)
        self.screen.blit(title, (self.window_w - SIDEBAR_WIDTH + 20, 20))
        
        # Status
        status = "PAUSED" if self.paused else "RUNNING"
        col = (255, 100, 100) if self.paused else (100, 255, 100)
        self.screen.blit(self.font_ui.render(f"Status: {status}", True, col), (self.window_w - SIDEBAR_WIDTH + 25, 60))

        # Draw UI
        for btn in self.buttons:
            btn.draw(self.screen, self.font_ui)
        self.slider_robots.draw(self.screen, self.font_ui)
        
        # Stats
        stats_y = 400
        stats = [
            f"Speed: {int(self.animation_speed * 100)}%",
            f"Orders Done: {self.model.order_manager.completed_orders}",
            f"Active Robots: {len([r for r in self.model.robot_agents if r.state != 'IDLE'])}"
        ]
        for line in stats:
            surf = self.font_ui.render(line, True, COLOR_TEXT_WHITE)
            self.screen.blit(surf, (self.window_w - SIDEBAR_WIDTH + 25, stats_y))
            stats_y += 30

    def update_robot_positions(self):
        all_arrived = True
        for agent in self.model.robot_agents:
            tx, ty = agent.pos
            if agent.unique_id not in self.smooth_positions:
                self.smooth_positions[agent.unique_id] = [tx, ty]
            
            cx, cy = self.smooth_positions[agent.unique_id]
            dx, dy = tx - cx, ty - cy
            
            if abs(dx) < 0.01 and abs(dy) < 0.01:
                self.smooth_positions[agent.unique_id] = [tx, ty]
            else:
                self.smooth_positions[agent.unique_id][0] += dx * self.animation_speed
                self.smooth_positions[agent.unique_id][1] += dy * self.animation_speed
                all_arrived = False
        return all_arrived

    def draw_game_area(self):
        # Grid
        gw = self.model.grid.width * self.cell_size
        gh = self.model.grid.height * self.cell_size
        for x in range(self.model.grid.width + 1):
            px = self.offset_x + x * self.cell_size
            pygame.draw.line(self.screen, COLOR_GRID, (px, self.offset_y), (px, self.offset_y + gh))
        for y in range(self.model.grid.height + 1):
            py = self.offset_y + y * self.cell_size
            pygame.draw.line(self.screen, COLOR_GRID, (self.offset_x, py), (self.offset_x + gw, py))

        # Static Agents
        for content, (x, y) in self.model.grid.coord_iter():
            rect = (self.offset_x + x*self.cell_size, self.offset_y + y*self.cell_size, self.cell_size, self.cell_size)
            for agent in content:
                name = agent.__class__.__name__
                if name == "ShelfAgent":
                    col = pygame.Color(getattr(agent, "color", "brown"))
                    pygame.draw.rect(self.screen, col, rect)
                    pygame.draw.rect(self.screen, (50,50,50), rect, 1)
                elif name == "PackingStationAgent":
                    col = pygame.Color(getattr(agent, "color", "black"))
                    pygame.draw.rect(self.screen, col, rect)
                elif name == "ChargingStationAgent":
                    pygame.draw.rect(self.screen, (255, 140, 0), rect)

        # Robots
        for agent in self.model.robot_agents:
            if agent.unique_id not in self.smooth_positions: continue
            sx, sy = self.smooth_positions[agent.unique_id]
            px = int(self.offset_x + sx * self.cell_size + self.cell_size/2)
            py = int(self.offset_y + sy * self.cell_size + self.cell_size/2)
            
            col = (100,100,100)
            if agent.battery < 20: col = (255,0,0)
            elif agent.state == "TO_DELIVER": col = (0,255,0)
            elif agent.state == "TO_PICKUP": col = (0,0,255)
            elif agent.state == "CHARGING": col = (255,255,0)
            elif agent.state == "TO_CHARGE": col = (255,165,0)
            
            radius = int(self.cell_size/2.5)
            pygame.draw.circle(self.screen, col, (px, py), radius)
            
            # Battery
            bar_w = self.cell_size - 4
            bar_h = 4
            fill = (agent.battery/100) * bar_w
            pygame.draw.rect(self.screen, (50,50,50), (px-bar_w//2, py-radius-6, bar_w, bar_h))
            pygame.draw.rect(self.screen, (0,255,0), (px-bar_w//2, py-radius-6, fill, bar_h))

    def run(self):
        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.update_layout(event.w, event.h)
                
                # UI Events
                for btn in self.buttons: btn.handle_event(event)
                if self.slider_robots.handle_event(event):
                    # If slider changed, update param and reset
                    if self.n_robots != self.slider_robots.value:
                        self.n_robots = self.slider_robots.value
                        self.reset_model()

            for btn in self.buttons: btn.check_hover(mouse_pos)

            # Simulation Logic
            if not self.paused:
                if self.needs_step:
                    self.model.step()
                    self.needs_step = False
                if self.update_robot_positions():
                    self.needs_step = True

            # Draw
            self.screen.fill(COLOR_BG)
            self.draw_game_area()
            self.draw_sidebar()
            
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    viz = WarehouseVisualizer()
    viz.run()