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

        self.sounds_ok = True
        try:
            pygame.mixer.init()
            self.snd_type = self._make_tone(880, 0.03)
            self.snd_clear = self._make_tone(1400, 0.09)
            self.snd_miss = self._make_tone(140, 0.25)
        except Exception:
            self.sounds_ok = False

        self.reset()

    def _make_tone(self, freq, duration):
        import array

        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = array.array("h")
        amp = 14000
        for i in range(n_samples):
            t = i / sample_rate
            fade = 1.0 - (i / n_samples)
            val = int(amp * fade * pygame.math.Vector2(1, 0).rotate_rad(2 * 3.14159 * freq * t).x)
            buf.append(val)
            buf.append(val)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, snd):
        if self.sounds_ok:
            try:
                snd.play()
            except Exception:
                pass

    def reset(self):
        self.blocks = []
        self.particles = []
        self.typed = ""
        self.target_block = None
        self.health = MAX_HEALTH
        self.score = 0
        self.level = 1
        self.spawn_timer = 0.0
        self.spawn_interval = SPAWN_INTERVAL_START
        self.game_over = False
        self.time_alive = 0.0

    def current_fall_speed(self):
        return BASE_FALL_SPEED + SPEED_PER_LEVEL * (self.level - 1)

    def spawn_block(self):
        x = random.randint(20, WIDTH - BLOCK_W - 20)
        code = random_code()
        speed = self.current_fall_speed() * random.uniform(0.9, 1.15)
        self.blocks.append(Block(x, code, speed))

    def handle_key(self, event):
        if self.game_over:
            if event.key == pygame.K_r:
                self.reset()
            return

        if event.key == pygame.K_BACKSPACE:
            self.typed = self.typed[:-1]
            self._update_target()
            return

        if event.key == pygame.K_RETURN:
            self._try_submit()
            return

        if event.unicode and event.unicode.isalnum():
            self.typed += event.unicode.upper()
            if len(self.typed) > CODE_LEN_MAX:
                self.typed = self.typed[:CODE_LEN_MAX]
            self._update_target()
            self.play(self.snd_type)

    def _update_target(self):
        self.target_block = None
        for b in self.blocks:
            if self.typed and b.code.startswith(self.typed):
                b.typed_len = len(self.typed)
                if self.target_block is None:
                    self.target_block = b
            else:
                b.typed_len = 0

    def _try_submit(self):
        for b in self.blocks:
            if b.code == self.typed:
                self._destroy_block(b)
                self.typed = ""
                self.target_block = None
                return
        self.typed = ""
        for b in self.blocks:
            b.typed_len = 0

    def _destroy_block(self, block):
        self.blocks.remove(block)
        self.score += 1
        cx, cy = block.x + BLOCK_W / 2, block.y + BLOCK_H / 2
        for _ in range(22):
            self.particles.append(Particle(cx, cy, NEON_GREEN))
        self.play(self.snd_clear)

        if self.score % LEVEL_UP_EVERY == 0:
            self.level += 1
            self.spawn_interval = max(SPAWN_INTERVAL_MIN, self.spawn_interval * 0.88)

    def update(self, dt):
        if self.game_over:
            return

        self.time_alive += dt
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_block()

        for b in list(self.blocks):
            b.update(dt)
            if b.bottom >= HEIGHT:
                self.blocks.remove(b)
                self.health -= DAMAGE_PER_MISS
                self.play(self.snd_miss)
                for _ in range(16):
                    self.particles.append(
                        Particle(b.x + BLOCK_W / 2, HEIGHT - 10, NEON_RED)
                    )
                if b is self.target_block:
                    self.typed = ""
                    self.target_block = None
                if self.health <= 0:
                    self.health = 0
                |