#!/usr/bin/env python3
import os, pygame, sys, math, time, random
from pygame.locals import *
from enum import Enum

# Detect whether we're running on a PiTFT (framebuffer at /dev/fb1)
def on_pitft():
    return os.path.exists("/dev/fb1")

# 如果要在树莓派的帧缓冲区上使用，通常需要在初始化 pygame 之前设置 SDL 环境变量，
# 以便 SDL 能够选择帧缓冲区驱动程序。我们仅在运行在 PiTFT 上时才设置这些变量。
# 注意：这些环境变量必须在 pygame.init() 或 SDL 初始化之前设置，才能生效。
if on_pitft():
    # These are common settings for PiTFT; you can adjust or remove as needed.
    os.putenv('SDL_VIDEODRIVER', 'fbcon')
    os.putenv('SDL_FBDEV', '/dev/fb1')
    # If using TSLIB for touchscreen input, enable the following (optional):
    # os.putenv('SDL_MOUSEDRV', 'TSLIB')
    # os.putenv('SDL_MOUSEDEV', '/dev/input/event0')

# Initialize pygame after any environment changes
pygame.init()

# 初始化音频混音器（用于音效）并加载 BGM/SFX
try:
    pygame.mixer.init()
except Exception:
    pass

# 脚本目录
script_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(script_dir, 'audio')
if not os.path.exists(audio_dir):
    audio_dir = script_dir

# helper to load short sounds
def _load_sound(fname, volume=0.6):
    path = os.path.join(audio_dir, fname)
    if os.path.exists(path):
        try:
            s = pygame.mixer.Sound(path)
            s.set_volume(volume)
            print(f'Loaded SFX: {path}')
            return s
        except Exception as e:
            print(f'Failed loading SFX {path}: {e}')
    return None

# Persistent background music (looping)
try:
    bgm_path = os.path.join(audio_dir, 'bgm.wav')
    if os.path.exists(bgm_path):
        try:
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
            print(f'Playing BGM: {bgm_path}')
        except Exception as e:
            print(f'无法播放BGM: {e}')
    else:
        print(f'未找到BGM文件: {bgm_path}')
except Exception as e:
    print(f'BGM加载异常: {e}')

# Load selectable SFX (fall back to sensible alternatives)
SFX = {}
SFX['medium_click'] = _load_sound('medium_click.wav', 0.6) or _load_sound('click.wav', 0.6)
SFX['slight_click'] = _load_sound('slight_click.wav', 0.45)
SFX['ding'] = _load_sound('ding.wav', 0.7)
SFX['delete'] = _load_sound('delete.wav', 0.6)
SFX['click'] = _load_sound('click.wav', 0.6)

# backward-compatible single variable for simple usages
click_sound = SFX.get('medium_click')

# Choose resolution depending on whether we're on the PiTFT framebuffer
if on_pitft():
    W, H = 480, 320
else:
    W, H = 800, 600

# Use fullscreen on PiTFT
flags = 0
if on_pitft():
    flags |= pygame.FULLSCREEN

lcd = pygame.display.set_mode((W, H), flags)
pygame.display.set_caption("Stellaris")
clock = pygame.time.Clock()
# Hide mouse cursor on PiTFT (touchscreen)
pygame.mouse.set_visible(not on_pitft())

# Background image support: try to load a background image from the script
# directory (background.png or background.jpg). If not found, generate a
# simple procedural starfield as a fallback.
BACKGROUND_SURFACE = None
try:
    # prefer PNG, then JPG
    for _name in ("background.png", "background.jpg"):
        bg_path = os.path.join(script_dir, _name)
        if os.path.exists(bg_path):
            try:
                _img = pygame.image.load(bg_path)
                # convert to display format and scale to screen size
                BACKGROUND_SURFACE = pygame.transform.scale(_img.convert(), (W, H))
                print(f"Loaded background image: {_name}")
            except Exception:
                BACKGROUND_SURFACE = None
            break
    # fallback: generate a simple starfield surface
    if BACKGROUND_SURFACE is None:
        bs = pygame.Surface((W, H))
        bs.fill((6, 10, 20))
        # deterministic small starfield so it doesn't change every run
        rnd = random.Random(42)
        for _ in range(220):
            sx = rnd.randint(0, W-1)
            sy = rnd.randint(0, H-1)
            col = rnd.choice([(200,200,255),(180,180,255),(255,255,200),(220,220,220)])
            sr = rnd.choice([1,1,2])
            pygame.draw.circle(bs, col, (sx, sy), sr)
        BACKGROUND_SURFACE = bs
except Exception:
    BACKGROUND_SURFACE = None

# Colors & fonts
WHITE = (255, 255, 255)
BLUE = (0, 120, 255)
BLACK = (0, 0, 0)
RED = (255, 60, 60)
YELLOW = (255, 255, 0)
LIGHT_YELLOW = (255, 255, 180)  # 淡黄色
LIGHT_BLUE = (180, 180, 255)    # 淡蓝色
WORKER_GREEN = (60, 200, 100)

# 行星可能的颜色列表
PLANET_COLORS = [WHITE, LIGHT_YELLOW, LIGHT_BLUE]

# 环的颜色候选（会在行星创建时随机选取）
RING_COLORS = [
    (200, 100, 255),
    (255, 180, 80),
    (120, 220, 180),
    (220, 120, 120),
    (200, 200, 100),
    (180, 160, 255),
    (160, 255, 200),
]

# Star name list
STAR_NAMES = [
    "Vega", "Sirius", "Polaris", "Rigel", "Arcturus",
    "Altair", "Antares", "Deneb", "Lyra", "Betelgeuse"
]

# 字母列表（用于行星命名）
LETTERS = list("ABCDEFGHIJKLMN")

# 尝试加载支持中文的字体
def load_font_with_fallback(size):
    """尝试加载中文字体，失败则使用默认字体"""
    chinese_fonts = [
        'C:\\Windows\\Fonts\\msyh.ttc',      # 微软雅黑
        'C:\\Windows\\Fonts\\simhei.ttf',    # 黑体
        'C:\\Windows\\Fonts\\simsun.ttc',    # 宋体
        'C:\\Windows\\Fonts\\simkai.ttf',    # 楷体
        '/System/Library/Fonts/PingFang.ttc', # macOS
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', # Linux
    ]
    
    for font_path in chinese_fonts:
        if os.path.exists(font_path):
            try:
                return pygame.font.Font(font_path, size)
            except Exception:
                continue
    
    # 如果所有中文字体都失败，使用系统默认字体
    return pygame.font.Font(None, size)

font_small = load_font_with_fallback(18)
font_medium = load_font_with_fallback(26)
font_big = load_font_with_fallback(58)

# 矿物颜色映射（用于多个弹窗）
ORE_COLORS = {
    'Gold': (255, 215, 0),
    'Silver': (192, 192, 192),
    'Rare Earth': (200, 100, 255),
    'Copper': (184, 115, 51),
    'Aluminum': (169, 169, 169)
}

# 单位目录：将三种兵种归类到“战士”类别下，包含生命值、攻击力和价格（与游戏资源对应）
# 价格字段使用与游戏中一致的矿物命名：Gold, Silver, Rare Earth, Copper, Aluminum
# 以及现金使用键名 'USD'（对应 GameWorld.player_usd）
UNIT_CATALOG = {
    'Warrior': {
        'Warrior': {
            'hp': 10,
            'attack': 10,
            'price': {'Gold': 5, 'Silver': 5, 'USD': 100}
        },
        'Tank': {
            'hp': 40,
            'attack': 20,
            'price': {'Gold': 25, 'Silver': 15, 'Rare Earth': 5, 'Copper': 5}
        },
        'Starfighter': {
            'hp': 100,
            'attack': 40,
            'price': {'Gold': 50, 'Silver': 25, 'Rare Earth': 20, 'Copper': 15, 'Aluminum': 15}
        }
    }
}

# 游戏状态
class GameState(Enum):
    MENU = 1
    MODE_SELECT = 2
    SCALE_SELECT = 3  # 新增：规模选择
    SINGLE_PLAYER = 4  # 修改：从3改为4

# Planet types
class PlanetType(Enum):
    BARREN = "Barren Planet"
    NORMAL = "Standard Planet"
    RICH = "Prosperous Planet"


