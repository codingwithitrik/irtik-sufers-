import pygame
import random
import os
import sys
from pathlib import Path

# -------------------- Config --------------------
GAME_NAME = "itrik surfers"
WIDTH, HEIGHT = 900, 500
FPS = 60

GROUND_Y = HEIGHT - 90
PLAYER_X = 120

# Files
HIGHSCORE_FILE = "highscore.txt"

# -------------------- Init --------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(GAME_NAME.capitalize())
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 24)
big_font = pygame.font.SysFont("Verdana", 48, bold=True)

# Ensure highscore file exists
Path(HIGHSCORE_FILE).touch(exist_ok=True)

# -------------------- Utility --------------------
def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass

# -------------------- Game Objects --------------------
class Player:
    def __init__(self):
        self.width = 48
        self.height = 64
        self.x = PLAYER_X
        self.y = GROUND_Y - self.height
        self.dy = 0.0
        self.gravity = 0.9
        self.jump_strength = -16
        self.double_jump_allowed = True
        self.on_ground = True
        self.color = (20, 160, 100)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.shield = 0  # frames of shield remaining

    def update(self):
        self.dy += self.gravity
        self.y += self.dy

        if self.y >= GROUND_Y - self.height:
            self.y = GROUND_Y - self.height
            self.dy = 0
            self.on_ground = True
            self.double_jump_allowed = True
        else:
            self.on_ground = False

        self.rect.topleft = (int(self.x), int(self.y))
        if self.shield > 0:
            self.shield -= 1

    def jump(self):
        if self.on_ground:
            self.dy = self.jump_strength
            self.on_ground = False
            self.double_jump_allowed = True
        elif self.double_jump_allowed:
            # double jump
            self.dy = self.jump_strength * 0.9
            self.double_jump_allowed = False

    def draw(self, surf):
        # body
        pygame.draw.rect(surf, self.color, self.rect, border_radius=8)
        # face / mark
        eye = (self.rect.centerx + 10, self.rect.centery - 6)
        pygame.draw.circle(surf, (255, 255, 255), eye, 6)
        pygame.draw.circle(surf, (0,0,0), eye, 2)
        # shield visual
        if self.shield > 0:
            pygame.draw.ellipse(surf, (120, 200, 255, 80), self.rect.inflate(20, 18), 3)

class Obstacle:
    def __init__(self, x, w, h, speed):
        self.rect = pygame.Rect(x, GROUND_Y - h, w, h)
        self.color = (200, 50, 40)
        self.speed = speed
        self.passed = False

    def update(self):
        self.rect.x -= int(self.speed)

    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=6)
        # hazard stripe
        pygame.draw.line(surf, (0,0,0), (self.rect.left+4, self.rect.top+6), (self.rect.right-6, self.rect.bottom-6), 3)

class Coin:
    def __init__(self, x, y, speed):
        self.r = 10
        self.x = x
        self.y = y
        self.speed = speed
        self.rect = pygame.Rect(x-self.r, y-self.r, self.r*2, self.r*2)
        self.collected = False

    def update(self):
        self.x -= int(self.speed)
        self.rect.topleft = (self.x - self.r, self.y - self.r)

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 200, 0), (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x)-2, int(self.y)-3), 4)

class PowerUp:
    def __init__(self, x, y, speed, kind="shield"):
        self.x = x; self.y = y; self.speed = speed
        self.r = 14
        self.kind = kind
        self.rect = pygame.Rect(x-self.r, y-self.r, self.r*2, self.r*2)

    def update(self):
        self.x -= int(self.speed)
        self.rect.topleft = (self.x - self.r, self.y - self.r)

    def draw(self, surf):
        if self.kind == "shield":
            pygame.draw.circle(surf, (100,200,255), (int(self.x), int(self.y)), self.r)
            pygame.draw.circle(surf, (255,255,255), (int(self.x)-3, int(self.y)-4), 5)
        else:
            pygame.draw.rect(surf, (200,120,50), self.rect)

