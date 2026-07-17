import pygame
import random
import string
import sys
 
WIDTH, HEIGHT = 800, 600
FPS = 60
 
BG_COLOR = (8, 10, 14)
GRID_COLOR = (18, 26, 24)
NEON_GREEN = (57, 255, 140)
NEON_CYAN = (60, 220, 255)
NEON_RED = (255, 70, 90)
DIM_GREEN = (25, 90, 60)
WHITE = (235, 245, 240)
 
FONT_NAME = "consolas"
 
CODE_LEN_MIN = 3
CODE_LEN_MAX = 5
 
BASE_FALL_SPEED = 40.0
SPEED_PER_LEVEL = 8.0
SPAWN_INTERVAL_START = 1.6
SPAWN_INTERVAL_MIN = 0.55
LEVEL_UP_EVERY = 8
 
MAX_HEALTH = 100
DAMAGE_PER_MISS = 12
 
BLOCK_W, BLOCK_H = 90, 40
 
 
def random_code(length=None):
    if length is None:
        length = random.randint(CODE_LEN_MIN, CODE_LEN_MAX)
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))
 
 
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color")
 
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, 6.283)
        speed = random.uniform(60, 220)
        self.vx = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x
        self.vy = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y
        self.max_life = random.uniform(0.35, 0.7)
        self.life = self.max_life
        self.color = color
 
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 250 * dt
        self.life -= dt
        return self.life > 0
 
    def draw(self, surf):
        if self.life <= 0:
            return
        t = max(0.0, self.life / self.max_life)
        r = max(1, int(4 * t))
        alpha_color = tuple(int(c * t + 8 * (1 - t)) for c in self.color)
        pygame.draw.circle(surf, alpha_color, (int(self.x), int(self.y)), r)
 
 
class Block:
    def __init__(self, x, code, speed):
        self.x = x
        self.y = -BLOCK_H
        self.code = code
        self.speed = speed
        self.typed_len = 0
 
    def update(self, dt):
        self.y += self.speed * dt
 
    @property
    def bottom(self):
        return self.y + BLOCK_H
 
    def draw(self, surf, font, is_target):
        rect = pygame.Rect(int(self.x), int(self.y), BLOCK_W, BLOCK_H)
 
        color = NEON_CYAN if is_target else DIM_GREEN
        pygame.draw.rect(surf, (color[0] // 4, color[1] // 4, color[2] // 4), rect)
        pygame.draw.rect(surf, color, rect, width=2)
 
        matched = self.code[: self.typed_len]
        remaining = self.code[self.typed_len :]
 
        matched_surf = font.render(matched, True, NEON_GREEN if is_target else DIM_GREEN)
        remaining_surf = font.render(remaining, True, WHITE if is_target else (90, 100, 96))
 
        total_w = matched_surf.get_width() + remaining_surf.get_width()
        start_x = rect.centerx - total_w // 2
        text_y = rect.centery - matched_surf.get_height() // 2
 
        surf.blit(matched_surf, (start_x, text_y))
        surf.blit(remaining_surf, (start_x + matched_surf.get_width(), text_y))
 
 
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Desk Sentinel: Terminal Edition")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
 
        self.font_block = pygame.font.SysFont(FONT_NAME, 22, bold=True)
        self.font_ui = pygame.font.SysFont(FONT_NAME, 20)
        self.font_ui_big = pygame.font.SysFont(FONT_NAME, 36, bold=True)
        self.font_title = pygame.font.SysFont(FONT_NAME, 54, bold=True)
 