# Celestial body class
class CelestialBody:
    def __init__(self, x, y, is_star=False, star_name=None, planet_letter=None):
        self.x = x
        self.y = y
        self.is_star = is_star
        self.color = random.choice([RED, YELLOW]) if is_star else random.choice(PLANET_COLORS)
        # Randomize planet size for variety
        self.radius = 16 if is_star else random.randint(6, 12)  # variable body size
        self.selected = False
        
        # 所有权：None（中立）、'player'（玩家）、'ai'（AI）
        self.owner = None
        
        # 舰船数量：初始为0（未占领的星球没有舰船）
        self.fleet_count = 0
        
        # 战斗/占领状态
        self.under_siege = False  # 是否正在被围攻/占领中
        self.siege_start_time = None  # 围攻开始时间
        self.siege_duration = 0  # 围攻总时长（秒）
        self.attacker_owner = None  # 进攻方所有者
        self.attacker_count = 0  # 进攻方舰船数量
        self.defender_count = 0  # 防守方舰船数量
        
        # 动画相关属性
        if not is_star:
            # 行星上下起伏动画：随机初始相位和频率
            self.float_phase = random.uniform(0, 2 * math.pi)
            self.float_speed = random.uniform(0.5, 1.5)  # 起伏速度
            self.float_amplitude = random.uniform(2, 4)  # 起伏幅度（像素）
        else:
            # 恒星辐射动画
            self.pulse_phase = random.uniform(0, 2 * math.pi)
            self.pulse_speed = random.uniform(0.8, 1.2)

        # 每个非恒星行星有一个随机环色和样式
        if not is_star:
            self.ring_color = random.choice(RING_COLORS)
            self.ring_angle = random.uniform(-30.0, 30.0)
            self.ring_visible = random.random() < 0.85
            # small variety flags
            self.has_glow = random.random() < 0.5
            self.pattern_type = random.choice(['none', 'spots', 'stripes'])
            if self.pattern_type == 'spots':
                self.pattern_color = tuple(max(0, c - 40) for c in self.color)
            elif self.pattern_type == 'stripes':
                self.pattern_color = tuple(min(255, c + 30) for c in self.color)
            else:
                self.pattern_color = None
            
            # Pre-generate pattern data (spots or stripes) so they don't change every frame
            if self.pattern_type == 'spots':
                # Pre-generate random spot list (fixed per planet)
                num_spots = random.randint(2, 4)
                self.pattern_spots = []
                for _ in range(num_spots):
                    # Store spot data as (sx_ratio, sy_ratio, sr_ratio) where ratios are 0.0-1.0
                    sx_ratio = random.uniform(0.2, 0.8)
                    sy_ratio = random.uniform(0.2, 0.8)
                    sr_ratio = random.uniform(0.15, 0.5)
                    self.pattern_spots.append((sx_ratio, sy_ratio, sr_ratio))
            elif self.pattern_type == 'stripes':
                # Stripes are deterministic (always 3 horizontal stripes), no randomness needed
                self.pattern_spots = None
            else:
                self.pattern_spots = None

        if is_star:
            self.name = star_name
            self.starbase = 0  # Initial starbase value
        else:
            # 使用传入的字母，如果没有则随机选择
            letter = planet_letter if planet_letter else random.choice(LETTERS)
            self.name = f"Planet {letter} of {star_name}"
            # 根据2:7:1的概率分配行星类型
            planet_type_roll = random.random()
            if planet_type_roll < 0.2:
                self.planet_type = PlanetType.BARREN
                self.max_districts = 3
            elif planet_type_roll < 0.9:
                self.planet_type = PlanetType.NORMAL
                self.max_districts = 8
            else:
                self.planet_type = PlanetType.RICH
                self.max_districts = 15

            # 随机分配区划
            total_districts = self.max_districts
            self.city_districts = 0
            self.agri_districts = 0
            self.industrial_districts = 0

            while total_districts > 0:
                district_type = random.randint(0, 2)
                if district_type == 0:
                    self.city_districts += 1
                elif district_type == 1:
                    self.agri_districts += 1
                else:
                    self.industrial_districts += 1
                total_districts -= 1
            
            # 星球上的工人数量（玩家可派遣工人来挖矿）
            self.assigned_workers = 0
            
            # 矿物类型及其储量 - 每个星球随机分配矿物储量
            # 黄金(Gold), 白银(Silver), 稀土(Rare Earth), 铜矿(Copper), 铝(Aluminum)
            total_ore_points = random.randint(50, 200)  # 每个星球的总矿物点数
            raw = {
                'Gold': random.randint(5, 50),
                'Silver': random.randint(5, 50),
                'Rare Earth': random.randint(5, 50),
                'Copper': random.randint(5, 50),
                'Aluminum': random.randint(5, 50),
            }
            # 规范化到 total_ore_points（内部用于概率分配），但我们不在 UI 中显示上限
            total_raw = sum(raw.values())
            self.ore_reserves = {}
            for ore_type, v in raw.items():
                # ensure at least 1 point
                self.ore_reserves[ore_type] = max(1, int((v / total_raw) * total_ore_points))
            # 保存初始总量以便计算开采比例
            self._initial_total_ore = sum(self.ore_reserves.values())

            # 已挖出的矿物储量 (玩家的矿物)
            self.mined_ore = {k: 0 for k in self.ore_reserves}

            # 随机生成“盛产”标签：选择1或2种主要矿物（按储量排序并随机决定是否包含第二种）
            sorted_ores = sorted(self.ore_reserves.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_ores[0][0]
            self.rich_in = [primary]
            if len(sorted_ores) > 1 and random.random() < 0.5:
                self.rich_in.append(sorted_ores[1][0])

            # 工人每秒挖矿速率（基于工业区划，降低到四分之一）
            self.mining_rate = self.industrial_districts * 0.125  # 原来是0.5，现在是0.125（四分之一）

    def draw(self, surface, camera_x, camera_y, zoom):
        # 计算动画偏移
        current_time = time.time()
        
        # 行星上下起伏（只影响y坐标）
        float_offset_y = 0
        if not self.is_star:
            self.float_phase += 0.016 * self.float_speed  # 约60fps下的相位增量
            float_offset_y = math.sin(self.float_phase) * self.float_amplitude
        
        screen_x = (self.x - camera_x) * zoom + W//2
        screen_y = (self.y - camera_y) * zoom + H//2 + float_offset_y  # 加上起伏偏移
        screen_y_fixed = (self.y - camera_y) * zoom + H//2  # 不受起伏影响的固定y坐标（用于角标）

        # 只绘制在屏幕范围内的星体
        if 0 <= screen_x <= W and 0 <= screen_y <= H:
            radius = max(2, int(self.radius * zoom))
            
            # 恒星辐射效果（透明圈向外扩散）
            if self.is_star:
                self.pulse_phase += 0.016 * self.pulse_speed
                pulse_progress = (math.sin(self.pulse_phase) + 1) / 2  # 0到1的循环
                if pulse_progress > 0.1:  # 只在部分时间显示
                    pulse_radius = int(radius * (1.2 + pulse_progress * 0.6))
                    pulse_alpha = int(100 * (1 - pulse_progress))  # 逐渐透明
                    try:
                        pulse_size = pulse_radius * 2 + 8
                        pulse_surf = pygame.Surface((pulse_size, pulse_size), pygame.SRCALPHA)
                        pulse_color = (self.color[0], self.color[1], self.color[2], pulse_alpha)
                        pygame.draw.circle(pulse_surf, pulse_color, (pulse_size//2, pulse_size//2), pulse_radius, 2)
                        surface.blit(pulse_surf, (int(screen_x - pulse_size//2), int(screen_y - pulse_size//2)))
                    except: pass

            # Soft shadow using alpha surface to avoid heavy ghosting
            shadow_offset = max(1, int(radius * 0.12))
            try:
                ss = max(8, int(radius * 4))
                shadow_surf = pygame.Surface((ss, ss), pygame.SRCALPHA)
                shadow_color = (0, 0, 0, 90)
                pygame.draw.circle(shadow_surf, shadow_color, (ss//2, ss//2), int(radius * 0.95))
                surface.blit(shadow_surf, (int(screen_x - ss//2 + shadow_offset), int(screen_y - ss//2 + shadow_offset)))
            except: pygame.draw.circle(surface, (0, 0, 0), (int(screen_x + shadow_offset), int(screen_y + shadow_offset)), radius)

            # optional atmosphere glow (subtle)
            if (not self.is_star) and getattr(self, 'has_glow', False):
                try:
                    glow_size = max(8, int(radius * 3.0))
                    glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                    glow_color = (self.color[0], self.color[1], self.color[2], 60)
                    pygame.draw.circle(glow_surf, glow_color, (glow_size//2, glow_size//2), int(radius * 1.6))
                    surface.blit(glow_surf, (int(screen_x - glow_size//2), int(screen_y - glow_size//2)))
                except: pass

            # Main planet body
            pygame.draw.circle(surface, self.color, (int(screen_x), int(screen_y)), radius)

            # Surface pattern (cheap): spots or stripes - use pre-cached pattern data
            if (not self.is_star) and getattr(self, 'pattern_type', 'none') != 'none':
                try:
                    patt_size = max(6, int(radius * 2))
                    patt_surf = pygame.Surface((patt_size, patt_size), pygame.SRCALPHA)
                    if self.pattern_type == 'spots':
                        # Use pre-cached spot positions (fixed per planet)
                        pattern_spots = getattr(self, 'pattern_spots', [])
                        for sx_ratio, sy_ratio, sr_ratio in pattern_spots:
                            sx = int(patt_size * sx_ratio)
                            sy = int(patt_size * sy_ratio)
                            sr = max(1, int(radius * sr_ratio))
                            spot_col = (self.pattern_color[0], self.pattern_color[1], self.pattern_color[2], 160)
                            pygame.draw.circle(patt_surf, spot_col, (sx, sy), sr)
                    elif self.pattern_type == 'stripes':
                        stripe_col = (self.pattern_color[0], self.pattern_color[1], self.pattern_color[2], 120)
                        stripe_h = max(1, int(patt_size * 0.12))
                        for i in range(-1, 2):
                            ry = patt_size//2 + i * stripe_h * 2
                            pygame.draw.rect(patt_surf, stripe_col, pygame.Rect(0, ry, patt_size, stripe_h))
                    surface.blit(patt_surf, (int(screen_x - patt_size//2), int(screen_y - patt_size//2)))
                except Exception:
                    pass

            # For planets (not stars) draw a thin tilted ring/ellipse around them
            if not self.is_star and getattr(self, 'ring_visible', True):
                ring_w = max(4, int(radius * 3.2))
                ring_h = max(2, int(radius * 0.9))
                try:
                    ring_surf_w = ring_w + 12
                    ring_surf_h = ring_h + 12
                    ring_surf = pygame.Surface((ring_surf_w, ring_surf_h), pygame.SRCALPHA)
                    base_ring = getattr(self, 'ring_color', (200, 200, 200))
                    ring_color = (base_ring[0], base_ring[1], base_ring[2], 200)
                    ring_rect = pygame.Rect(6, 6, ring_w, ring_h)
                    ring_thickness = max(1, int(radius * 0.16))
                    pygame.draw.ellipse(ring_surf, ring_color, ring_rect, ring_thickness)
                    # rotate the ring surface by a per-planet angle
                    angle = getattr(self, 'ring_angle', 0.0)
                    rotated = pygame.transform.rotate(ring_surf, angle)
                    rx = int(screen_x - rotated.get_width() // 2)
                    ry = int(screen_y - rotated.get_height() // 2 + int(radius * 0.25))
                    surface.blit(rotated, (rx, ry))
                except Exception:
                    ring_color_fallback = getattr(self, 'ring_color', (200, 200, 200))
                    ring_x = int(screen_x - ring_w // 2)
                    ring_y = int(screen_y - ring_h // 2 + radius * 0.25)
                    ring_rect_f = pygame.Rect(ring_x, ring_y, ring_w, ring_h)
                    ring_thickness = max(1, int(radius * 0.16))
                    pygame.draw.ellipse(surface, ring_color_fallback, ring_rect_f, ring_thickness)

            # Selection highlight
            if self.selected:
                pygame.draw.circle(surface, WHITE, (int(screen_x), int(screen_y)), radius + 2, 1)

            # Worker indicator: small green triangle to the right of the planet when workers assigned
            if (not self.is_star) and getattr(self, 'assigned_workers', 0) > 0:
                try:
                    tri_size = max(4, int(radius * 0.7))
                    tx, ty = int(screen_x), int(screen_y_fixed)  # 使用固定y坐标
                    pts = [(tx + radius + tri_size, ty - tri_size), (tx + radius, ty), (tx + radius + tri_size, ty + tri_size)]
                    pygame.draw.polygon(surface, WORKER_GREEN, pts)
                    pygame.draw.polygon(surface, BLACK, pts, 1)
                except: pass

            # Fleet indicator: small black triangle above the body when it has ships
            if getattr(self, 'fleet_count', 0) > 0:
                try:
                    tri_size = max(3, int(radius * 0.6))
                    tx, ty = int(screen_x), int(screen_y_fixed)  # 使用固定y坐标
                    # Triangle pointing up above the body
                    pts = [(tx, ty - radius - tri_size), (tx - tri_size, ty - radius), (tx + tri_size, ty - radius)]
                    pygame.draw.polygon(surface, BLACK, pts)
                except: pass

    def contains_point(self, x, y, camera_x, camera_y, zoom):
        screen_x = (self.x - camera_x) * zoom + W//2
        screen_y = (self.y - camera_y) * zoom + H//2
        dist = math.sqrt((x - screen_x)**2 + (y - screen_y)**2)
        return dist <= self.radius * zoom

# 移动中的舰队类
class MovingFleet:
    """表示正在星体间移动的舰队"""
    def __init__(self, start_body, end_body, ship_count):
        self.start_body = start_body
        self.end_body = end_body
        self.ship_count = ship_count
        # 起点和终点世界坐标
        self.start_x = start_body.x
        self.start_y = start_body.y
        self.end_x = end_body.x
        self.end_y = end_body.y
        # 当前位置（0.0 = 起点，1.0 = 终点）
        self.progress = 0.0
        # 速度：每秒移动的进度（0.2 = 5秒到达）
        self.speed = 0.2
        
    def update(self, dt):
        """更新舰队位置，dt为时间增量（秒）"""
        self.progress += self.speed * dt
        return self.progress >= 1.0  # 返回是否到达目的地
    
    def get_position(self):
        """获取当前世界坐标"""
        x = self.start_x + (self.end_x - self.start_x) * self.progress
        y = self.start_y + (self.end_y - self.start_y) * self.progress
        return x, y
    
    def draw(self, surface, camera_x, camera_y, zoom):
        """绘制移动中的舰队（黑色三角形）"""
        x, y = self.get_position()
        screen_x = (x - camera_x) * zoom + W//2
        screen_y = (y - camera_y) * zoom + H//2
        
        # 只在屏幕内绘制
        if 0 <= screen_x <= W and 0 <= screen_y <= H:
            tri_size = max(4, int(6 * zoom))
            tx, ty = int(screen_x), int(screen_y)
            # 计算移动方向的角度，让三角形指向移动方向
            angle = math.atan2(self.end_y - self.start_y, self.end_x - self.start_x)
            # 三角形顶点（指向右侧，需要旋转）
            pts_base = [(tri_size, 0), (-tri_size//2, -tri_size), (-tri_size//2, tri_size)]
            # 旋转顶点
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            pts = []
            for px, py in pts_base:
                rx = px * cos_a - py * sin_a + tx
                ry = px * sin_a + py * cos_a + ty
                pts.append((int(rx), int(ry)))
            pygame.draw.polygon(surface, BLACK, pts)

# 星系类
class StarSystem:
    def __init__(self, x, y, star_name):
        self.star = CelestialBody(x, y, is_star=True, star_name=star_name)
        self.planets = []
        self.connections = []  # 存储连接路径 (body1, body2)
        
        # 生成6-12个行星（增加行星数量）
        num_planets = random.randint(6, 12)
        max_attempts = 100  # 每个行星最多尝试100次放置
        
        # 准备字母列表，确保不重复
        available_letters = list(LETTERS)
        random.shuffle(available_letters)
        planet_index = 0
        
        for _ in range(num_planets):
            placed = False
            for attempt in range(max_attempts):
                # 在恒星周围随机生成行星，距离在50-200之间
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(50, 200)
                planet_x = x + math.cos(angle) * distance
                planet_y = y + math.sin(angle) * distance
                
                # 检查与已有行星的距离（最小距离30像素）
                min_planet_distance = 30
                too_close = False
                for existing_planet in self.planets:
                    dist = math.hypot(planet_x - existing_planet.x, planet_y - existing_planet.y)
                    if dist < min_planet_distance:
                        too_close = True
                        break
                
                # 如果距离足够，放置行星
                if not too_close:
                    # 使用不重复的字母
                    letter = available_letters[planet_index % len(available_letters)]
                    self.planets.append(CelestialBody(planet_x, planet_y, star_name=star_name, planet_letter=letter))
                    planet_index += 1
                    placed = True
                    break
            
            # 如果尝试多次都失败，放宽距离要求再试一次
            if not placed:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(50, 200)
                planet_x = x + math.cos(angle) * distance
                planet_y = y + math.sin(angle) * distance
                letter = available_letters[planet_index % len(available_letters)]
                self.planets.append(CelestialBody(planet_x, planet_y, star_name=star_name, planet_letter=letter))
                planet_index += 1
        
        # 使用最小生成树确保所有星体连通（Prim算法）
        # 将恒星和所有行星作为图的节点
        all_bodies = [self.star] + self.planets
        if len(all_bodies) <= 1:
            return
        
        # Prim算法：从恒星开始
        in_tree = {self.star}
        not_in_tree = set(self.planets)
        
        while not_in_tree:
            # 找到树内节点到树外节点的最短边
            min_dist = float('inf')
            best_from = None
            best_to = None
            
            for body_in in in_tree:
                for body_out in not_in_tree:
                    dist = math.hypot(body_in.x - body_out.x, body_in.y - body_out.y)
                    if dist < min_dist:
                        min_dist = dist
                        best_from = body_in
                        best_to = body_out
            
            # 添加最短边
            if best_from and best_to:
                self.connections.append((best_from, best_to))
                in_tree.add(best_to)
                not_in_tree.remove(best_to)
        
        # 可选：添加少量额外连接以增加路径选择（5%概率）
        for i in range(len(all_bodies)):
            for j in range(i + 1, len(all_bodies)):
                body1, body2 = all_bodies[i], all_bodies[j]
                conn = (body1, body2)
                rev = (body2, body1)
                # 如果这条边不存在，且随机概率满足，添加它
                if conn not in self.connections and rev not in self.connections:
                    if random.random() < 0.05:
                        self.connections.append(conn)

    def draw(self, surface, camera_x, camera_y, zoom):
        # 先绘制连接线（在星体下方）
        for body1, body2 in self.connections:
            screen_x1 = (body1.x - camera_x) * zoom + W//2
            screen_y1 = (body1.y - camera_y) * zoom + H//2
            screen_x2 = (body2.x - camera_x) * zoom + W//2
            screen_y2 = (body2.y - camera_y) * zoom + H//2
            
            # 只绘制至少有一个端点在屏幕范围内的线
            if ((0 <= screen_x1 <= W and 0 <= screen_y1 <= H) or 
                (0 <= screen_x2 <= W and 0 <= screen_y2 <= H)):
                # 淡白色细线
                pale_white = (200, 200, 200)
                pygame.draw.line(surface, pale_white, 
                               (int(screen_x1), int(screen_y1)), 
                               (int(screen_x2), int(screen_y2)), 1)
        
        # 然后绘制星体（在连接线上方）
        self.star.draw(surface, camera_x, camera_y, zoom)
        for planet in self.planets:
            planet.draw(surface, camera_x, camera_y, zoom)

    def get_body_at(self, x, y, camera_x, camera_y, zoom):
        if self.star.contains_point(x, y, camera_x, camera_y, zoom):
            return self.star
        for planet in self.planets:
            if planet.contains_point(x, y, camera_x, camera_y, zoom):
                return planet
        return None

# 游戏世界类
class GameWorld:
    def __init__(self, scale='large'):
        """
        初始化游戏世界
        scale: 'small' (小宇宙：3个星系) 或 'large' (大宇宙：20个星系)
        """
        self.scale = scale
        self.systems = []
        self.inter_system_connections = []  # 存储恒星系间的连接 (planet1, planet2)
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.selected_body = None
        self.dragging = False
        self.last_mouse_pos = None
        
        # 游戏资源 - 玩家全局资源
        self.player_food = 20  # 初始20食物
        self.workers = 0  # 工人数量
        self.player_usd = 500  # 初始货币
        # 玩家额外的集中库存（用于买入的矿物会放到这里）
        self.player_stock = {'Gold': 0, 'Silver': 0, 'Rare Earth': 0, 'Copper': 0, 'Aluminum': 0}
        # 单位目录（引用全局目录，方便后续在界面或购买逻辑中使用）
        self.unit_catalog = UNIT_CATALOG
        # 玩家拥有的单位实例列表（每个单位是一个字典，包含 type, category, hp, attack 等）
        self.player_units = []
        # 是否显示当前星球的已开采弹窗
        self.show_mined_popup = False
        self.mined_popup_body = None
        # 是否显示全局矿物总数弹窗
        self.show_ore_popup = False
        self._ore_popup_totals = None
        # 是否显示单位购买弹窗
        self.show_unit_popup = False
        # 是否显示舰队派遣弹窗
        self.show_fleet_popup = False
        self.fleet_popup_source = None
        # 交易界面状态
        self.show_trade_popup = False
        self.trade_view = None  # None, 'buy', 'sell'
        # 交易价格基础与当前实时价格（波动范围±50%）
        self.trade_price_base = {
            'Gold': 50.0,
            'Silver': 20.0,
            'Food': 2.0,
            'Worker': 4.0
        }
        self.current_trade_prices = self.trade_price_base.copy()
        self._last_price_update = time.time()
        
        # 移动中的舰队列表
        self.moving_fleets = []
        
        self.generate_systems()
        self.generate_inter_system_connections()  # 生成恒星系间连接
        
        # 初始化玩家起始星球（随机选择一个行星）
        self.initialize_player_start()

    def generate_systems(self):
        # 根据规模决定星系数量和生成范围
        if self.scale == 'small':
            num_systems = 3  # 小宇宙：3个星系
            range_limit = 400  # 生成范围：±400
            min_distance = 200  # 最小距离：200
        else:  # 'large'
            num_systems = 20  # 大宇宙：20个星系
            range_limit = 1500  # 生成范围：±1500
            min_distance = 300  # 最小距离：300
        
        available_names = (STAR_NAMES * 3)[:num_systems]  # 扩展名字列表
        random.shuffle(available_names)

        # 在指定区域内生成星系
        for i in range(num_systems):
            while True:
                x = random.uniform(-range_limit, range_limit)
                y = random.uniform(-range_limit, range_limit)
                # 确保星系之间有足够距离
                if all(math.hypot(x - sys.star.x, y - sys.star.y) > min_distance for sys in self.systems):
                    self.systems.append(StarSystem(x, y, available_names[i]))
                    break
    
    def initialize_player_start(self):
        """初始化玩家起始星球：随机选择一个行星，给予10艘舰船"""
        # 收集所有行星（不包括恒星）
        all_planets = []
        for system in self.systems:
            all_planets.extend(system.planets)
        
        if all_planets:
            # 随机选择一个行星作为玩家起始星球
            start_planet = random.choice(all_planets)
            start_planet.owner = 'player'
            start_planet.fleet_count = 10
            
            # 将摄像机移动到起始星球
            self.camera_x = start_planet.x
            self.camera_y = start_planet.y
            
            print(f"玩家起始星球: {start_planet.name}, 位置: ({start_planet.x:.0f}, {start_planet.y:.0f})")
    
    def get_player_owned_bodies(self):
        """获取玩家拥有的所有星体"""
        owned = []
        for system in self.systems:
            if system.star.owner == 'player':
                owned.append(system.star)
            for planet in system.planets:
                if planet.owner == 'player':
                    owned.append(planet)
        return owned
    
    def get_visible_bodies(self):
        """获取玩家可见的所有星体（已拥有的+相邻的）"""
        owned = set(self.get_player_owned_bodies())
        visible = set(owned)
        
        # 添加所有与已拥有星体相邻的星体
        for body in owned:
            adjacent = self.get_adjacent_bodies(body)
            visible.update(adjacent)
        
        return visible
    
    def get_visible_connections(self):
        """获取玩家可见的连接线（连接两个可见星体的线）"""
        visible_bodies = self.get_visible_bodies()
        visible_conns = []
        
        # 星系内连接
        for system in self.systems:
            for conn in system.connections:
                if conn[0] in visible_bodies and conn[1] in visible_bodies:
                    visible_conns.append(conn)
        
        # 星系间连接
        for conn in self.inter_system_connections:
            if conn[0] in visible_bodies and conn[1] in visible_bodies:
                visible_conns.append(conn)
        
        return visible_conns
    
    def draw_body_gray(self, body, surface, camera_x, camera_y, zoom):
        """绘制灰色的未拥有星体（简化版）"""
        screen_x = (body.x - camera_x) * zoom + W//2
        screen_y_fixed = (body.y - camera_y) * zoom + H//2
        
        if 0 <= screen_x <= W and 0 <= screen_y_fixed <= H:
            radius = max(2, int(body.radius * zoom))
            # 灰色圆形
            gray_color = (120, 120, 120)
            pygame.draw.circle(surface, gray_color, (int(screen_x), int(screen_y_fixed)), radius)
            # 边框
            pygame.draw.circle(surface, (80, 80, 80), (int(screen_x), int(screen_y_fixed)), radius, 1)

    def generate_inter_system_connections(self):
        """使用最小生成树确保所有星系连通，同时减少连接线密度"""
        if len(self.systems) <= 1:
            return
        
        # 构建所有星系的所有星体列表（用于后续选择最佳连接点）
        system_bodies = {}
        for system in self.systems:
            system_bodies[system] = [system.star] + system.planets
        
        # 使用Prim算法在星系级别构建最小生成树
        in_tree = {self.systems[0]}
        not_in_tree = set(self.systems[1:])
        
        while not_in_tree:
            # 找到树内星系到树外星系的最短连接
            min_dist = float('inf')
            best_sys1 = None
            best_sys2 = None
            best_body1 = None
            best_body2 = None
            
            for sys1 in in_tree:
                for sys2 in not_in_tree:
                    # 找到两个星系之间的最佳连接点（最短距离）
                    for body1 in system_bodies[sys1]:
                        for body2 in system_bodies[sys2]:
                            dist = math.hypot(body1.x - body2.x, body1.y - body2.y)
                            if dist < min_dist:
                                min_dist = dist
                                best_sys1 = sys1
                                best_sys2 = sys2
                                best_body1 = body1
                                best_body2 = body2
            
            # 添加最短连接
            if best_body1 and best_body2:
                conn = (best_body1, best_body2)
                rev = (best_body2, best_body1)
                if conn not in self.inter_system_connections and rev not in self.inter_system_connections:
                    self.inter_system_connections.append(conn)
                in_tree.add(best_sys2)
                not_in_tree.remove(best_sys2)
        
        # 可选：添加极少量额外连接（2%概率），避免过于稀疏
        for i in range(len(self.systems)):
            for j in range(i + 1, len(self.systems)):
                if random.random() < 0.02:  # 降低概率从之前的多条连接到2%
                    sys1 = self.systems[i]
                    sys2 = self.systems[j]
                    # 找最短连接点
                    min_dist = float('inf')
                    best_a = None
                    best_b = None
                    for a in system_bodies[sys1]:
                        for b in system_bodies[sys2]:
                            dist = math.hypot(a.x - b.x, a.y - b.y)
                            if dist < min_dist:
                                min_dist = dist
                                best_a = a
                                best_b = b
                    if best_a and best_b:
                        conn = (best_a, best_b)
                        rev = (best_b, best_a)
                        if conn not in self.inter_system_connections and rev not in self.inter_system_connections:
                            self.inter_system_connections.append(conn)

    def create_inter_system_links(self, system1, system2):
        # 这个方法现在不再使用，但保留以防其他代码引用
        pass
    
    def handle_fleet_arrival(self, fleet):
        """处理舰队到达目的地的逻辑"""
        target = fleet.end_body
        attacker_owner = 'player'  # 目前只有玩家派遣舰队，后续可扩展
        
        if target.owner is None:
            # 情况1: 未被占领的中立星球 - 需要时间占领
            if not target.under_siege:
                # 开始占领
                target.under_siege = True
                target.siege_start_time = time.time()
                target.siege_duration = 10  # 占领中立星球需要10秒
                target.attacker_owner = attacker_owner
                target.attacker_count = fleet.ship_count
                target.defender_count = 0
                print(f"开始占领中立星球: {target.name}")
            else:
                # 已经有舰队在占领，增加进攻方兵力
                target.attacker_count += fleet.ship_count
                
        elif target.owner == attacker_owner:
            # 情况2: 己方星球 - 直接增援
            target.fleet_count += fleet.ship_count
            print(f"增援己方星球: {target.name}, 现有 {target.fleet_count} 艘舰船")
            
        else:
            # 情况3: 敌方星球 - 战斗或开始围攻
            if not target.under_siege:
                # 计算战斗时长
                attacker_power = fleet.ship_count
                defender_power = target.fleet_count
                
                if defender_power == 0:
                    # 敌方星球无驻军，开始占领
                    target.under_siege = True
                    target.siege_start_time = time.time()
                    target.siege_duration = 10  # 空星球占领需要10秒
                    target.attacker_owner = attacker_owner
                    target.attacker_count = attacker_power
                    target.defender_count = 0
                    print(f"开始占领敌方空星球: {target.name}")
                else:
                    # 有敌军驻守，开始战斗
                    power_ratio = max(attacker_power, defender_power) / min(attacker_power, defender_power)
                    # 战斗时长：基础20秒，根据战力差距调整（差距越大越快）
                    # 最快5秒（悬殊10倍以上），最慢20秒（势均力敌）
                    base_duration = 20
                    min_duration = 5
                    if power_ratio >= 10:
                        battle_duration = min_duration
                    else:
                        # 线性插值: ratio 1->20秒, ratio 10->5秒
                        battle_duration = base_duration - (power_ratio - 1) / 9 * (base_duration - min_duration)
                    
                    target.under_siege = True
                    target.siege_start_time = time.time()
                    target.siege_duration = battle_duration
                    target.attacker_owner = attacker_owner
                    target.attacker_count = attacker_power
                    target.defender_count = defender_power
                    print(f"开始战斗: {target.name}, 攻方{attacker_power} vs 守方{defender_power}, 预计{battle_duration:.1f}秒")
            else:
                # 已经在战斗中，增加进攻方兵力
                target.attacker_count += fleet.ship_count
    
    def update_sieges(self):
        """更新所有正在围攻/战斗中的星球"""
        current_time = time.time()
        
        for system in self.systems:
            # 检查恒星
            if system.star.under_siege:
                self.update_single_siege(system.star, current_time)
            
            # 检查行星
            for planet in system.planets:
                if planet.under_siege:
                    self.update_single_siege(planet, current_time)
    
    def update_single_siege(self, body, current_time):
        """更新单个星球的围攻/战斗状态"""
        elapsed = current_time - body.siege_start_time
        
        if elapsed >= body.siege_duration:
            # 战斗/占领结束
            if body.defender_count == 0:
                # 没有防守方，直接占领
                body.owner = body.attacker_owner
                body.fleet_count = body.attacker_count
                print(f"占领完成: {body.name}, {body.attacker_count} 艘舰船驻扎")
            else:
                # 有战斗，计算结果
                if body.attacker_count > body.defender_count:
                    # 进攻方胜利
                    remaining = body.attacker_count - body.defender_count
                    body.owner = body.attacker_owner
                    body.fleet_count = remaining
                    print(f"战斗胜利: {body.name}, 剩余 {remaining} 艘舰船")
                elif body.defender_count > body.attacker_count:
                    # 防守方胜利
                    remaining = body.defender_count - body.attacker_count
                    body.fleet_count = remaining
                    print(f"战斗失败: {body.name}, 敌方剩余 {remaining} 艘舰船")
                else:
                    # 同归于尽
                    body.fleet_count = 0
                    print(f"同归于尽: {body.name}, 双方全灭")
            
            # 重置围攻状态
            body.under_siege = False
            body.siege_start_time = None
            body.siege_duration = 0
            body.attacker_owner = None
            body.attacker_count = 0
            body.defender_count = 0
    
    def convex_hull(self, points):
        """计算凸包（Graham扫描算法）"""
        if len(points) < 3:
            return points
        
        # 找到最下面的点（y最小，相同则x最小）
        start = min(points, key=lambda p: (p[1], p[0]))
        
        # 按极角排序
        def polar_angle(p):
            dx = p[0] - start[0]
            dy = p[1] - start[1]
            return math.atan2(dy, dx)
        
        sorted_points = sorted([p for p in points if p != start], key=polar_angle)
        sorted_points.insert(0, start)
        
        # Graham扫描
        hull = []
        for p in sorted_points:
            while len(hull) > 1:
                # 检查是否向左转
                o = hull[-2]
                a = hull[-1]
                cross = (a[0] - o[0]) * (p[1] - o[1]) - (a[1] - o[1]) * (p[0] - o[0])
                if cross <= 0:
                    hull.pop()
                else:
                    break
            hull.append(p)
        
        return hull
    
    def draw_territory_borders(self, surface, owned_bodies):
        """绘制玩家领土边界 - 使用圆形区域合并和平滑曲线"""
        # 收集所有玩家占领星球的坐标和半径
        player_planets = []
        for body in owned_bodies:
            if body.owner == 'player':
                # 每个星球周围创建一个影响圆，半径根据星球大小确定
                radius = 60 if body.is_star else 40  # 恒星影响范围更大
                player_planets.append((body.x, body.y, radius))
        
        if len(player_planets) < 1:
            return
        
        # 如果只有1-2个星球，绘制简单的圆形
        if len(player_planets) <= 2:
            for x, y, r in player_planets:
                screen_x = (x - self.camera_x) * self.zoom + W//2
                screen_y = (y - self.camera_y) * self.zoom + H//2
                screen_r = int(r * self.zoom)
                
                # 绘制半透明圆形
                temp_surface = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.circle(temp_surface, (100, 150, 255, 30), (int(screen_x), int(screen_y)), screen_r)
                surface.blit(temp_surface, (0, 0))
                pygame.draw.circle(surface, (100, 150, 255, 120), (int(screen_x), int(screen_y)), screen_r, 2)
            return
        
        # 对于多个星球，生成边界轮廓点
        # 策略：在每个星球周围生成圆周上的点，然后找到外围轮廓
        all_boundary_points = []
        angle_step = math.pi / 8  # 每45度采样一个点
        
        for planet_x, planet_y, radius in player_planets:
            for i in range(16):  # 每个圆周采样16个点
                angle = i * angle_step
                px = planet_x + math.cos(angle) * radius
                py = planet_y + math.sin(angle) * radius
                all_boundary_points.append((px, py))
        
        # 如果点数太少，直接返回
        if len(all_boundary_points) < 3:
            return
        
        # 计算这些点的凸包
        try:
            hull_points = self.convex_hull(all_boundary_points)
        except:
            return
        
        if len(hull_points) < 3:
            return
        
        # 平滑凸包边界：在每对相邻点之间插入曲线控制点
        smooth_points = []
        n = len(hull_points)
        for i in range(n):
            p1 = hull_points[i]
            p2 = hull_points[(i + 1) % n]
            
            # 添加当前点
            smooth_points.append(p1)
            
            # 在两点之间添加3个插值点，形成平滑曲线
            for t in [0.25, 0.5, 0.75]:
                interp_x = p1[0] * (1 - t) + p2[0] * t
                interp_y = p1[1] * (1 - t) + p2[1] * t
                # 稍微向外凸出，创造曲线效果
                center_x = sum(p[0] for p in hull_points) / n
                center_y = sum(p[1] for p in hull_points) / n
                dx = interp_x - center_x
                dy = interp_y - center_y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    # 向外扩展5%
                    bulge_factor = 1.05
                    smooth_x = center_x + dx * bulge_factor
                    smooth_y = center_y + dy * bulge_factor
                    smooth_points.append((smooth_x, smooth_y))
        
        # 转换到屏幕坐标
        screen_points = []
        for x, y in smooth_points:
            screen_x = (x - self.camera_x) * self.zoom + W//2
            screen_y = (y - self.camera_y) * self.zoom + H//2
            screen_points.append((screen_x, screen_y))
        
        # 绘制半透明填充区域和边界线
        if len(screen_points) >= 3:
            try:
                # 创建半透明表面
                temp_surface = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.polygon(temp_surface, (100, 150, 255, 30), screen_points)  # 淡蓝色，透明度30
                surface.blit(temp_surface, (0, 0))
                
                # 绘制边界线（更明显的颜色）
                pygame.draw.lines(surface, (100, 150, 255, 120), True, screen_points, 2)
            except:
                pass  # 如果点太少或有其他问题，跳过绘制

    def draw(self, surface):
        # draw background if available
        if 'BACKGROUND_SURFACE' in globals() and BACKGROUND_SURFACE is not None:
            try:
                surface.blit(BACKGROUND_SURFACE, (0, 0))
            except:
                pass
        
        # 获取可见的星体和连接线
        visible_bodies = self.get_visible_bodies()
        visible_connections = self.get_visible_connections()
        owned_bodies = set(self.get_player_owned_bodies())
        
        # 绘制玩家星域边界（在连接线之前，作为背景）
        self.draw_territory_borders(surface, owned_bodies)
        
        # 绘制可见的连接线
        pale_blue = (150, 180, 220)
        for a, b in visible_connections:
            x1 = (a.x - self.camera_x) * self.zoom + W//2
            y1 = (a.y - self.camera_y) * self.zoom + H//2
            x2 = (b.x - self.camera_x) * self.zoom + W//2
            y2 = (b.y - self.camera_y) * self.zoom + H//2
            if ((0 <= x1 <= W and 0 <= y1 <= H) or (0 <= x2 <= W and 0 <= y2 <= H) or
                (x1 < 0 and x2 > W) or (x1 > W and x2 < 0) or (y1 < 0 and y2 > H) or (y1 > H and y2 < 0)):
                pygame.draw.line(surface, pale_blue, (int(x1), int(y1)), (int(x2), int(y2)), 1)

        # 绘制可见的星体
        for system in self.systems:
            # 绘制恒星（如果可见）
            if system.star in visible_bodies:
                # 如果是已拥有的，正常绘制；如果是未拥有的，绘制为灰色
                if system.star in owned_bodies:
                    system.star.draw(surface, self.camera_x, self.camera_y, self.zoom)
                else:
                    self.draw_body_gray(system.star, surface, self.camera_x, self.camera_y, self.zoom)
            
            # 绘制行星（如果可见）
            for planet in system.planets:
                if planet in visible_bodies:
                    if planet in owned_bodies:
                        planet.draw(surface, self.camera_x, self.camera_y, self.zoom)
                    else:
                        self.draw_body_gray(planet, surface, self.camera_x, self.camera_y, self.zoom)

        # 更新并绘制移动中的舰队
        frame_time = 1.0 / 60.0
        fleets_to_remove = []
        for fleet in self.moving_fleets:
            if fleet.update(frame_time):
                # 舰队到达目的地，开始战斗/占领逻辑
                self.handle_fleet_arrival(fleet)
                fleets_to_remove.append(fleet)
            else:
                # 绘制移动中的舰队
                fleet.draw(surface, self.camera_x, self.camera_y, self.zoom)
        
        # 移除已到达的舰队
        for fleet in fleets_to_remove:
            self.moving_fleets.remove(fleet)
        
        # 更新所有正在围攻/占领中的星球
        self.update_sieges()

        # 更新工人挖矿（每帧消耗食物，每帧生成矿物）
        # 假设每帧是1/60秒
        frame_time = 1.0 / 60.0
        
        # 工人食物消耗
        food_consumption_per_frame = self.workers * 5 / (24 * 60 * 60)  # 5食物/天，转换为每帧
        self.player_food = max(0, self.player_food - food_consumption_per_frame)
        
        # 工人挖矿
        for system in self.systems:
            for planet in system.planets:
                if not planet.is_star and planet.assigned_workers > 0:
                    # 计算这一帧挖的总矿物量
                    total_mining_amount = planet.assigned_workers * planet.mining_rate * frame_time
                    
                    # 根据星球的矿物储量比例随机分配到各种矿物
                    # 计算每种矿物的相对比例
                    total_ore = sum(planet.ore_reserves.values())
                    if total_ore > 0:
                        for ore_type in planet.ore_reserves:
                            ore_ratio = planet.ore_reserves[ore_type] / total_ore
                            mining_for_this_ore = total_mining_amount * ore_ratio
                            planet.mined_ore[ore_type] += mining_for_this_ore
        
        # 区划资源生产系统
        for system in self.systems:
            for planet in system.planets:
                if not planet.is_star and planet.owner == 'player':
                    # 城市区划：每个城市每天产生 0.5 个工人
                    # 1天 = 86400秒，每帧 = 1/60秒
                    # 每帧每个城市产生 0.5 / 86400 个工人
                    worker_production = planet.city_districts * 0.5 / 86400 * frame_time
                    self.workers += worker_production
                    
                    # 农业区划：每个农业每天产生 10 食物
                    food_production = planet.agri_districts * 10 / 86400 * frame_time
                    self.player_food += food_production
                    
                    # 工业区划：尝试建造舰船
                    # 每个工业每30秒建造1艘舰船，需要消耗 5 金属 + 2 稀土
                    ships_per_second = planet.industrial_districts / 30.0
                    ships_this_frame = ships_per_second * frame_time
                    
                    # 每艘舰船需要的资源
                    metal_per_ship = 5  # 需要5单位金属（Gold/Silver/Copper/Aluminum任意组合）
                    rare_earth_per_ship = 2  # 需要2单位稀土
                    
                    # 检查是否有足够资源
                    available_metal = planet.mined_ore.get('Gold', 0) + planet.mined_ore.get('Silver', 0) + \
                                     planet.mined_ore.get('Copper', 0) + planet.mined_ore.get('Aluminum', 0)
                    available_rare_earth = planet.mined_ore.get('Rare Earth', 0)
                    
                    # 计算可以建造多少艘
                    can_build_metal = available_metal / metal_per_ship
                    can_build_rare = available_rare_earth / rare_earth_per_ship
                    max_can_build = min(can_build_metal, can_build_rare, ships_this_frame)
                    
                    if max_can_build > 0:
                        # 消耗资源
                        metal_needed = max_can_build * metal_per_ship
                        rare_needed = max_can_build * rare_earth_per_ship
                        
                        # 按比例从各种金属中扣除
                        if available_metal > 0:
                            for metal_type in ['Gold', 'Silver', 'Copper', 'Aluminum']:
                                metal_ratio = planet.mined_ore.get(metal_type, 0) / available_metal
                                planet.mined_ore[metal_type] -= metal_needed * metal_ratio
                        
                        # 扣除稀土
                        planet.mined_ore['Rare Earth'] -= rare_needed
                        
                        # 增加舰船
                        planet.fleet_count += int(max_can_build)
                        if random.random() < (max_can_build - int(max_can_build)):
                            planet.fleet_count += 1  # 概率性增加不足1的部分

        
        # Draw player resource bar at the top
        resource_bar_height = 50
        resource_surface = pygame.Surface((W, resource_bar_height))
        resource_surface.fill(BLACK)
        resource_surface.set_alpha(200)
        surface.blit(resource_surface, (0, 0))
        
        # Draw player food and workers status
        food_text = f"Food: {int(self.player_food)}"
        workers_text = f"Available Workers: {int(self.workers)}"  # 只显示整数部分
        
        food_surf = font_small.render(food_text, True, (100, 200, 100))  # 绿色
        workers_surf = font_small.render(workers_text, True, YELLOW)
        
        surface.blit(food_surf, (10, 8))
        surface.blit(workers_surf, (10, 28))
        
        # Draw "Buy Worker" button (costs 5 food) - button style instead of plain text
        buy_worker_btn_w = 200
        buy_worker_btn_h = 34
        buy_worker_btn_x = W - 520
        buy_worker_btn_y = 8
        buy_worker_btn_rect = pygame.Rect(buy_worker_btn_x, buy_worker_btn_y, buy_worker_btn_w, buy_worker_btn_h)
        can_afford = self.player_food >= 5
        # Change button color based on affordability
        btn_color = (60, 120, 60) if can_afford else (80, 80, 80)
        pygame.draw.rect(surface, btn_color, buy_worker_btn_rect)
        pygame.draw.rect(surface, WHITE, buy_worker_btn_rect, 2)  # white border
        buy_worker_text = "Buy Worker (5 Food)"
        surface.blit(font_small.render(buy_worker_text, True, WHITE), (buy_worker_btn_x + 10, buy_worker_btn_y + 8))
        self._buy_worker_rect = buy_worker_btn_rect
        
        # Draw "Ores" button on the top bar (opens global ores totals popup)
        ores_btn_w = 100
        ores_btn_h = 34
        ores_btn_x = W - 110
        ores_btn_y = 8
        ores_btn_rect = pygame.Rect(ores_btn_x, ores_btn_y, ores_btn_w, ores_btn_h)
        pygame.draw.rect(surface, (60, 60, 90), ores_btn_rect)
        pygame.draw.rect(surface, WHITE, ores_btn_rect, 2)  # white border
        surface.blit(font_small.render('Ores', True, WHITE), (ores_btn_x + 28, ores_btn_y + 8))
        # store rect for click handling
        self._ores_button_rect = ores_btn_rect
        # Draw "Trade" button to the left of Ores
        trade_btn_w = 100
        trade_btn_h = 34
        trade_btn_x = ores_btn_x - trade_btn_w - 6
        trade_btn_y = ores_btn_y
        trade_btn_rect = pygame.Rect(trade_btn_x, trade_btn_y, trade_btn_w, trade_btn_h)
        pygame.draw.rect(surface, (80, 60, 90), trade_btn_rect)
        pygame.draw.rect(surface, WHITE, trade_btn_rect, 2)  # white border
        surface.blit(font_small.render('Trade', True, WHITE), (trade_btn_x + 22, trade_btn_y + 8))
        self._trade_button_rect = trade_btn_rect
        
        # Draw "Units" button to the left of Trade
        units_btn_w = 100
        units_btn_h = 34
        units_btn_x = trade_btn_x - units_btn_w - 6
        units_btn_y = ores_btn_y
        units_btn_rect = pygame.Rect(units_btn_x, units_btn_y, units_btn_w, units_btn_h)
        pygame.draw.rect(surface, (90, 60, 60), units_btn_rect)
        pygame.draw.rect(surface, WHITE, units_btn_rect, 2)  # white border
        surface.blit(font_small.render('Units', True, WHITE), (units_btn_x + 26, units_btn_y + 8))
        self._units_button_rect = units_btn_rect

        # draw selected info panel
        if self.selected_body:
            info_surface = pygame.Surface((W//3, H))
            info_surface.fill(WHITE)
            info_surface.set_alpha(240)
            surface.blit(info_surface, (0, 0))
            name_surf = font_medium.render(self.selected_body.name, True, BLACK)
            surface.blit(name_surf, (10, 10))
            
            # 显示舰船数量（对所有星体通用）
            fleet_count = getattr(self.selected_body, 'fleet_count', 0)
            
            # 检查是否正在战斗/占领中
            if getattr(self.selected_body, 'under_siege', False):
                # 显示战斗/占领状态
                elapsed = time.time() - self.selected_body.siege_start_time
                progress = min(100, (elapsed / self.selected_body.siege_duration) * 100)
                
                if self.selected_body.defender_count == 0:
                    # 占领中
                    status_text = f"占领中... {progress:.0f}%"
                    fleet_text = f"进攻方: {self.selected_body.attacker_count} 舰船"
                else:
                    # 战斗中
                    status_text = f"战斗中... {progress:.0f}%"
                    fleet_text = f"攻:{self.selected_body.attacker_count} vs 守:{self.selected_body.defender_count}"
                
                status_surf = font_small.render(status_text, True, RED)
                surface.blit(status_surf, (10, 45))
                fleet_surf = font_small.render(fleet_text, True, RED)
                surface.blit(fleet_surf, (10, 70))
                self._fleet_text_rect = pygame.Rect(10, 70, fleet_surf.get_width(), fleet_surf.get_height())
                y_offset = 95  # 战斗状态下，后续内容从更低位置开始
            else:
                # 正常显示
                fleet_text = f"Ships: {fleet_count}"
                fleet_color = BLUE if fleet_count > 0 else (150, 150, 150)
                fleet_surf = font_small.render(fleet_text, True, fleet_color)
                surface.blit(fleet_surf, (10, 45))
                # 存储这个文本的矩形区域用于点击检测
                self._fleet_text_rect = pygame.Rect(10, 45, fleet_surf.get_width(), fleet_surf.get_height())
                y_offset = 75  # 正常状态下的偏移
            
            if self.selected_body.is_star:
                base_text = f"Starbase Level: {self.selected_body.starbase}"
                base_surf = font_small.render(base_text, True, BLACK)
                surface.blit(base_surf, (10, y_offset))
            else:
                type_text = f"Type: {self.selected_body.planet_type.value}"
                city_text = f"City: {self.selected_body.city_districts}"
                agri_text = f"Agri: {self.selected_body.agri_districts}"
                indust_text = f"Indust: {self.selected_body.industrial_districts}"
                workers_on_planet = f"Workers: {self.selected_body.assigned_workers}"
                
                # 第一列信息 - 左上方
                surface.blit(font_small.render(type_text, True, BLACK), (10, y_offset + 5))
                surface.blit(font_small.render(city_text, True, BLACK), (10, y_offset + 35))
                surface.blit(font_small.render(agri_text, True, BLACK), (10, y_offset + 65))
                surface.blit(font_small.render(indust_text, True, BLACK), (10, y_offset + 95))
                surface.blit(font_small.render(workers_on_planet, True, BLUE), (10, y_offset + 125))
                
                # 显示该星球“盛产”标签（不显示精确上限）
                rich_text = "Rich in: " + ", ".join(self.selected_body.rich_in)
                surface.blit(font_small.render(rich_text, True, (80, 80, 200)), (10, 230))

                # 根据开采进度显示提示：过度开发 / 枯萎（不显示数值）
                initial = max(1, getattr(self.selected_body, '_initial_total_ore', 1))
                mined = sum(self.selected_body.mined_ore.values())
                remaining = max(0, initial - mined)
                pct_remaining = remaining / initial * 100.0
                warning_text = None
                if mined >= initial * 0.5:
                    warning_text = "过度开发"
                if pct_remaining <= 10.0:
                    warning_text = "枯萎"
                if warning_text:
                    # 红色/橙色提示
                    warn_color = (220, 100, 40) if warning_text == "过度开发" else (160, 60, 60)
                    surface.blit(font_small.render(warning_text, True, warn_color), (10, 260))
                
                # "View Mined" button
                view_mined_color = BLUE if sum(self.selected_body.mined_ore.values()) > 0 else (150,150,150)
                view_mined_text = "[View Mined]"
                view_mined_surf = font_small.render(view_mined_text, True, view_mined_color)
                surface.blit(view_mined_surf, (10, H - 90))

                # Dispatch and recall worker buttons - bottom
                dispatch_btn_color = BLUE if int(self.workers) > 0 else (150, 150, 150)
                recall_btn_color = BLUE if self.selected_body.assigned_workers > 0 else (150, 150, 150)
                
                dispatch_text = f"[+Dispatch]"
                recall_text = f"[-Recall]"
                
                dispatch_surf = font_small.render(dispatch_text, True, dispatch_btn_color)
                recall_surf = font_small.render(recall_text, True, recall_btn_color)
                
                # Button positions: display on separate lines at bottom
                surface.blit(dispatch_surf, (10, H - 60))
                surface.blit(recall_surf, (10, H - 30))

        # 如果开启了已开采弹窗，绘制弹窗（覆盖在界面上）
        if getattr(self, 'show_mined_popup', False) and self.mined_popup_body:
            popup_w = W // 2
            popup_h = H // 2
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            # border
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            # title
            title = f"Mined on {self.mined_popup_body.name}"
            popup_surf.blit(font_medium.render(title, True, BLACK), (10, 10))
            # list ores
            y = 50
            for ore in ['Gold','Silver','Rare Earth','Copper','Aluminum']:
                amt = int(self.mined_popup_body.mined_ore.get(ore, 0))
                line = f"{ore}: {amt}"
                popup_surf.blit(font_small.render(line, True, ORE_COLORS.get(ore, BLACK)), (10, y))
                y += 26
            # close button
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))
            surface.blit(popup_surf, (popup_x, popup_y))
            # store popup rect for click handling
            self._popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # 如果开启了全局矿物总数弹窗，绘制弹窗（覆盖在界面上）
        if getattr(self, 'show_ore_popup', False) and getattr(self, '_ore_popup_totals', None):
            popup_w = W // 2
            popup_h = H // 2
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            popup_surf.blit(font_medium.render('Global Ores', True, BLACK), (10, 10))
            y = 50
            for ore in ['Gold','Silver','Rare Earth','Copper','Aluminum']:
                amt = int(self._ore_popup_totals.get(ore, 0))
                line = f"{ore}: {amt}"
                popup_surf.blit(font_small.render(line, True, ORE_COLORS.get(ore, BLACK)), (10, y))
                y += 26
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))
            surface.blit(popup_surf, (popup_x, popup_y))
            self._ore_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._ore_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # Trade popup
        # update dynamic prices every 0.6s
        now = time.time()
        # slow price update: every 1.8s (3x slower than previous 0.6s)
        if now - self._last_price_update > 1.8:
            for k, base in self.trade_price_base.items():
                self.current_trade_prices[k] = max(0.01, base * (1.0 + random.uniform(-0.5, 0.5)))
            self._last_price_update = now

        if getattr(self, 'show_trade_popup', False):
            popup_w = int(W * 0.6)
            popup_h = int(H * 0.7)
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            popup_surf.blit(font_medium.render('Trade', True, BLACK), (10, 10))

            # Close button
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))

            # Buy / Sell selector
            buy_rect = pygame.Rect(10, 60, 120, 28)
            sell_rect = pygame.Rect(140, 60, 120, 28)
            pygame.draw.rect(popup_surf, (100,100,140), buy_rect)
            pygame.draw.rect(popup_surf, (100,100,140), sell_rect)
            popup_surf.blit(font_small.render('Buy', True, WHITE), (buy_rect.x + 38, buy_rect.y + 6))
            popup_surf.blit(font_small.render('Sell', True, WHITE), (sell_rect.x + 38, sell_rect.y + 6))
            # store selector rects for clicks (absolute coords)
            self._trade_buy_selector_rect = pygame.Rect(popup_x + buy_rect.x, popup_y + buy_rect.y, buy_rect.w, buy_rect.h)
            self._trade_sell_selector_rect = pygame.Rect(popup_x + sell_rect.x, popup_y + sell_rect.y, sell_rect.w, sell_rect.h)

            y = 100
            # If selling view, show holdings and sell buttons
            if self.trade_view == 'sell':
                popup_surf.blit(font_small.render('Holdings (sellable):', True, BLACK), (10, y))
                y += 28
                # aggregate mined ores across planets + player_stock
                totals = self.aggregate_mined_totals()
                # add player_stock
                for ore in self.player_stock:
                    totals[ore] = totals.get(ore, 0) + int(self.player_stock.get(ore, 0))
                # reset action button list
                self._trade_action_buttons = []
                for ore in ['Gold','Silver']:
                    amt = int(totals.get(ore, 0))
                    sell_price = self.current_trade_prices.get(ore, self.trade_price_base.get(ore, 0.0)) * 0.9
                    popup_surf.blit(font_small.render(f"{ore}: {amt}  Sell ${sell_price:.2f}", True, BLACK), (10, y))
                    # sell buttons: Sell 10, Sell 50, Sell All
                    b10_rect = pygame.Rect(220, y, 80, 20)
                    b50_rect = pygame.Rect(310, y, 80, 20)
                    ball_rect = pygame.Rect(400, y, 80, 20)
                    popup_surf.blit(font_small.render('[Sell 10]', True, BLUE), (b10_rect.x, b10_rect.y))
                    popup_surf.blit(font_small.render('[Sell 50]', True, BLUE), (b50_rect.x, b50_rect.y))
                    popup_surf.blit(font_small.render('[Sell All]', True, BLUE), (ball_rect.x, ball_rect.y))
                    # store absolute rects and metadata
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b10_rect.x, popup_y + b10_rect.y, b10_rect.w, b10_rect.h), 'action': 'sell', 'ore': ore, 'qty': 10})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b50_rect.x, popup_y + b50_rect.y, b50_rect.w, b50_rect.h), 'action': 'sell', 'ore': ore, 'qty': 50})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + ball_rect.x, popup_y + ball_rect.y, ball_rect.w, ball_rect.h), 'action': 'sell', 'ore': ore, 'qty': 'all'})
                    y += 28

                # food and workers
                food_sell_price = self.current_trade_prices.get('Food', self.trade_price_base.get('Food', 0.0)) * 0.9
                popup_surf.blit(font_small.render(f"Food: {int(self.player_food)}  Sell ${food_sell_price:.2f}", True, BLACK), (10, y))
                f10_rect = pygame.Rect(220, y, 80, 20)
                fall_rect = pygame.Rect(310, y, 80, 20)
                popup_surf.blit(font_small.render('[Sell 10]', True, BLUE), (f10_rect.x, f10_rect.y))
                popup_surf.blit(font_small.render('[Sell All]', True, BLUE), (fall_rect.x, fall_rect.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + f10_rect.x, popup_y + f10_rect.y, f10_rect.w, f10_rect.h), 'action': 'sell_food', 'qty': 10})
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fall_rect.x, popup_y + fall_rect.y, fall_rect.w, fall_rect.h), 'action': 'sell_food', 'qty': 'all'})
                y += 28
                worker_sell_price = self.current_trade_prices.get('Worker', self.trade_price_base.get('Worker', 0.0)) * 0.9
                popup_surf.blit(font_small.render(f"Workers (unassigned): {self.workers}  Sell ${worker_sell_price:.2f}", True, BLACK), (10, y))
                w1_rect = pygame.Rect(310, y, 70, 20)
                popup_surf.blit(font_small.render('[Sell 1]', True, BLUE), (w1_rect.x, w1_rect.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + w1_rect.x, popup_y + w1_rect.y, w1_rect.w, w1_rect.h), 'action': 'sell_worker', 'qty': 1})
                y += 28
                popup_surf.blit(font_small.render(f"USD: ${int(self.player_usd)}", True, BLACK), (10, y))

            else:
                # buy view or default - show dynamic prices and buy buttons
                popup_surf.blit(font_small.render('Buy using USD (prices fluctuate ±50%)', True, BLACK), (10, y))
                y += 28
                # prepare action list
                self._trade_action_buttons = []
                for ore in ['Gold','Silver']:
                    price = self.current_trade_prices.get(ore, 0.0)
                    popup_surf.blit(font_small.render(f"{ore}: ${price:.2f}", True, BLACK), (10, y))
                    b1 = pygame.Rect(220, y, 70, 20)
                    b5 = pygame.Rect(300, y, 70, 20)
                    popup_surf.blit(font_small.render('[Buy 1]', True, BLUE), (b1.x, b1.y))
                    popup_surf.blit(font_small.render('[Buy 5]', True, BLUE), (b5.x, b5.y))
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b1.x, popup_y + b1.y, b1.w, b1.h), 'action': 'buy', 'ore': ore, 'qty': 1})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b5.x, popup_y + b5.y, b5.w, b5.h), 'action': 'buy', 'ore': ore, 'qty': 5})
                    y += 28
                # food
                price = self.current_trade_prices.get('Food', 0.0)
                popup_surf.blit(font_small.render(f"Food: ${price:.2f}", True, BLACK), (10, y))
                fb10 = pygame.Rect(220, y, 80, 20)
                fb50 = pygame.Rect(310, y, 80, 20)
                popup_surf.blit(font_small.render('[Buy 10]', True, BLUE), (fb10.x, fb10.y))
                popup_surf.blit(font_small.render('[Buy 50]', True, BLUE), (fb50.x, fb50.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fb10.x, popup_y + fb10.y, fb10.w, fb10.h), 'action': 'buy_food', 'qty': 10})
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fb50.x, popup_y + fb50.y, fb50.w, fb50.h), 'action': 'buy_food', 'qty': 50})

            surface.blit(popup_surf, (popup_x, popup_y))
            # store rects for click handling (we only need close rect and the popup rect)
            self._trade_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._trade_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # Unit purchase popup
        if getattr(self, 'show_unit_popup', False):
            popup_w = int(W * 0.7)
            popup_h = int(H * 0.8)
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            popup_surf.blit(font_medium.render('Warrior Units', True, BLACK), (10, 10))

            # Close button
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))

            y = 60
            self._unit_buy_buttons = []
            
            # Display player's current resources
            popup_surf.blit(font_small.render(f"USD: ${int(self.player_usd)}", True, (60,60,60)), (10, y))
            y += 28
            # Aggregate available ores (mined + stock) - display in two lines to avoid overlap
            avail_ores = self.aggregate_mined_totals()
            for ore in avail_ores:
                avail_ores[ore] += int(self.player_stock.get(ore, 0))
            ore_line1 = f"Gold: {avail_ores.get('Gold',0)}  Silver: {avail_ores.get('Silver',0)}  Rare Earth: {avail_ores.get('Rare Earth',0)}"
            ore_line2 = f"Copper: {avail_ores.get('Copper',0)}  Aluminum: {avail_ores.get('Aluminum',0)}"
            popup_surf.blit(font_small.render(ore_line1, True, (60,60,60)), (10, y))
            y += 26
            popup_surf.blit(font_small.render(ore_line2, True, (60,60,60)), (10, y))
            y += 40

            # Iterate through three unit types under Warrior category
            category = 'Warrior'
            for unit_name, unit_data in self.unit_catalog.get(category, {}).items():
                hp = unit_data['hp']
                attack = unit_data['attack']
                price = unit_data['price']
                
                # Unit name and attributes (bold display)
                unit_line = f"{unit_name}  HP:{hp}  ATK:{attack}"
                popup_surf.blit(font_medium.render(unit_line, True, BLACK), (10, y))
                y += 36
                
                # Price details - split into multiple lines if too long to avoid overlap
                price_parts = []
                for res, amt in price.items():
                    if res == 'USD':
                        price_parts.append(f"${amt}")
                    else:
                        price_parts.append(f"{amt} {res}")
                
                # Split price display into two lines if there are many resources
                if len(price_parts) > 3:
                    # First line: first 3 items
                    price_line1 = "Price: " + ", ".join(price_parts[:3])
                    popup_surf.blit(font_small.render(price_line1, True, (80,80,80)), (10, y))
                    y += 22
                    # Second line: remaining items
                    price_line2 = "       " + ", ".join(price_parts[3:])
                    popup_surf.blit(font_small.render(price_line2, True, (80,80,80)), (10, y))
                    y -= 22  # Move back up for button positioning
                else:
                    price_text = "Price: " + ", ".join(price_parts)
                    popup_surf.blit(font_small.render(price_text, True, (80,80,80)), (10, y))
                
                # Check if player can afford
                can_afford = True
                if 'USD' in price and self.player_usd < price['USD']:
                    can_afford = False
                for ore, amt in price.items():
                    if ore != 'USD' and avail_ores.get(ore, 0) < amt:
                        can_afford = False
                        break
                
                # Buy button (positioned on right side to avoid overlap with price)
                buy_color = (60,160,60) if can_afford else (120,120,120)
                btn_x = popup_w - 130
                btn_y = y - 4
                buy_rect = pygame.Rect(btn_x, btn_y, 110, 32)
                pygame.draw.rect(popup_surf, buy_color, buy_rect)
                pygame.draw.rect(popup_surf, WHITE, buy_rect, 2)  # white border
                popup_surf.blit(font_small.render('Buy', True, WHITE), (buy_rect.x + 36, buy_rect.y + 8))
                
                # 存储按钮信息
                self._unit_buy_buttons.append({
                    'rect': pygame.Rect(popup_x + buy_rect.x, popup_y + buy_rect.y, buy_rect.w, buy_rect.h),
                    'unit_name': unit_name,
                    'category': category,
                    'can_afford': can_afford,
                    'price': price,
                    'hp': hp,
                    'attack': attack
                })
                
                # Add extra spacing if price was split into two lines
                if len(price_parts) > 3:
                    y += 60
                else:
                    y += 48

            # Display current owned units count at bottom
            y += 15
            popup_surf.blit(font_small.render(f"Owned Units: {len(self.player_units)}", True, BLUE), (10, y))
            
            surface.blit(popup_surf, (popup_x, popup_y))
            self._unit_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._unit_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # Fleet send popup
        if getattr(self, 'show_fleet_popup', False) and self.fleet_popup_source:
            popup_w = int(W * 0.65)  # 增大宽度从0.5到0.65
            popup_h = int(H * 0.7)   # 增大高度从0.6到0.7
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            
            # Title
            title = f"Send Ships from {self.fleet_popup_source.name}"
            popup_surf.blit(font_medium.render(title, True, BLACK), (10, 10))
            
            # Close button
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))
            
            # Show available ships
            available = getattr(self.fleet_popup_source, 'fleet_count', 0)
            popup_surf.blit(font_small.render(f"Available Ships: {available}", True, BLACK), (10, 50))
            
            # Get adjacent bodies
            adjacent = self.get_adjacent_bodies(self.fleet_popup_source)
            
            y = 90
            self._fleet_send_buttons = []
            
            if len(adjacent) == 0:
                popup_surf.blit(font_small.render("No connected destinations", True, (150,150,150)), (10, y))
            else:
                popup_surf.blit(font_small.render("Select destination:", True, BLACK), (10, y))
                y += 30
                
                for dest_body in adjacent:
                    # Destination name
                    dest_name = dest_body.name
                    popup_surf.blit(font_small.render(dest_name, True, BLACK), (10, y))
                    y += 32  # 增加行间距从28到32
                    
                    # Send buttons for different quantities
                    btn_y = y - 28  # 调整按钮位置
                    send_options = [5, 10, 20]
                    btn_x_start = 220  # 向右移动按钮位置从180到220
                    for i, qty in enumerate(send_options):
                        can_send = available >= qty
                        btn_color = (60,120,180) if can_send else (120,120,120)
                        btn_x = btn_x_start + i * 85  # 增加按钮间距从75到85
                        btn_rect = pygame.Rect(btn_x, btn_y, 75, 28)  # 增加宽度从70到75，高度从22到28
                        pygame.draw.rect(popup_surf, btn_color, btn_rect)
                        pygame.draw.rect(popup_surf, WHITE, btn_rect, 1)
                        popup_surf.blit(font_small.render(f"{qty}", True, WHITE), (btn_x + 28, btn_y + 5))  # 调整文字位置
                        
                        # Store button info
                        self._fleet_send_buttons.append({
                            'rect': pygame.Rect(popup_x + btn_x, popup_y + btn_y, btn_rect.w, btn_rect.h),
                            'dest': dest_body,
                            'qty': qty,
                            'can_send': can_send
                        })
                    
                    y += 12  # 增加间距从10到12
            
            surface.blit(popup_surf, (popup_x, popup_y))
            self._fleet_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._fleet_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

    # Helper: aggregate mined totals across all planets (does not include player_stock)
    def aggregate_mined_totals(self):
        totals = {'Gold': 0, 'Silver': 0, 'Rare Earth': 0, 'Copper': 0, 'Aluminum': 0}
        for system in self.systems:
            for planet in system.planets:
                for ore in totals.keys():
                    totals[ore] += int(planet.mined_ore.get(ore, 0))
        return totals

    # Helper: deduct mined resources from player_stock first then planets (returns amount actually deducted)
    def deduct_mined_from_sources(self, ore, amount):
        left = int(amount)
        # from player stock
        stock_amt = int(self.player_stock.get(ore, 0))
        take = min(stock_amt, left)
        if take > 0:
            self.player_stock[ore] = max(0, stock_amt - take)
            left -= take
        if left <= 0:
            return int(amount)
        # from planets
        for system in self.systems:
            for planet in system.planets:
                avail = int(planet.mined_ore.get(ore, 0))
                if avail <= 0:
                    continue
                t = min(avail, left)
                planet.mined_ore[ore] = max(0, planet.mined_ore.get(ore, 0) - t)
                left -= t
                if left <= 0:
                    return int(amount)
        # return actual deducted
        return int(amount - left)

    def sell_ore(self, ore, qty):
        totals = self.aggregate_mined_totals()
        avail = int(totals.get(ore, 0)) + int(self.player_stock.get(ore, 0))
        if qty == 'all':
            qty_to_sell = int(avail)
        else:
            qty_to_sell = int(min(qty, avail))
        if qty_to_sell <= 0:
            return
        # determine actual deducted
        deducted = self.deduct_mined_from_sources(ore, qty_to_sell)
        # credit player USD based on actual deducted and sell price (90% of buy)
        price_per = self.current_trade_prices.get(ore, 0.0) * 0.9
        self.player_usd += price_per * deducted

    def handle_click(self, x, y):
        # If fleet popup is open, handle its controls first
        if getattr(self, 'show_fleet_popup', False):
            # close button
            if hasattr(self, '_fleet_popup_close_rect') and self._fleet_popup_close_rect.collidepoint(x, y):
                self.show_fleet_popup = False
                self.fleet_popup_source = None
                return True
            # send buttons
            for btn in getattr(self, '_fleet_send_buttons', []):
                if btn['rect'].collidepoint(x, y) and btn.get('can_send', False):
                    # 派遣舰队
                    qty = btn['qty']
                    dest = btn['dest']
                    source = self.fleet_popup_source
                    
                    # 扣除出发地的舰船
                    source.fleet_count -= qty
                    
                    # 创建移动中的舰队
                    fleet = MovingFleet(source, dest, qty)
                    self.moving_fleets.append(fleet)
                    
                    # 播放音效
                    try:
                        if SFX.get('slight_click'):
                            SFX['slight_click'].play()
                    except Exception:
                        pass
                    
                    # 关闭弹窗
                    self.show_fleet_popup = False
                    self.fleet_popup_source = None
                    return True
            # clicks inside popup are consumed
            if hasattr(self, '_fleet_popup_rect') and self._fleet_popup_rect.collidepoint(x, y):
                return True
            return True
        
        # If unit popup is open, handle its controls first
        if getattr(self, 'show_unit_popup', False):
            # close button
            if hasattr(self, '_unit_popup_close_rect') and self._unit_popup_close_rect.collidepoint(x, y):
                self.show_unit_popup = False
                return True
            # buy buttons
            for btn in getattr(self, '_unit_buy_buttons', []):
                if btn['rect'].collidepoint(x, y) and btn.get('can_afford', False):
                    # 扣除资源并创建单位
                    price = btn['price']
                    # 扣除 USD
                    if 'USD' in price:
                        self.player_usd -= price['USD']
                    # 扣除矿物（优先从 player_stock，然后从星球上挖出的矿物）
                    for ore, amt in price.items():
                        if ore != 'USD':
                            self.deduct_mined_from_sources(ore, amt)
                    # 创建单位实例
                    unit = {
                        'category': btn['category'],
                        'name': btn['unit_name'],
                        'hp': btn['hp'],
                        'max_hp': btn['hp'],
                        'attack': btn['attack']
                    }
                    self.player_units.append(unit)
                    # 播放确认声音（优先 ding）
                    try:
                        if SFX.get('ding'):
                            SFX['ding'].play()
                        elif SFX.get('medium_click'):
                            SFX['medium_click'].play()
                    except Exception:
                        pass
                    return True
            # clicks inside popup are consumed
            if hasattr(self, '_unit_popup_rect') and self._unit_popup_rect.collidepoint(x, y):
                return True
            return True
        
        # If trade popup is open, handle its controls first
        # If trade popup is open, handle its controls first
        if getattr(self, 'show_trade_popup', False):
            # close button
            if hasattr(self, '_trade_popup_close_rect') and self._trade_popup_close_rect.collidepoint(x, y):
                self.show_trade_popup = False
                self.trade_view = None
                return True
            # buy/sell selector
            if hasattr(self, '_trade_buy_selector_rect') and self._trade_buy_selector_rect.collidepoint(x, y):
                self.trade_view = 'buy'
                return True
            if hasattr(self, '_trade_sell_selector_rect') and self._trade_sell_selector_rect.collidepoint(x, y):
                self.trade_view = 'sell'
                return True
            # action buttons
            for btn in getattr(self, '_trade_action_buttons', []):
                if btn['rect'].collidepoint(x, y):
                    act = btn.get('action')
                    if act == 'sell':
                        ore = btn.get('ore')
                        qty = btn.get('qty')
                        if qty == 'all':
                            # determine total available
                            totals = self.aggregate_mined_totals()
                            totals[ore] = totals.get(ore, 0) + int(self.player_stock.get(ore, 0))
                            qty_to_sell = int(totals.get(ore, 0))
                        else:
                            qty_to_sell = int(qty)
                        if qty_to_sell > 0:
                            self.sell_ore(ore, qty_to_sell)
                            try:
                                if SFX.get('delete'):
                                    SFX['delete'].play()
                                elif SFX.get('slight_click'):
                                    SFX['slight_click'].play()
                            except Exception:
                                pass
                    elif act == 'sell_food':
                        qty = btn.get('qty')
                        if qty == 'all':
                            qty_to_sell = int(self.player_food)
                        else:
                            qty_to_sell = int(qty)
                        if qty_to_sell > 0:
                            # sell price is 90% of current buy price
                            price_per = self.current_trade_prices.get('Food', 0.0) * 0.9
                            price = price_per * qty_to_sell
                            self.player_food = max(0, self.player_food - qty_to_sell)
                            self.player_usd += price
                            try:
                                if SFX.get('delete'):
                                    SFX['delete'].play()
                            except Exception:
                                pass
                    elif act == 'sell_worker':
                        qty = int(btn.get('qty', 1))
                        if self.workers >= qty:
                            self.workers -= qty
                            self.player_usd += self.current_trade_prices.get('Worker', 0.0) * 0.9 * qty
                            try:
                                if SFX.get('delete'):
                                    SFX['delete'].play()
                            except Exception:
                                pass
                    elif act == 'buy':
                        ore = btn.get('ore')
                        qty = int(btn.get('qty', 1))
                        price = self.current_trade_prices.get(ore, 0.0) * qty
                        if self.player_usd >= price:
                            self.player_usd -= price
                            # add to player stock
                            self.player_stock[ore] = int(self.player_stock.get(ore, 0)) + qty
                            try:
                                if SFX.get('ding'):
                                    SFX['ding'].play()
                            except Exception:
                                pass
                    elif act == 'buy_food':
                        qty = int(btn.get('qty', 1))
                        price = self.current_trade_prices.get('Food', 0.0) * qty
                        if self.player_usd >= price:
                            self.player_usd -= price
                            self.player_food += qty
                            try:
                                if SFX.get('ding'):
                                    SFX['ding'].play()
                            except Exception:
                                pass
                    return True
            # clicks inside popup area are consumed
            if hasattr(self, '_trade_popup_rect') and self._trade_popup_rect.collidepoint(x, y):
                return True
            return True

        # 如果任意弹窗正在显示，先处理弹窗关闭点击（弹窗优先）
        # Global ores popup handling
        if getattr(self, 'show_ore_popup', False):
            if hasattr(self, '_ore_popup_close_rect') and self._ore_popup_close_rect.collidepoint(x, y):
                self.show_ore_popup = False
                self._ore_popup_totals = None
                return True
            # 点击弹窗之外不做其他操作
            if hasattr(self, '_ore_popup_rect') and self._ore_popup_rect.collidepoint(x, y):
                return True
            return True

        # Per-planet mined popup handling
        if getattr(self, 'show_mined_popup', False):
            if hasattr(self, '_popup_close_rect') and self._popup_close_rect.collidepoint(x, y):
                self.show_mined_popup = False
                self.mined_popup_body = None
                return True
            # 点击弹窗之外不做其他操作
            if hasattr(self, '_popup_rect') and self._popup_rect.collidepoint(x, y):
                return True
            return True
        # 检查是否点击了"购买工人"按钮
        if hasattr(self, '_buy_worker_rect') and self._buy_worker_rect.collidepoint(x, y):
            if self.player_food >= 5:
                self.player_food -= 5
                self.workers += 1  # 添加到未分配工人池
                # 播放购买工人音效
                try:
                    if SFX.get('ding'):
                        SFX['ding'].play()
                    elif SFX.get('medium_click'):
                        SFX['medium_click'].play()
                except Exception:
                    pass
            return True

        # 检查是否点击了顶部的 "Ores" 按钮
        if hasattr(self, '_ores_button_rect') and self._ores_button_rect.collidepoint(x, y):
            self._ore_popup_totals = self.aggregate_mined_totals()
            self.show_ore_popup = True
            return True
        # 检查是否点击了顶部的 "Trade" 按钮
        if hasattr(self, '_trade_button_rect') and self._trade_button_rect.collidepoint(x, y):
            self.show_trade_popup = True
            self.trade_view = 'buy'
            return True
        
        # Check if "Units" button was clicked
        if hasattr(self, '_units_button_rect') and self._units_button_rect.collidepoint(x, y):
            self.show_unit_popup = True
            return True
        
        # 检查是否点击了左侧信息面板的按钮
        if x < W//3 and self.selected_body:
            # 点击舰船数量文本打开派遣弹窗（对所有星体通用）
            if hasattr(self, '_fleet_text_rect') and self._fleet_text_rect.collidepoint(x, y):
                fleet_count = getattr(self.selected_body, 'fleet_count', 0)
                if fleet_count > 0:
                    self.show_fleet_popup = True
                    self.fleet_popup_source = self.selected_body
                    try:
                        if SFX.get('medium_click'):
                            SFX['medium_click'].play()
                    except Exception:
                        pass
                return True
            
            if not self.selected_body.is_star:
                # 查看已开采按钮 (View Mined)
                view_mined_rect = pygame.Rect(10, H - 90, 120, 20)
                if view_mined_rect.collidepoint(x, y):
                    # 仅当有已挖出矿物时显示
                    if sum(self.selected_body.mined_ore.values()) > 0:
                        self.show_mined_popup = True
                        self.mined_popup_body = self.selected_body
                        try:
                            if SFX.get('ding'):
                                SFX['ding'].play()
                        except Exception:
                            pass
                    return True

                # 派遣工人按钮 (Dispatch Worker)
                dispatch_btn_rect = pygame.Rect(10, H - 60, 100, 20)
                if dispatch_btn_rect.collidepoint(x, y):
                    if int(self.workers) > 0:  # 有可用的未分配工人（只使用整数部分）
                        self.selected_body.assigned_workers += 1
                        self.workers -= 1  # 减去1个完整工人
                        try:
                            if SFX.get('slight_click'):
                                SFX['slight_click'].play()
                        except Exception:
                            pass
                    return True
                
                # 召回工人按钮 (Recall Worker)
                recall_btn_rect = pygame.Rect(10, H - 30, 100, 20)
                if recall_btn_rect.collidepoint(x, y):
                    if self.selected_body.assigned_workers > 0:
                        self.selected_body.assigned_workers -= 1
                        self.workers += 1
                        try:
                            if SFX.get('slight_click'):
                                SFX['slight_click'].play()
                        except Exception:
                            pass
                    return True
            return True
        
        # 处理星体点击
        self.selected_body = None
        for system in self.systems:
            body = system.get_body_at(x, y, self.camera_x, self.camera_y, self.zoom)
            if body:
                self.selected_body = body
                body.selected = True
                self.camera_x = body.x
                self.camera_y = body.y
                return True
        return False

    def handle_zoom(self, amount):
        self.zoom = max(0.2, min(2.0, self.zoom + amount))
    
    def get_adjacent_bodies(self, body):
        """获取与指定星体有链接线连接的相邻星体"""
        adjacent = []
        # 检查星系内部连接
        for system in self.systems:
            if body == system.star or body in system.planets:
                # 星系内部连接
                for conn in system.connections:
                    if conn[0] == body:
                        adjacent.append(conn[1])
                    elif conn[1] == body:
                        adjacent.append(conn[0])
        
        # 检查星系间连接
        for conn in self.inter_system_connections:
            if conn[0] == body:
                adjacent.append(conn[1])
            elif conn[1] == body:
                adjacent.append(conn[0])
        
        return adjacent