# -------------------- Background (parallax) --------------------
class Background:
    def __init__(self):
        self.layers = []
        # create simple layers rectangles for parallax
        for i, color in enumerate([(100,180,255),(85,155,220),(60,120,190)]):
            speed = 0.6 + i*0.4
            surface = pygame.Surface((WIDTH, HEIGHT // 3), pygame.SRCALPHA)
            surface.fill(color)
            self.layers.append({"surf": surface, "x": 0, "speed": speed, "y": i*(HEIGHT//6)})

    def update(self, base_speed):
        for l in self.layers:
            l["x"] -= int(base_speed * l["speed"])
            if l["x"] <= -WIDTH:
                l["x"] = 0

    def draw(self, surf):
        for l in self.layers:
            surf.blit(l["surf"], (l["x"], l["y"]))
            surf.blit(l["surf"], (l["x"] + WIDTH, l["y"]))

# -------------------- Main Game Class --------------------
class ItrikSurfers:
    def __init__(self):
        self.running = True
        self.playing = False
        self.player = Player()
        self.background = Background()

        self.scroll_speed = 6.0
        self.spawn_timer = 0
        self.coin_timer = 0
        self.power_timer = 0
        self.obstacles = []
        self.coins = []
        self.powerups = []

        self.score = 0
        self.distance = 0
        self.highscore = load_highscore()
        self.game_over = False

        # Difficulty curve
        self.difficulty_increment = 0.0005

    def reset(self):
        self.player = Player()
        self.obstacles = []
        self.coins = []
        self.powerups = []
        self.score = 0
        self.distance = 0
        self.scroll_speed = 6.0
        self.spawn_timer = 0
        self.coin_timer = 0
        self.power_timer = 0
        self.game_over = False

    def spawn_obstacle(self):
        w = random.randint(30, 70)
        h = random.randint(40, 100)
        x = WIDTH + random.randint(20, 120)
        self.obstacles.append(Obstacle(x, w, h, self.scroll_speed))

    def spawn_coin(self):
        x = WIDTH + random.randint(30, 200)
        y = random.randint(GROUND_Y - 180, GROUND_Y - 40)
        self.coins.append(Coin(x, y, self.scroll_speed))

    def spawn_powerup(self):
        x = WIDTH + random.randint(200, 600)
        y = random.randint(GROUND_Y - 180, GROUND_Y - 60)
        self.powerups.append(PowerUp(x, y, self.scroll_speed, kind="shield"))

    def update(self):
        if not self.playing:
            return

        # increase difficulty gradually by raising scroll_speed slightly
        self.scroll_speed += self.difficulty_increment
        self.distance += self.scroll_speed / 10.0
        self.background.update(self.scroll_speed)

        # spawn logic
        self.spawn_timer += 1
        if self.spawn_timer > max(18, 70 - int(self.scroll_speed*3)):
            self.spawn_obstacle()
            self.spawn_timer = 0

        self.coin_timer += 1
        if self.coin_timer > 40:
            self.spawn_coin()
            self.coin_timer = 0

        self.power_timer += 1
        if self.power_timer > 900:
            self.spawn_powerup()
            self.power_timer = 0

        # update player
        self.player.update()

        # update obstacles
        for ob in self.obstacles[:]:
            ob.speed = self.scroll_speed
            ob.update()
            if ob.rect.right < -50:
                self.obstacles.remove(ob)
            # collision
            if ob.rect.colliderect(self.player.rect):
                if self.player.shield <= 0:
                    self.game_over = True
                    self.playing = False
                else:
                    # destroy obstacle if shield active
                    try:
                        self.obstacles.remove(ob)
                    except:
                        pass

            # scoring for passing obstacles
            if not ob.passed and ob.rect.right < self.player.x:
                ob.passed = True
                self.score += 5

        # update coins
        for c in self.coins[:]:
            c.speed = self.scroll_speed
            c.update()
            if c.x < -50:
                self.coins.remove(c)
            if c.rect.colliderect(self.player.rect) and not c.collected:
                c.collected = True
                self.score += 10
                try:
                    self.coins.remove(c)
                except:
                    pass

        # update powerups
        for p in self.powerups[:]:
            p.speed = self.scroll_speed
            p.update()
            if p.x < -50:
                self.powerups.remove(p)
            if p.rect.colliderect(self.player.rect):
                if p.kind == "shield":
                    self.player.shield = FPS * 3  # 3 seconds
                try:
                    self.powerups.remove(p)
                except:
                    pass

        # distance-based score
        self.score += int(self.scroll_speed / 250)

    def draw_ui(self, surf):
        # ground
        pygame.draw.rect(surf, (40,40,40), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        # score/distance
        score_s = font.render(f"Score: {self.score}", True, (255,255,255))
        dist_s = font.render(f"Distance: {int(self.distance)} m", True, (255,255,255))
        hs_s = font.render(f"Highscore: {self.highscore}", True, (255,255,255))
        surf.blit(score_s, (10, 10))
        surf.blit(dist_s, (10, 36))
        surf.blit(hs_s, (10, 62))

        # instructions small
        instr = font.render("SPACE to jump, P to pause. Collect coins and shield!", True, (220,220,220))
        surf.blit(instr, (WIDTH//2 - instr.get_width()//2, 10))

    def draw(self, surf):
        # sky
        surf.fill((135, 206, 250))
        # background layers
        self.background.draw(surf)

        # decorative distant city (simple)
        for i in range(8):
            bx = (i * 120 + (pygame.time.get_ticks()//20) % 120) % WIDTH
            pygame.draw.rect(surf, (120,120,140), (bx, GROUND_Y - 220, 80, 160))

        # draw coins
        for c in self.coins:
            c.draw(surf)
        # draw powerups
        for p in self.powerups:
            p.draw(surf)
        # draw obstacles
        for ob in self.obstacles:
            ob.draw(surf)

        # draw player
        self.player.draw(surf)

        # UI
        self.draw_ui(surf)

    def start_screen(self):
        screen.fill((20, 20, 40))
        title = big_font.render(GAME_NAME.upper(), True, (255, 200, 60))
        subtitle = font.render("Press SPACE to start - Jump with SPACE - Press P to pause", True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 80))
        hs = font.render(f"Highscore: {self.highscore}", True, (255,255,255))
        screen.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//3 + 120))
        pygame.display.flip()

    def game_over_screen(self):
        # save highscore
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.score)

        screen.fill((10,10,20))
        over = big_font.render("GAME OVER", True, (255, 90, 90))
        score_text = font.render(f"Score: {self.score}", True, (255,255,255))
        hs_text = font.render(f"Highscore: {self.highscore}", True, (255,255,255))
        resume_text = font.render("Press R to Restart or Q to Quit", True, (200,200,200))

        screen.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//3))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//3 + 80))
        screen.blit(hs_text, (WIDTH//2 - hs_text.get_width()//2, HEIGHT//3 + 110))
        screen.blit(resume_text, (WIDTH//2 - resume_text.get_width()//2, HEIGHT//3 + 160))
        pygame.display.flip()

# -------------------- Main Loop --------------------
def main():
    game = ItrikSurfers()
    in_start = True
    paused = False

    while game.running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False

            if event.type == pygame.KEYDOWN:
                if in_start:
                    if event.key == pygame.K_SPACE:
                        game.playing = True
                        in_start = False
                elif not game.playing and game.game_over:
                    if event.key == pygame.K_r:
                        game.reset()
                        game.playing = True
                    elif event.key == pygame.K_q:
                        game.running = False
                else:
                    if event.key == pygame.K_SPACE:
                        game.player.jump()
                    if event.key == pygame.K_p:
                        paused = not paused

        if in_start:
            game.start_screen()
            continue

        if paused:
            # draw paused overlay
            pause_s = big_font.render("PAUSED", True, (255,255,255))
            screen.blit(pause_s, (WIDTH//2 - pause_s.get_width()//2, HEIGHT//2 - 30))
            pygame.display.flip()
            continue

        # Update game state
        if game.playing:
            game.update()

        # Draw
        game.draw(screen)
        pygame.display.flip()

        # Game over handling
        if game.game_over:
            game.game_over_screen()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