level1_buttons = {'Start': (W//2, H//2), 'Reload': (W//2, H//2 + 60), 'Help': (W//2, H//2 + 120), 'Exit': (W//2, H//2 + 180)}
level2_buttons = {'Single Player vs AI': (W//2, H//2 - 30), 'Multiplayer': (W//2, H//2 + 30), 'Back': (100, 50)}
level3_buttons = {'小宇宙 (Small)': (W//2, H//2 - 30), '大宇宙 (Large)': (W//2, H//2 + 30), 'Back': (100, 50)}

def draw_title():
    lcd.blit(font_big.render("STELLARIS", True, WHITE), font_big.render("STELLARIS", True, WHITE).get_rect(center=(W//2, 150)))

def draw_button(text, position, font=font_medium, color=WHITE):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=position)
    if text_rect.collidepoint(pygame.mouse.get_pos()): text_surface = font.render(text, True, BLUE)
    lcd.blit(text_surface, text_rect)
    return text_rect

def draw_buttons(buttons, font=font_medium):
    return {text: draw_button(text, pos, font) for text, pos in buttons.items()}

def main():
    game_state = GameState.MENU
    game_world = None
    running = True

    while running:
        lcd.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == GameState.SINGLE_PLAYER:
                        game_state = GameState.MODE_SELECT
                    else:
                        running = False
            elif event.type == pygame.MOUSEWHEEL:
                # New-style wheel event (pygame 2 / SDL2).
                # Only zoom when in single player and mouse is not over the left info panel.
                if game_state == GameState.SINGLE_PLAYER and game_world:
                    mx, my = pygame.mouse.get_pos()
                    # left info panel width = W//3 (matches drawing logic)
                    if not (game_world.selected_body and mx < W//3):
                        # event.y is positive for wheel up
                        game_world.handle_zoom(0.1 * event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                if event.button == 1:  # 左键点击
                    if game_state == GameState.MENU:
                        for text, rect in draw_buttons(level1_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效（优先 medium_click -> click）
                                try:
                                    if SFX.get('medium_click'):
                                        SFX['medium_click'].play()
                                    elif SFX.get('click'):
                                        SFX['click'].play()
                                except Exception:
                                    pass
                                if text == 'Start':
                                    game_state = GameState.MODE_SELECT
                                elif text == 'Exit':
                                    running = False
                    elif game_state == GameState.MODE_SELECT:
                        for text, rect in draw_buttons(level2_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效（优先 medium_click -> click）
                                try:
                                    if SFX.get('medium_click'):
                                        SFX['medium_click'].play()
                                    elif SFX.get('click'):
                                        SFX['click'].play()
                                except Exception:
                                    pass
                                if text == 'Single Player vs AI':
                                    game_state = GameState.SCALE_SELECT  # 先进入规模选择界面
                                elif text == 'Back':
                                    game_state = GameState.MENU
                    elif game_state == GameState.SCALE_SELECT:
                        for text, rect in draw_buttons(level3_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效
                                try:
                                    if SFX.get('medium_click'):
                                        SFX['medium_click'].play()
                                    elif SFX.get('click'):
                                        SFX['click'].play()
                                except Exception:
                                    pass
                                if text == '小宇宙 (Small)':
                                    game_state = GameState.SINGLE_PLAYER
                                    game_world = GameWorld(scale='small')
                                    # Immediately draw once so UI element rects are initialized
                                    try:
                                        game_world.draw(lcd)
                                        pygame.display.flip()
                                    except Exception:
                                        pass
                                elif text == '大宇宙 (Large)':
                                    game_state = GameState.SINGLE_PLAYER
                                    game_world = GameWorld(scale='large')
                                    # Immediately draw once so UI element rects are initialized
                                    try:
                                        game_world.draw(lcd)
                                        pygame.display.flip()
                                    except Exception:
                                        pass
                                elif text == 'Back':
                                    game_state = GameState.MODE_SELECT
                    elif game_state == GameState.SINGLE_PLAYER:
                        if not game_world.handle_click(x, y):  # 如果没有点击到星体，开始拖拽
                            game_world.dragging = True
                            game_world.last_mouse_pos = (x, y)
                elif event.button == 4:  # 滚轮向上 (legacy)
                    if game_state == GameState.SINGLE_PLAYER and game_world:
                        # only zoom if mouse is outside the left info panel
                        if not (game_world.selected_body and x < W//3):
                            game_world.handle_zoom(0.1)
                elif event.button == 5:  # 滚轮向下 (legacy)
                    if game_state == GameState.SINGLE_PLAYER and game_world:
                        if not (game_world.selected_body and x < W//3):
                            game_world.handle_zoom(-0.1)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and game_state == GameState.SINGLE_PLAYER:  # 左键释放
                    game_world.dragging = False
            elif event.type == pygame.MOUSEMOTION and game_state == GameState.SINGLE_PLAYER:
                if game_world.dragging:
                    x, y = pygame.mouse.get_pos()
                    dx = x - game_world.last_mouse_pos[0]
                    dy = y - game_world.last_mouse_pos[1]
                    game_world.camera_x -= dx / game_world.zoom
                    game_world.camera_y -= dy / game_world.zoom
                    game_world.last_mouse_pos = (x, y)

        # 绘制当前状态
        if game_state == GameState.MENU:
            draw_title()
            draw_buttons(level1_buttons, font_medium)
        elif game_state == GameState.MODE_SELECT:
            draw_buttons(level2_buttons, font_medium)
        elif game_state == GameState.SCALE_SELECT:
            draw_buttons(level3_buttons, font_medium)
        elif game_state == GameState.SINGLE_PLAYER:
            game_world.draw(lcd)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()