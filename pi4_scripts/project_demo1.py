

# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import os, pygame, sys, math, time, random, threading
from pygame.locals import *
from enum import Enum

# GPIO按钮控制（仅在树莓派上可用）
GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    # 配置GPIO模式
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # PiTFT的4个按钮: GPIO 17, 22, 23, 27
    BUTTON_17 = 17  # 对应pause
    BUTTON_22 = 22  # 对应buy worker
    BUTTON_23 = 23  # 对应trade
    BUTTON_27 = 27  # 对应exit
    # 设置按钮为输入，启用上拉电阻
    for pin in [BUTTON_17, BUTTON_22, BUTTON_23, BUTTON_27]:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print("✓ GPIO按钮初始化成功 (GPIO 17=Pause, 22=Buy Worker, 23=Trade, 27=Exit)")
except Exception as e:
    print(f"⚠ GPIO初始化失败: {e}")
    GPIO_AVAILABLE = False

# NeoPixel LED控制（仅在树莓派上可用）
try:
    import board
    import neopixel
    import time
    NEOPIXEL_AVAILABLE = True
    NEOPIXEL_PIN = board.D12  # GPIO 12
    NUM_PIXELS = 9  # 9个LED灯
    pixels = None
    
    # LED游戏状态指示变量
    led_game_state = {
        'current_leds': 5,        # 当前亮起的LED数量（初始5个，范围0-9）
        'last_player_count': 0,   # 上次玩家占领数量
        'last_ai_count': 0,       # 上次AI占领数量
        'last_update': 0,         # 上次更新时间
        'update_interval': 1.0,   # 更新间隔（秒）- 每秒检查一次
        'last_danger_warning': 0, # 上次危险提示时间
        'initialized': False      # 是否已初始化星球计数
    }
    
    def init_neopixel():
        """初始化NeoPixel灯条"""
        global pixels, led_game_state
        try:
            pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.44, auto_write=False)
            # 初始点亮5个LED（蓝色）
            for i in range(NUM_PIXELS):
                if i < 5:
                    pixels[i] = (0, 22, 113)  # 蓝色（降低亮度）
                else:
                    pixels[i] = (0, 0, 0)     # 熄灭
            pixels.show()
            led_game_state['current_leds'] = 5
            led_game_state['last_update'] = time.time()
            print(f"✓ NeoPixel初始化成功，{NUM_PIXELS}个LED连接到GPIO 12 (游戏状态指示模式)")
            return True
        except Exception as e:
            print(f"⚠ NeoPixel初始化失败: {e}")
            return False
    
    def update_game_status_leds(player_planet_count, ai_planet_count):
        """根据双方占领星球数量更新LED显示
        
        LED逻辑：
        - 初始：5个LED亮起（蓝色，均势）
        - 玩家占领更多星球 -> 增加LED
        - AI占领更多星球 -> 减少LED
        - 1-3个LED：橙色（劣势）
        - 4-7个LED：蓝色（均势）
        - 7-9个LED：绿色（优势）
        - 0个LED：失败
        - 9个LED：胜利
        """
        global pixels, led_game_state
        if not NEOPIXEL_AVAILABLE or pixels is None:
            return
        
        try:
            current_time = time.time()
            # 控制更新频率，避免LED闪烁
            if current_time - led_game_state['last_update'] < led_game_state['update_interval']:
                return
            
            led_game_state['last_update'] = current_time
            
            # 初始化：第一次调用时记录初始星球数量
            if not led_game_state['initialized']:
                led_game_state['last_player_count'] = player_planet_count
                led_game_state['last_ai_count'] = ai_planet_count
                led_game_state['initialized'] = True
                # 保持初始5个LED
                return
            
            # 计算双方星球数量变化
            player_change = player_planet_count - led_game_state['last_player_count']
            ai_change = ai_planet_count - led_game_state['last_ai_count']
            
            # 更新记录
            led_game_state['last_player_count'] = player_planet_count
            led_game_state['last_ai_count'] = ai_planet_count
            
            # 根据双方变化调整LED
            current_leds = led_game_state['current_leds']
            
            # 玩家占领更多 -> 增加LED（每占领1个星球增加1个灯）
            if player_change > ai_change:
                delta = player_change - ai_change
                if delta > 0:
                    current_leds = min(NUM_PIXELS, current_leds + delta)
            # AI占领更多 -> 减少LED（每占领1个星球减少1个灯）
            elif ai_change > player_change:
                delta = ai_change - player_change
                if delta > 0:
                    current_leds = max(0, current_leds - delta)
            
            # 限制范围（0-9）
            current_leds = max(0, min(NUM_PIXELS, current_leds))
            led_game_state['current_leds'] = current_leds
            
            # 更新LED显示
            for i in range(NUM_PIXELS):
                if i < current_leds:
                    # 根据LED数量显示不同颜色
                    if current_leds >= 7:  # 7-9个LED：绿色（优势）
                        pixels[i] = (0, 113, 0)  # 绿色
                    elif current_leds >= 4:  # 4-7个LED：蓝色（均势）
                        pixels[i] = (0, 45, 113)  # 蓝色
                    else:  # 1-3个LED：橙色（劣势）
                        pixels[i] = (113, 45, 0)  # 橙色
                else:
                    pixels[i] = (0, 0, 0)  # 熄灭
            
            pixels.show()
            
            # 胜负判断和状态提示
            if current_leds >= NUM_PIXELS:
                if current_time - led_game_state['last_danger_warning'] >= 120:
                    print("🎉 LED全亮 - 玩家胜利！")
                    led_game_state['last_danger_warning'] = current_time
            elif current_leds <= 0:
                if current_time - led_game_state['last_danger_warning'] >= 120:
                    print("💀 LED全灭 - 玩家失败！")
                    led_game_state['last_danger_warning'] = current_time
            elif current_leds <= 3:
                if current_time - led_game_state['last_danger_warning'] >= 120:
                    print("⚠️  橙色警告 - 玩家劣势！")
                    led_game_state['last_danger_warning'] = current_time
                    
        except Exception as e:
            print(f"⚠ LED状态更新失败: {e}")
    
    def update_breathing_leds():
        """保留此函数以兼容（不再使用呼吸效果）"""
        pass
    
    def update_planet_leds(planet_count):
        """保留此函数以兼容，但不再使用"""
        pass
    
    def set_led_color(index, color):
        """设置指定LED的颜色"""
        global pixels
        if not NEOPIXEL_AVAILABLE or pixels is None:
            return
        
        try:
            if 0 <= index < NUM_PIXELS:
                pixels[index] = color
                pixels.show()
        except Exception as e:
            print(f"⚠ 设置LED颜色失败: {e}")
    
    def clear_all_leds():
        """清除所有LED"""
        global pixels
        if NEOPIXEL_AVAILABLE and pixels is not None:
            try:
                pixels.fill((0, 0, 0))
                pixels.show()
                print("✓ 所有LED已关闭")
            except Exception as e:
                print(f"⚠ 清除LED失败: {e}")
    
    def cleanup_neopixel():
        """清理NeoPixel资源"""
        global pixels
        if NEOPIXEL_AVAILABLE and pixels is not None:
            try:
                pixels.fill((0, 0, 0))
                pixels.show()
                pixels.deinit()
                pixels = None
                print("✓ NeoPixel资源已清理")
            except Exception as e:
                print(f"⚠ NeoPixel清理失败: {e}")

except ImportError:
    NEOPIXEL_AVAILABLE = False
    print("⚠ NeoPixel库不可用，LED功能禁用")
    print("  提示：请安装 adafruit-circuitpython-neopixel")
    print("  pip install adafruit-circuitpython-neopixel")
    
    # 创建空函数以避免错误
    def init_neopixel(): return True
    def update_game_status_leds(player_count, ai_count): pass
    def update_breathing_leds(): pass
    def update_planet_leds(planet_count): pass
    def set_led_color(index, color): pass
    def clear_all_leds(): pass
    def cleanup_neopixel(): pass

# Detect whether we're running on a PiTFT (framebuffer at /dev/fb1)
def on_pitft():
    # 检查命令行参数，如果有 --external-display 就强制使用外接显示器
    if '--external-display' in sys.argv:
        return False
    # 检查命令行参数，如果有 --pitft 就强制使用PiTFT
    if '--pitft' in sys.argv:
        return True
    
    # 如果没有命令行参数且在树莓派上，询问用户选择（只询问一次）
    if os.path.exists("/dev/fb1"):
        print("检测到树莓派环境，请选择显示模式：")
        print("1. PiTFT触摸屏 (320x240, 全屏)")
        print("2. 外接显示器 (800x600, 窗口)")
        
        while True:
            try:
                choice = input("请输入选择 (1或2): ").strip()
                if choice == '1':
                    print("使用PiTFT触摸屏模式")
                    return True
                elif choice == '2':
                    # 检查外接显示器是否可用
                    display_ok = False
                    if 'DISPLAY' not in os.environ:
                        os.putenv('DISPLAY', ':0')
                    
                    try:
                        import subprocess
                        result = subprocess.run(['xset', 'q'], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            display_ok = True
                    except:
                        pass
                    
                    if display_ok:
                        print("使用外接显示器模式")
                        return False
                    else:
                        print("⚠ 外接显示器不可用！请选择PiTFT模式(1)")
                        print("💡 提示：如需使用外接显示器，请先运行: export DISPLAY=:0")
                        continue
                else:
                    print("无效选择，请输入1或2")
            except (KeyboardInterrupt, EOFError):
                print("\n使用默认模式：PiTFT触摸屏")
                return True
    
    # PC环境默认返回False
    return False

# 根据用户选择设置环境变量
use_pitft = on_pitft()

if use_pitft:
    # PiTFT模式：导入相关库并设置环境变量
    try:
        import sys
        # 尝试多个可能的路径来查找PiTFT库
        possible_paths = [
            '/home/qz425/final/pigame',
            '/home/qz425/final/pitft_touchscreen',
            '/usr/local/lib/python3/dist-packages',
            '/usr/lib/python3/dist-packages',
            '.',  # 当前目录
            'pigame',  # 如果已安装在系统路径中
            'pitft_touchscreen'
        ]

        pigame_imported = False
        pitft_touchscreen_imported = False

        for path in possible_paths:
            if not pigame_imported:
                try:
                    if path.startswith('/'):
                        sys.path.insert(0, path)
                    import pigame
                    pigame_imported = True
                    print(f"✓ 找到pigame库: {path}")
                except ImportError:
                    if path.startswith('/'):
                        try:
                            sys.path.remove(path)
                        except ValueError:
                            pass
                    continue

            if not pitft_touchscreen_imported:
                try:
                    if path.startswith('/'):
                        sys.path.insert(0, path)
                    import pitft_touchscreen
                    pitft_touchscreen_imported = True
                    print(f"✓ 找到pitft_touchscreen库: {path}")
                except ImportError:
                    if path.startswith('/'):
                        try:
                            sys.path.remove(path)
                        except ValueError:
                            pass
                    continue

            if pigame_imported and pitft_touchscreen_imported:
                break

        if not pigame_imported or not pitft_touchscreen_imported:
            raise ImportError("无法找到pigame或pitft_touchscreen库")

        # 设置PiTFT环境变量
        os.putenv('SDL_VIDEODRIVER', 'fbcon')
        os.putenv('SDL_FBDEV', '/dev/fb1')
        os.putenv('SDL_MOUSEDRV', 'TSLIB')
        os.putenv('SDL_MOUSEDEV', '/dev/input/event6')
        os.putenv('DISPLAY', '')
        # 设置触摸屏设备
        os.environ['TSLIB_TSDEVICE'] = '/dev/input/event6'
        print("✓ PiTFT模式配置完成 (触摸设备: event6)")
    except ImportError as e:
        print(f"✗ PiTFT库导入失败: {e}")
        print("程序将尝试继续运行在无触摸模式...")
        use_pitft = False
else:
    # 外接显示器模式
    if 'DISPLAY' not in os.environ:
        os.putenv('DISPLAY', ':0')
    print("✓ 外接显示器模式配置完成")
  
# 导入LLM AI模块
try:
    from llm_ai_player import LLMAIPlayer
    import ai_config
    LLM_AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠ LLM AI模块导入失败: {e}")
    LLM_AI_AVAILABLE = False

# 检测触摸屏设备是否可用
def check_touchscreen_device():
    """检查触摸屏设备是否存在和可用"""
    possible_devices = [
        '/dev/input/touchscreen',
        '/dev/input/event6',
        '/dev/input/event0',
        '/dev/input/event1',
        '/dev/input/event2',
        '/dev/input/event3'
    ]
    
    for device in possible_devices:
        if os.path.exists(device):
            try:
                # 尝试打开设备文件来验证权限
                with open(device, 'rb') as f:
                    print(f"✓ 找到可用的触摸屏设备: {device}")
                    return device
            except (PermissionError, OSError) as e:
                print(f"⚠ 设备 {device} 存在但无法访问: {e}")
                continue
    
    print("⚠ 未找到可用的触摸屏设备")
    return None


def configure_audio_driver():
    """
    配置音频驱动，让SDL自动选择最佳驱动
    支持的驱动顺序：pulseaudio -> alsa -> oss -> dsp
    """
    import os
    import subprocess

    # 检查是否已经设置了音频驱动
    if 'SDL_AUDIODRIVER' in os.environ:
        driver = os.environ['SDL_AUDIODRIVER']
        print(f"[DEBUG] 使用已设置的音频驱动: {driver}")
        return

    # 自动检测并选择最佳音频驱动
    drivers_to_try = ['pulseaudio', 'alsa', 'oss', 'dsp']

    for driver in drivers_to_try:
        try:
            # 测试驱动是否可用
            test_env = os.environ.copy()
            test_env['SDL_AUDIODRIVER'] = driver

            # 运行一个简单的音频测试
            result = subprocess.run(
                ['python3', '-c', 'import pygame; pygame.mixer.init(); pygame.mixer.quit()'],
                env=test_env,
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                os.environ['SDL_AUDIODRIVER'] = driver
                print(f"[DEBUG] 自动选择音频驱动: {driver}")
                return

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            continue

    # 如果都没有成功，使用默认驱动
    print("[DEBUG] 使用SDL默认音频驱动")
    # 不设置SDL_AUDIODRIVER，让SDL自动选择


# Initialize pygame after any environment changes
# 音频驱动配置 - 自动选择最佳驱动
configure_audio_driver()

pygame.init()

# 初始化NeoPixel（仅在树莓派上）
neopixel_initialized = init_neopixel()

# 导入并初始化 PiTft 对象（如果在 PiTFT 上运行）
pitft = None
if use_pitft:
    try:
        # 检查pigame是否已导入
        if 'pigame' not in globals():
            raise ImportError("pigame库未导入")

        # 尝试使用 event6 初始化触摸屏
        pitft = pigame.PiTft()
        # 如果 pigame 支持设置触摸设备，尝试设置为 event6
        if hasattr(pitft, 'ts_device'):
            pitft.ts_device = '/dev/input/event6'
        print("✓ PiTFT触摸屏初始化成功")
    except Exception as e:
        print(f"⚠ PiTFT触摸屏初始化失败: {e}")
        print("程序将继续运行，但触摸功能将不可用")
        pitft = None
        use_pitft = False
        # 回退到外接显示器模式
        print("回退到外接显示器模式 (800x600)")
        W, H = 800, 600

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

# Initialize audio mixer with appropriate settings
print("[DEBUG] 初始化音频系统...")
try:
    if on_pitft():
        # Pi需要特定的音频设置 - 使用44100Hz标准频率，更大的buffer减少噪音
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)  # 增加混音通道数
        freq_info = pygame.mixer.get_init()
        print(f"[DEBUG] ✓ 音频初始化: {freq_info[0]}Hz, {freq_info[2]}声道, buffer=4096")
    else:
        pygame.mixer.init()
        print("Initialized audio mixer")
except Exception as e:
    print(f'[ERROR] 音频初始化失败: {e}')

# Load selectable SFX (must be loaded AFTER mixer init)
SFX = {}
SFX['medium_click'] = _load_sound('medium_click.wav', 0.8) or _load_sound('click.wav', 0.8)
SFX['slight_click'] = _load_sound('slight_click.wav', 0.7)
SFX['ding'] = _load_sound('ding.wav', 0.9)
SFX['delete'] = _load_sound('delete.wav', 0.8)
SFX['click'] = _load_sound('click.wav', 0.8)

# Load and play background music
try:
    bgm_path = os.path.join(audio_dir, 'bgm.wav')
    if os.path.exists(bgm_path):
        try:
            print(f"[DEBUG] 加载BGM: {bgm_path}")
            print(f"[DEBUG] BGM文件大小: {os.path.getsize(bgm_path)} bytes")

            # 先停止任何正在播放的音乐
            pygame.mixer.music.stop()
            pygame.time.wait(100)

            pygame.mixer.music.load(bgm_path)
            print("[DEBUG] BGM加载成功")

            pygame.mixer.music.set_volume(0.4)  # 提高音量到40%
            print("[DEBUG] 设置BGM音量为0.4")

            pygame.mixer.music.play(-1)  # 循环播放
            print("[DEBUG] 开始播放BGM（循环播放）")

            # 等待更长时间让音频开始
            pygame.time.wait(1000)  # 等待1秒

            if pygame.mixer.music.get_busy():
                print(f'[DEBUG] ✓ BGM播放成功，正在播放中')
                print('[DEBUG] 如果仍无声音，请检查Pi音频配置')
            else:
                print(f'[WARN] BGM播放失败 - get_busy()返回False')

                # 尝试重新播放
                print("[DEBUG] 尝试重新播放BGM...")
                pygame.mixer.music.play(-1)
                pygame.time.wait(500)
                if pygame.mixer.music.get_busy():
                    print("[DEBUG] ✓ 重新播放成功")
                else:
                    print("[ERROR] 重新播放也失败")
                    print("[DEBUG] 尝试使用Sound对象播放BGM...")

                    # 备用的播放方法：使用Sound对象而不是music
                    try:
                        bgm_sound = pygame.mixer.Sound(bgm_path)
                        bgm_sound.set_volume(0.3)
                        bgm_sound.play(-1)  # 循环播放
                        print("[DEBUG] ✓ 使用Sound对象播放BGM成功")
                        pygame.time.wait(1000)
                        print("[HINT] 如果听到声音，说明是pygame.mixer.music的问题")
                    except Exception as e2:
                        print(f"[ERROR] Sound对象播放也失败: {e2}")
                        print("[HINT] 可能需要检查音频文件格式或Pi音频配置")

        except Exception as e:
            print(f'[ERROR] 无法播放BGM: {e}')
            import traceback
            traceback.print_exc()
    else:
        print(f'[WARN] 未找到BGM文件: {bgm_path}')
except Exception as e:
    print(f'[ERROR] BGM加载异常: {e}')
    import traceback
    traceback.print_exc()

# backward-compatible single variable for simple usages
click_sound = SFX.get('medium_click')

# 简单的音效管理器
class AudioManager:
    """增强的音效管理器，支持mplayer和pygame双重播放"""
    def __init__(self):
        self.use_mplayer = self._check_mplayer_available()
        self.playing_processes = []  # 跟踪正在播放的mplayer进程
        self.audio_files = {}  # 存储文件名到路径的映射

        if self.use_mplayer:
            print("[DEBUG] ✓ AudioManager: 使用mplayer播放音频")
        else:
            print("[DEBUG] AudioManager: 使用pygame播放音频")

        # 注册程序退出时的清理函数
        import atexit
        atexit.register(self.cleanup)

    def _check_mplayer_available(self):
        """检查mplayer是否可用"""
        try:
            import subprocess
            result = subprocess.run(['which', 'mplayer'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    def register_audio_file(self, name, file_path):
        """注册音频文件路径"""
        if os.path.exists(file_path):
            self.audio_files[name] = file_path

    def play_sfx(self, sound):
        """播放音效 - 优先使用mplayer"""
        if not sound:
            return

        try:
            # 如果sound是字符串，查找对应的音频文件路径
            if isinstance(sound, str):
                audio_path = self.audio_files.get(sound)
                if audio_path and self.use_mplayer and os.path.exists(audio_path):
                    self._play_with_mplayer(audio_path)
                    return
                # 如果不使用mplayer或文件不存在，回退到pygame Sound对象
                sound = SFX.get(sound)

            # 如果sound是pygame Sound对象，使用传统方法
            if hasattr(sound, 'play'):
                sound.play()
                return

        except Exception as e:
            print(f"播放音效失败: {e}")

    def _play_with_mplayer(self, audio_file):
        """使用mplayer播放音频文件"""
        try:
            import subprocess
            import threading

            # mplayer命令：只播放音频，不显示视频
            cmd = [
                'mplayer',
                '-vo', 'null',      # 不显示视频
                '-ao', 'alsa',      # 使用ALSA音频输出
                '-really-quiet',    # 静默模式
                '-volume', '50',    # 音量50%
                audio_file
            ]

            # 创建进程
            process = subprocess.Popen(cmd,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)

            # 添加到进程列表
            self.playing_processes.append(process)

            # 在后台等待进程结束并清理
            def cleanup_process():
                try:
                    process.wait()  # 等待进程结束
                except:
                    pass
                finally:
                    # 从列表中移除已完成的进程
                    if process in self.playing_processes:
                        self.playing_processes.remove(process)

            # 启动后台清理线程
            cleanup_thread = threading.Thread(target=cleanup_process, daemon=True)
            cleanup_thread.start()

        except Exception as e:
            print(f"mplayer播放失败: {e}")

    def stop_all_audio(self):
        """停止所有正在播放的音频"""
        if not self.playing_processes:
            return

        print(f"[DEBUG] 停止 {len(self.playing_processes)} 个mplayer进程...")

        for process in self.playing_processes[:]:  # 复制列表以避免修改时的问题
            try:
                if process.poll() is None:  # 检查进程是否还在运行
                    process.terminate()
                    # 等待最多1秒让进程优雅结束
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        # 如果没能在1秒内结束，强制结束
                        process.kill()
                        process.wait()
                print(f"[DEBUG] 已停止mplayer进程 (PID: {process.pid})")
            except Exception as e:
                print(f"[WARN] 停止mplayer进程失败: {e}")
            finally:
                if process in self.playing_processes:
                    self.playing_processes.remove(process)

    def cleanup(self):
        """清理资源"""
        self.stop_all_audio()

# 创建全局音效管理器实例
audio_manager = AudioManager()

# 注册音频文件路径到AudioManager（用于mplayer播放）
audio_files = {
    'medium_click': os.path.join(audio_dir, 'medium_click.wav'),
    'slight_click': os.path.join(audio_dir, 'slight_click.wav'),
    'ding': os.path.join(audio_dir, 'ding.wav'),
    'delete': os.path.join(audio_dir, 'delete.wav'),
    'click': os.path.join(audio_dir, 'click.wav')
}

for name, path in audio_files.items():
    if os.path.exists(path):
        audio_manager.register_audio_file(name, path)

# Choose resolution depending on whether we're using PiTFT
if use_pitft:
    W, H = 320, 240
else:
    W, H = 800, 600

# Use fullscreen on PiTFT
flags = 0
if use_pitft:
    flags |= pygame.FULLSCREEN

lcd = pygame.display.set_mode((W, H), flags)
pygame.display.set_caption("Stellaris")
clock = pygame.time.Clock()
# Hide mouse cursor on PiTFT (touchscreen)
pygame.mouse.set_visible(not use_pitft)

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

# 根据是否在PiTFT上运行调整字体大小
if use_pitft:
    # PiTFT 320x240 分辨率使用加大的字体
    font_tiny = load_font_with_fallback(13)    # 按钮用超小字体
    font_small = load_font_with_fallback(16)   # 原8 -> 14 -> 16 (再次加大)
    font_medium = load_font_with_fallback(22)  # 原12 -> 20 -> 22 (再次加大)
    font_big = load_font_with_fallback(36)     # 原28 -> 36
    font_huge = load_font_with_fallback(48)    # 超大字体
else:
    # PC 800x600 分辨率使用更大字体
    font_tiny = load_font_with_fallback(20)    # 按钮用超小字体
    font_small = load_font_with_fallback(24)   # 原14 -> 24
    font_medium = load_font_with_fallback(32)  # 原20 -> 32
    font_big = load_font_with_fallback(72)     # 原58 -> 72
    font_huge = load_font_with_fallback(96)    # 超大字体

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
        'Starbot': {
            'hp': 40,
            'attack': 20,
            'price': {'Gold': 25, 'Silver': 15, 'Rare Earth': 5, 'Copper': 5}
        },
        'Demolitionist': {
            'hp': 10,
            'attack': 15,
            'price': {'Gold': 10, 'Silver': 30, 'Copper': 5},
            'special': 'anti_starbot'  # 对Starbot有200%伤害加成
        },
        'Monk': {
            'hp': 20,
            'attack': 5,
            'price': {'Gold': 50, 'Silver': 50},
            'special': 'convert'  # 每秒20%概率转化敌方单位
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
    DIFFICULTY_SELECT = 3  # 新增：难度选择
    SCALE_SELECT = 4  # 修改：规模选择
    SINGLE_PLAYER = 5  # 修改：单人游戏

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
        
        # 单位列表：存储具体的兵种单位
        self.units = []  # 每个单位是一个字典，包含name, hp, max_hp, attack, special等
        
        # 战斗/占领状态
        self.under_siege = False  # 是否正在被围攻/占领中
        self.siege_start_time = None  # 围攻开始时间
        self.siege_duration = 0  # 围攻总时长（秒）
        self.attacker_owner = None  # 进攻方所有者
        self.attacker_count = 0  # 进攻方舰船数量
        self.defender_count = 0  # 防守方舰船数量
        
        # 最近一次战斗记录
        self.last_battle_info = None  # 存储战斗小结信息
        
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
            
            # Ownership indicator: colored ring around the planet
            if self.owner == 'player':
                # Blue ring for player-owned planets
                try:
                    pygame.draw.circle(surface, (100, 150, 255), (int(screen_x), int(screen_y)), radius + 3, 2)
                except: pass
            elif self.owner == 'ai':
                # Red ring for AI-owned planets
                try:
                    pygame.draw.circle(surface, (255, 100, 100), (int(screen_x), int(screen_y)), radius + 3, 2)
                except: pass
            
            # Conflict indicator: red exclamation mark for planets under siege/battle
            if getattr(self, 'under_siege', False):
                try:
                    # 红色感叹号
                    exclaim_size = max(12, int(radius * 1.2))
                    tx = int(screen_x)
                    ty = int(screen_y_fixed) - radius - exclaim_size - 5
                    
                    # 绘制感叹号主体（矩形）
                    exclaim_w = max(3, int(exclaim_size * 0.25))
                    exclaim_h = max(8, int(exclaim_size * 0.6))
                    pygame.draw.rect(surface, (255, 50, 50), 
                                   pygame.Rect(tx - exclaim_w//2, ty, exclaim_w, exclaim_h))
                    
                    # 绘制感叹号下方的点
                    dot_y = ty + exclaim_h + max(2, int(exclaim_size * 0.15))
                    pygame.draw.circle(surface, (255, 50, 50), (tx, dot_y), max(2, exclaim_w//2))
                except: pass

    def contains_point(self, x, y, camera_x, camera_y, zoom):
        screen_x = (self.x - camera_x) * zoom + W//2
        screen_y = (self.y - camera_y) * zoom + H//2
        dist = math.sqrt((x - screen_x)**2 + (y - screen_y)**2)
        return dist <= self.radius * zoom

# 移动中的舰队类
class MovingFleet:
    """表示正在星体间移动的舰队"""
    def __init__(self, start_body, end_body, ship_count, units=None):
        self.start_body = start_body
        self.end_body = end_body
        self.ship_count = ship_count
        self.units = units if units is not None else []  # 携带的具体单位
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
    def __init__(self, x, y, star_name, scale='large'):
        self.star = CelestialBody(x, y, is_star=True, star_name=star_name)
        self.planets = []
        self.connections = []  # 存储连接路径 (body1, body2)
        
        # 根据规模生成行星数量
        if scale == 'small':
            num_planets = random.randint(4, 6)  # 小宇宙：4-6个行星
        else:
            num_planets = random.randint(6, 12)  # 大宇宙：6-12个行星
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
        self.drag_start_pos = None  # 拖拽起始位置
        self.drag_threshold = 15 if W < 400 else 5  # 最小拖拽距离阈值（像素）
        
        # 双指触控支持（PiTFT）
        self.touch_points = {}  # 存储触摸点 {id: (x, y)}
        self.last_pinch_distance = None  # 上次双指距离
        self.last_two_finger_center = None  # 上次双指中心点
        
        # 暂停状态
        self.paused = False
        
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
        self.unit_popup_page = 0  # 当前页码
        # 是否显示舰队派遣弹窗
        self.show_fleet_popup = False
        self.fleet_popup_source = None
        
        # 单位选择界面（派遣舰队时选择具体单位）
        self.show_unit_select_popup = False
        self.unit_select_ship_count = 0
        self.unit_select_destination = None
        self.unit_select_source = None
        self.selected_units_to_send = []
        self.unit_select_scroll_offset = 0  # 滚动偏移量
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
        
        # LLM AI玩家（如果可用）
        self.llm_ai = None
        self.use_llm_ai = False
        self.ai_thinking = False  # AI是否正在思考
        self.ai_pending_action = None  # AI决策结果（异步）
        self.ai_thread_lock = threading.Lock()  # 线程锁
        if LLM_AI_AVAILABLE and hasattr(ai_config, 'USE_LLM_AI') and ai_config.USE_LLM_AI:
            try:
                # 获取AI提供商配置
                provider = getattr(ai_config, 'AI_PROVIDER', 'ollama')  # 默认ollama
                difficulty = getattr(ai_config, 'AI_DIFFICULTY', 'normal')
                proxy_url = getattr(ai_config, 'PROXY_URL', None)  # 代理配置
                
                if provider == "gemini":
                    # 使用Google Gemini
                    api_key = getattr(ai_config, 'GEMINI_API_KEY', None)
                    gemini_model = getattr(ai_config, 'GEMINI_MODEL', 'gemini-2.0-flash-exp')
                    
                    if api_key:
                        self.llm_ai = LLMAIPlayer(
                            api_key=api_key, 
                            provider="gemini", 
                            gemini_model=gemini_model, 
                            difficulty=difficulty,
                            proxy_url=proxy_url
                        )
                        if self.llm_ai.is_available():
                            self.use_llm_ai = True
                            print(f"✓ 使用Google Gemini AI ({gemini_model})")
                        else:
                            print("⚠ Gemini AI初始化失败，使用规则AI")
                    else:
                        print("⚠ 未配置Gemini API密钥，使用规则AI")
                        
                elif provider == "ollama":
                    # 使用免费的Ollama本地AI
                    ollama_model = getattr(ai_config, 'OLLAMA_MODEL', 'qwen2.5:3b')
                    self.llm_ai = LLMAIPlayer(
                        provider="ollama", 
                        ollama_model=ollama_model, 
                        difficulty=difficulty,
                        proxy_url=proxy_url
                    )
                    if self.llm_ai.is_available():
                        self.use_llm_ai = True
                        print(f"✓ 使用Ollama本地AI ({ollama_model})")
                    else:
                        print("⚠ Ollama AI初始化失败，使用规则AI")
                        
                else:  # openai
                    # 使用OpenAI GPT
                    api_key = getattr(ai_config, 'OPENAI_API_KEY', None)
                    model = getattr(ai_config, 'AI_MODEL', 'gpt-4o-mini')
                    
                    if api_key and api_key != 'sk-your-api-key-here':
                        self.llm_ai = LLMAIPlayer(
                            api_key=api_key, 
                            provider="openai", 
                            model=model, 
                            difficulty=difficulty,
                            proxy_url=proxy_url
                        )
                        if self.llm_ai.is_available():
                            self.use_llm_ai = True
                            print(f"✓ 使用OpenAI GPT AI ({model})")
                        else:
                            print("⚠ OpenAI AI初始化失败，使用规则AI")
                    else:
                        print("⚠ 未配置有效的OpenAI API密钥，使用规则AI")
            except Exception as e:
                print(f"⚠ LLM AI初始化错误: {e}，使用规则AI")
        else:
            print("✓ 使用规则AI")
        
        self.generate_systems()
        self.generate_inter_system_connections()  # 生成恒星系间连接
        
        # 初始化玩家起始星球（随机选择一个行星）
        self.initialize_player_start()

    def generate_systems(self):
        # 根据规模决定星系数量和生成范围
        if self.scale == 'small':
            num_systems = 2  # 小宇宙：2个星系
            range_limit = 300  # 生成范围：±300
            min_distance = 180  # 最小距离：180
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
                    self.systems.append(StarSystem(x, y, available_names[i], scale=self.scale))
                    break
    
    def initialize_player_start(self):
        """初始化玩家起始星球：随机选择一个行星，给予10艘舰船"""
        # 收集所有行星（不包括恒星）
        all_planets = []
        for system in self.systems:
            all_planets.extend(system.planets)
        
        if all_planets and len(all_planets) >= 2:
            # 随机选择两个相距较远的行星作为玩家和AI的起始星球
            random.shuffle(all_planets)
            
            # 玩家起始星球
            start_planet = all_planets[0]
            start_planet.owner = 'player'
            start_planet.fleet_count = 10
            
            # 将摄像机移动到起始星球
            self.camera_x = start_planet.x
            self.camera_y = start_planet.y
            
            print(f"玩家起始星球: {start_planet.name}, 位置: ({start_planet.x:.0f}, {start_planet.y:.0f})")
            
            # AI起始星球 - 选择离玩家最远的行星
            max_dist = 0
            ai_start = None
            for planet in all_planets[1:]:
                dist = math.hypot(planet.x - start_planet.x, planet.y - start_planet.y)
                if dist > max_dist:
                    max_dist = dist
                    ai_start = planet
            
            if ai_start:
                ai_start.owner = 'ai'
                ai_start.fleet_count = 10
                print(f"AI起始星球: {ai_start.name}, 位置: ({ai_start.x:.0f}, {ai_start.y:.0f})")
                self.ai_home_planet = ai_start
                self.player_home_planet = start_planet
            
            # 探索过的星球记录（通过航线连接过的星球）
            self.player_explored_bodies = {start_planet}  # 玩家初始探索过自己的起始星球
            self.ai_explored_bodies = {ai_start} if ai_start else set()  # AI初始探索过自己的起始星球
            
            # AI决策计时器和难度设置
            self.ai_last_decision_time = time.time()
            self.ai_difficulty = getattr(self, 'ai_difficulty', 'normal')  # 难度: easy, normal, hard
            
            # 根据难度调整AI参数
            if self.ai_difficulty == 'easy':
                self.ai_decision_interval = 16.0  # 简单模式：16秒决策一次（降低CPU占用）
                self.ai_aggression = 0.6  # 进攻性较低
                self.ai_resource_bonus = 0.8  # 资源生产80%
            elif self.ai_difficulty == 'hard':
                self.ai_decision_interval = 6.0  # 困难模式：6秒决策一次（优化后）
                self.ai_aggression = 1.4  # 进攻性更高
                self.ai_resource_bonus = 1.3  # 资源生产130%
            else:  # normal
                self.ai_decision_interval = 10.0  # 普通模式：10秒决策一次（优化后）
                self.ai_aggression = 1.0  # 标准进攻性
                self.ai_resource_bonus = 1.0  # 标准资源
            
            # 游戏状态
            self.game_over = False
            self.winner = None
            
            # 初始化LED显示
            self.update_led_display()
    
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
        """获取玩家可见的所有星体（已拥有的+AI拥有的+相邻的）"""
        owned = set(self.get_player_owned_bodies())
        visible = set(owned)
        
        # 添加所有AI拥有的星体（让玩家能看到AI）
        ai_owned = set(self.get_ai_owned_bodies())
        visible.update(ai_owned)
        
        # 添加所有与已拥有星体相邻的星体
        for body in owned:
            adjacent = self.get_adjacent_bodies(body)
            visible.update(adjacent)
        
        # 添加所有与AI拥有星体相邻的星体
        for body in ai_owned:
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
        # 根据舰队所有者确定进攻方
        attacker_owner = getattr(fleet, 'owner', 'player')
        
        # 标记目标星球为已探索（通过派遣舰队探索）
        if attacker_owner == 'player':
            self.player_explored_bodies.add(target)
        elif attacker_owner == 'ai':
            self.ai_explored_bodies.add(target)
        
        # 保存进攻方的单位列表
        attacking_units = fleet.units if hasattr(fleet, 'units') else []
        
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
                target.attacking_units = attacking_units  # 保存进攻方单位
                target.defending_units = []
                print(f"Start occupying neutral planet: {target.name}")
            else:
                # 已经有舰队在占领，增加进攻方兵力
                target.attacker_count += fleet.ship_count
                if hasattr(target, 'attacking_units'):
                    target.attacking_units.extend(attacking_units)
                else:
                    target.attacking_units = attacking_units
                
        elif target.owner == attacker_owner:
            # 情况2: 己方星球 - 直接增援
            target.fleet_count += fleet.ship_count
            # 将单位添加到星球
            if hasattr(target, 'units'):
                target.units.extend(attacking_units)
            else:
                target.units = attacking_units
            print(f"Reinforcing own planet: {target.name}, now has {target.fleet_count} ships")
            
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
                    target.attacking_units = attacking_units
                    target.defending_units = []
                    print(f"Start occupying enemy empty planet: {target.name}")
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
                    target.attacking_units = attacking_units
                    target.defending_units = target.units[:] if hasattr(target, 'units') else []
                    print(f"Start battle: {target.name}, Attacker {attacker_power} vs Defender {defender_power}, Est. {battle_duration:.1f}s")
            else:
                # 已经在战斗中，增加进攻方兵力
                target.attacker_count += fleet.ship_count
                if hasattr(target, 'attacking_units'):
                    target.attacking_units.extend(attacking_units)
                else:
                    target.attacking_units = attacking_units
    
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
        
        # 获取参战单位列表
        attacking_units = getattr(body, 'attacking_units', [])
        defending_units = getattr(body, 'defending_units', [])
        
        # 僧侣转化能力：每秒检查一次
        if hasattr(body, 'last_monk_check'):
            if current_time - body.last_monk_check >= 1.0:
                body.last_monk_check = current_time
                # 检查进攻方是否有僧侣（使用实际参战的单位）
                if body.attacker_owner == 'player':
                    monk_count = sum(1 for u in attacking_units if u.get('name') == 'Monk' and u.get('hp', 0) > 0)
                    if monk_count > 0 and body.defender_count > 0 and defending_units:
                        # 20%概率转化一个敌方单位
                        if random.random() < 0.2:
                            # 从防守方转移一个单位到进攻方
                            if defending_units:
                                converted_unit = defending_units.pop(0)
                                attacking_units.append(converted_unit)
                                body.defender_count -= 1
                                body.attacker_count += 1
                                print(f"僧侣转化了一个敌方单位！")
        else:
            body.last_monk_check = current_time
        
        if elapsed >= body.siege_duration:
            # 记录战斗前的数据
            initial_attacker_count = body.attacker_count
            initial_attacker_units = len(attacking_units)
            initial_defender_count = body.defender_count
            initial_defender_units = len(defending_units)
            
            # Battle/occupation ended
            if body.defender_count == 0:
                # No defenders, direct occupation
                body.owner = body.attacker_owner
                body.fleet_count = body.attacker_count
                # Assign attacker units to the planet
                body.units = attacking_units
                print(f"Occupation complete: {body.name}, {body.attacker_count} ships stationed")
                
                # 记录战斗信息（占领中立星球）
                body.last_battle_info = {
                    'attacker_owner': body.attacker_owner,
                    'defender_owner': 'neutral',
                    'attacker_ships_before': initial_attacker_count,
                    'attacker_ships_after': body.attacker_count,
                    'attacker_units_before': initial_attacker_units,
                    'attacker_units_after': len(attacking_units),
                    'defender_ships_before': 0,
                    'defender_ships_after': 0,
                    'defender_units_before': 0,
                    'defender_units_after': 0,
                    'winner': body.attacker_owner
                }
            else:
                # 有战斗，使用真实战斗模拟
                original_defender_owner = body.owner
                winner, survivors = self.simulate_battle(attacking_units, defending_units, body.attacker_owner)
                
                if winner == 'attacker':
                    # Attacker victory
                    body.owner = body.attacker_owner
                    body.fleet_count = len(survivors)
                    body.units = survivors
                    print(f"Battle won: {body.name}, {len(survivors)} ships remaining")
                    
                    # 记录战斗信息
                    body.last_battle_info = {
                        'attacker_owner': body.attacker_owner,
                        'defender_owner': original_defender_owner,
                        'attacker_ships_before': initial_attacker_count,
                        'attacker_ships_after': len(survivors),
                        'attacker_units_before': initial_attacker_units,
                        'attacker_units_after': len(survivors),
                        'defender_ships_before': initial_defender_count,
                        'defender_ships_after': 0,
                        'defender_units_before': initial_defender_units,
                        'defender_units_after': 0,
                        'winner': body.attacker_owner
                    }
                elif winner == 'defender':
                    # Defender victory
                    body.fleet_count = len(survivors)
                    body.units = survivors
                    print(f"Battle lost: {body.name}, enemy has {len(survivors)} ships remaining")
                    
                    # 记录战斗信息
                    body.last_battle_info = {
                        'attacker_owner': body.attacker_owner,
                        'defender_owner': original_defender_owner,
                        'attacker_ships_before': initial_attacker_count,
                        'attacker_ships_after': 0,
                        'attacker_units_before': initial_attacker_units,
                        'attacker_units_after': 0,
                        'defender_ships_before': initial_defender_count,
                        'defender_ships_after': len(survivors),
                        'defender_units_before': initial_defender_units,
                        'defender_units_after': len(survivors),
                        'winner': original_defender_owner
                    }
                else:
                    # Mutual destruction
                    body.owner = None
                    body.fleet_count = 0
                    body.units = []
                    print(f"Mutual destruction: {body.name}, all forces destroyed")
                    
                    # 记录战斗信息
                    body.last_battle_info = {
                        'attacker_owner': body.attacker_owner,
                        'defender_owner': original_defender_owner,
                        'attacker_ships_before': initial_attacker_count,
                        'attacker_ships_after': 0,
                        'attacker_units_before': initial_attacker_units,
                        'attacker_units_after': 0,
                        'defender_ships_before': initial_defender_count,
                        'defender_ships_after': 0,
                        'defender_units_before': initial_defender_units,
                        'defender_units_after': 0,
                        'winner': 'draw'
                    }
            
            # 重置围攻状态
            body.under_siege = False
            body.siege_start_time = None
            body.siege_duration = 0
            body.attacker_owner = None
            body.attacker_count = 0
            body.defender_count = 0
            
            # 更新LED显示（星球所有权可能已改变）
            self.update_led_display()
    
    def simulate_battle(self, attackers, defenders, attacker_owner):
        """
        模拟真实战斗，基于单位的HP和攻击力
        返回: (胜利方, 存活单位列表)
        """
        # 复制单位列表，避免修改原列表
        atk_units = [u.copy() for u in attackers if u.get('hp', 0) > 0]
        def_units = [u.copy() for u in defenders if u.get('hp', 0) > 0]
        
        # 如果有一方没有单位，直接返回
        if not atk_units:
            return ('defender', def_units)
        if not def_units:
            return ('attacker', atk_units)
        
        # 战斗模拟：轮流攻击
        max_rounds = 100  # 防止无限循环
        for round_num in range(max_rounds):
            # 移除已死亡单位
            atk_units = [u for u in atk_units if u.get('hp', 0) > 0]
            def_units = [u for u in def_units if u.get('hp', 0) > 0]
            
            # 检查战斗是否结束
            if not atk_units and not def_units:
                return ('draw', [])
            if not atk_units:
                return ('defender', def_units)
            if not def_units:
                return ('attacker', atk_units)
            
            # 进攻方攻击
            for attacker in atk_units[:]:  # 使用切片避免迭代时修改
                if not def_units:
                    break
                if attacker.get('hp', 0) <= 0:
                    continue
                
                # 选择目标（随机或优先攻击血少的）
                target = min(def_units, key=lambda u: u.get('hp', 0))
                attack_power = attacker.get('attack', 10)
                
                # 爆破手对Starbot有200%伤害
                if attacker.get('name') == 'Demolitionist' and target.get('name') == 'Starbot':
                    attack_power *= 2
                
                target['hp'] = target.get('hp', 0) - attack_power
            
            # 移除已死亡的防守单位
            def_units = [u for u in def_units if u.get('hp', 0) > 0]
            if not def_units:
                return ('attacker', atk_units)
            
            # 防守方反击
            for defender in def_units[:]:
                if not atk_units:
                    break
                if defender.get('hp', 0) <= 0:
                    continue
                
                # 选择目标
                target = min(atk_units, key=lambda u: u.get('hp', 0))
                attack_power = defender.get('attack', 10)
                
                # 爆破手对Starbot有200%伤害（如果防守方有爆破手）
                if defender.get('name') == 'Demolitionist' and target.get('name') == 'Starbot':
                    attack_power *= 2
                
                target['hp'] = target.get('hp', 0) - attack_power
            
            # 移除已死亡的进攻单位
            atk_units = [u for u in atk_units if u.get('hp', 0) > 0]
        
        # 如果达到最大回合数，比较剩余总HP
        atk_total_hp = sum(u.get('hp', 0) for u in atk_units)
        def_total_hp = sum(u.get('hp', 0) for u in def_units)
        
        if atk_total_hp > def_total_hp:
            return ('attacker', atk_units)
        elif def_total_hp > atk_total_hp:
            return ('defender', def_units)
        else:
            return ('draw', [])
    
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
                # 如果是已拥有的或AI拥有的，正常绘制；如果是未拥有的，绘制为灰色
                if system.star in owned_bodies or system.star.owner == 'ai':
                    system.star.draw(surface, self.camera_x, self.camera_y, self.zoom)
                else:
                    self.draw_body_gray(system.star, surface, self.camera_x, self.camera_y, self.zoom)
            
            # 绘制行星（如果可见）
            for planet in system.planets:
                if planet in visible_bodies:
                    if planet in owned_bodies or planet.owner == 'ai':
                        planet.draw(surface, self.camera_x, self.camera_y, self.zoom)
                    else:
                        self.draw_body_gray(planet, surface, self.camera_x, self.camera_y, self.zoom)

        # 更新并绘制移动中的舰队（暂停时不更新）
        frame_time = 1.0 / 60.0
        fleets_to_remove = []
        for fleet in self.moving_fleets:
            if not self.paused and not self.game_over:
                if fleet.update(frame_time):
                    # 舰队到达目的地，开始战斗/占领逻辑
                    self.handle_fleet_arrival(fleet)
                    fleets_to_remove.append(fleet)
                else:
                    # 绘制移动中的舰队
                    fleet.draw(surface, self.camera_x, self.camera_y, self.zoom)
            else:
                # 暂停或游戏结束时只绘制，不更新位置
                fleet.draw(surface, self.camera_x, self.camera_y, self.zoom)
        
        # 移除已到达的舰队
        for fleet in fleets_to_remove:
            self.moving_fleets.remove(fleet)
        
        # 更新所有正在围攻/占领中的星球（暂停时不更新）
        if not self.paused and not self.game_over:
            self.update_sieges()
        
        # 检查胜负条件（仅在游戏未结束时检查）
        if not self.game_over:
            self.check_win_condition()

        # 更新工人挖矿（每帧消耗食物，每帧生成矿物）- 暂停时不更新
        if not self.paused and not self.game_over:
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
                    
                    # AI星球的被动舰船生产（应用难度系数）
                    elif not planet.is_star and planet.owner == 'ai':
                        # AI的工业区划产生舰船（受难度影响）
                        # 基础速率：每个工业每30秒建造1艘舰船，乘以难度系数
                        ships_per_second = planet.industrial_districts / 30.0 * getattr(self, 'ai_resource_bonus', 1.0)
                        ships_this_frame = ships_per_second * frame_time
                        
                        # AI不需要资源，直接生产（简化处理）
                        planet.fleet_count += int(ships_this_frame)
                        if random.random() < (ships_this_frame - int(ships_this_frame)):
                            planet.fleet_count += 1  # 概率性增加不足1的部分

        
        # Draw player resource bar at the top
        # 根据屏幕大小调整资源栏高度
        resource_bar_height = 50 if W >= 800 else 30
        resource_surface = pygame.Surface((W, resource_bar_height))
        resource_surface.fill(BLACK)
        resource_surface.set_alpha(200)
        surface.blit(resource_surface, (0, 0))
        
        # Draw player food and workers status
        food_text = f"Food: {int(self.player_food)}"
        workers_text = f"Workers: {int(self.workers)}" if W < 400 else f"Available Workers: {int(self.workers)}"  # 小屏幕缩短文字
        
        food_surf = font_medium.render(food_text, True, (100, 200, 100))  # 绿色
        workers_surf = font_medium.render(workers_text, True, YELLOW)
        
        text_y_offset = 4 if W < 400 else 8
        surface.blit(food_surf, (4, text_y_offset))
        surface.blit(workers_surf, (4, text_y_offset + (14 if W < 400 else 20)))
        
        # 按钮布局（从左到右）：根据屏幕大小动态调整
        # 小屏幕模式：缩小按钮和间距
        btn_scale = 0.4 if W < 400 else 1.0
        btn_h = int(34 * btn_scale) if W < 400 else 34
        btn_spacing = 4 if W < 400 else 10
        text_offset_y = 3 if W < 400 else 8
        
        # 绘制暂停/恢复按钮
        pause_btn_w = int(100 * btn_scale) if W < 400 else 100
        pause_btn_x = int(W * 0.28) if W < 400 else 220
        pause_btn_y = 2 if W < 400 else 8
        pause_btn_rect = pygame.Rect(pause_btn_x, pause_btn_y, pause_btn_w, btn_h)
        pause_btn_color = (100, 100, 200) if not self.paused else (200, 100, 100)
        pygame.draw.rect(surface, pause_btn_color, pause_btn_rect)
        pygame.draw.rect(surface, WHITE, pause_btn_rect, 1 if W < 400 else 2)
        pause_text = "Resume" if self.paused else "Pause"
        text_surf = font_tiny.render(pause_text, True, WHITE)
        text_x = pause_btn_x + (pause_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, pause_btn_y + text_offset_y))
        self._pause_btn_rect = pause_btn_rect
        
        # Draw "Buy Worker" button (costs 5 food)
        buy_worker_btn_w = int(72 * btn_scale) if W < 400 else 180
        buy_worker_btn_x = pause_btn_x + pause_btn_w + btn_spacing
        buy_worker_btn_y = pause_btn_y
        buy_worker_btn_rect = pygame.Rect(buy_worker_btn_x, buy_worker_btn_y, buy_worker_btn_w, btn_h)
        can_afford = self.player_food >= 5
        # Change button color based on affordability
        btn_color = (60, 120, 60) if can_afford else (80, 80, 80)
        pygame.draw.rect(surface, btn_color, buy_worker_btn_rect)
        pygame.draw.rect(surface, WHITE, buy_worker_btn_rect, 1 if W < 400 else 2)
        buy_worker_text = "Buy(5F)" if W < 400 else "Buy Worker (5F)"
        text_surf = font_tiny.render(buy_worker_text, True, WHITE)
        text_x = buy_worker_btn_x + (buy_worker_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, buy_worker_btn_y + text_offset_y))
        self._buy_worker_rect = buy_worker_btn_rect
        
        # 右侧按钮从右往左排列：Exit -> Ores -> Trade -> Units
        side_btn_w = int(85 * btn_scale) if W < 400 else 70
        side_btn_spacing = 5 if W < 400 else 8
        
        # Draw "Exit" button on the top bar (far right)
        exit_btn_x = W - side_btn_w - (4 if W < 400 else 10)
        exit_btn_y = pause_btn_y
        exit_btn_rect = pygame.Rect(exit_btn_x, exit_btn_y, side_btn_w, btn_h)
        pygame.draw.rect(surface, (180, 60, 60), exit_btn_rect)
        pygame.draw.rect(surface, WHITE, exit_btn_rect, 1 if W < 400 else 2)
        text_surf = font_tiny.render('Exit', True, WHITE)
        text_x = exit_btn_x + (side_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, exit_btn_y + text_offset_y))
        self._quit_btn_rect = exit_btn_rect
        
        # Draw "Ores" button (to the left of Exit)
        ores_btn_x = exit_btn_x - side_btn_w - side_btn_spacing
        ores_btn_y = pause_btn_y
        ores_btn_rect = pygame.Rect(ores_btn_x, ores_btn_y, side_btn_w, btn_h)
        pygame.draw.rect(surface, (60, 60, 90), ores_btn_rect)
        pygame.draw.rect(surface, WHITE, ores_btn_rect, 1 if W < 400 else 2)
        text_surf = font_tiny.render('Ores', True, WHITE)
        text_x = ores_btn_x + (side_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, ores_btn_y + text_offset_y))
        self._ores_button_rect = ores_btn_rect
        
        # Draw "Trade" button (to the left of Ores)
        trade_btn_x = ores_btn_x - side_btn_w - side_btn_spacing
        trade_btn_y = pause_btn_y
        trade_btn_rect = pygame.Rect(trade_btn_x, trade_btn_y, side_btn_w, btn_h)
        pygame.draw.rect(surface, (80, 60, 90), trade_btn_rect)
        pygame.draw.rect(surface, WHITE, trade_btn_rect, 1 if W < 400 else 2)
        text_surf = font_tiny.render('Trade', True, WHITE)
        text_x = trade_btn_x + (side_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, trade_btn_y + text_offset_y))
        self._trade_button_rect = trade_btn_rect
        
        # Draw "Units" button (to the left of Trade)
        units_btn_x = trade_btn_x - side_btn_w - side_btn_spacing
        units_btn_y = pause_btn_y
        units_btn_rect = pygame.Rect(units_btn_x, units_btn_y, side_btn_w, btn_h)
        pygame.draw.rect(surface, (90, 60, 60), units_btn_rect)
        pygame.draw.rect(surface, WHITE, units_btn_rect, 1 if W < 400 else 2)
        text_surf = font_tiny.render('Units', True, WHITE)
        text_x = units_btn_x + (side_btn_w - text_surf.get_width()) // 2
        surface.blit(text_surf, (text_x, units_btn_y + text_offset_y))
        self._units_button_rect = units_btn_rect

        # draw selected info panel
        if self.selected_body:
            # 小屏幕使用更合适的宽度比例
            info_panel_width = int(W * 0.45) if W < 400 else W//3
            info_surface = pygame.Surface((info_panel_width, H))
            info_surface.fill(WHITE)
            info_surface.set_alpha(240)
            surface.blit(info_surface, (0, 0))
            name_surf = font_medium.render(self.selected_body.name, True, BLACK)
            name_x = 4 if W < 400 else 10
            name_y = resource_bar_height + 2 if W < 400 else 10
            surface.blit(name_surf, (name_x, name_y))
            
            # 显示舰船数量（对所有星体通用）
            fleet_count = getattr(self.selected_body, 'fleet_count', 0)
            
            # 计算基本位置偏移
            base_y = name_y + name_surf.get_height() + (4 if W < 400 else 5)
            line_spacing = 18 if W < 400 else 25
            
            # 检查是否正在战斗/占领中
            if getattr(self.selected_body, 'under_siege', False):
                # 显示战斗/占领状态
                elapsed = time.time() - self.selected_body.siege_start_time
                progress = min(100, (elapsed / self.selected_body.siege_duration) * 100)
                
                if self.selected_body.defender_count == 0:
                    # 占领中
                    status_text = f"Occupying... {progress:.0f}%"
                    fleet_text = f"Attacker: {self.selected_body.attacker_count} ships"
                else:
                    # 战斗中
                    status_text = f"Battle in progress... {progress:.0f}%"
                    fleet_text = f"Atk:{self.selected_body.attacker_count} vs Def:{self.selected_body.defender_count}"
                
                status_surf = font_small.render(status_text, True, RED)
                surface.blit(status_surf, (name_x, base_y))
                fleet_surf = font_small.render(fleet_text, True, RED)
                surface.blit(fleet_surf, (name_x, base_y + line_spacing))
                self._fleet_text_rect = pygame.Rect(name_x, base_y + line_spacing, fleet_surf.get_width(), fleet_surf.get_height())
                y_offset = base_y + line_spacing * 2  # 战斗状态下，后续内容从更低位置开始
            else:
                # 正常显示
                fleet_text = f"Ships: {fleet_count}"
                fleet_color = BLUE if fleet_count > 0 else (150, 150, 150)
                fleet_surf = font_small.render(fleet_text, True, fleet_color)
                surface.blit(fleet_surf, (name_x, base_y))
                # 添加点击提示
                hint_text = "(Click to deploy)"
                hint_color = (120, 120, 120) if fleet_count > 0 else (80, 80, 80)
                hint_surf = font_tiny.render(hint_text, True, hint_color)
                surface.blit(hint_surf, (name_x + fleet_surf.get_width() + 5, base_y + 2))
                # 存储这个文本的矩形区域用于点击检测
                self._fleet_text_rect = pygame.Rect(name_x, base_y, fleet_surf.get_width(), fleet_surf.get_height())
                y_offset = base_y + line_spacing  # 正常状态下的偏移
            
            # 显示最近一次战斗小结（如果有）
            if hasattr(self.selected_body, 'last_battle_info') and self.selected_body.last_battle_info:
                battle = self.selected_body.last_battle_info
                
                # 标题
                battle_title = font_small.render("Last Battle:", True, (180, 0, 0))
                surface.blit(battle_title, (name_x, y_offset))
                y_offset += line_spacing
                
                # 进攻方信息
                atk_owner = "Player" if battle['attacker_owner'] == 'player' else "AI"
                atk_change = battle['attacker_ships_after'] - battle['attacker_ships_before']
                atk_sign = "+" if atk_change >= 0 else ""
                atk_text = f"{atk_owner}: {battle['attacker_ships_before']}→{battle['attacker_ships_after']} ({atk_sign}{atk_change}) ships"
                atk_color = (0, 100, 200) if battle['attacker_owner'] == 'player' else (200, 100, 0)
                surface.blit(font_tiny.render(atk_text, True, atk_color), (name_x + 5, y_offset))
                y_offset += line_spacing - 5
                
                # 单位变化
                atk_unit_change = battle['attacker_units_after'] - battle['attacker_units_before']
                atk_unit_sign = "+" if atk_unit_change >= 0 else ""
                atk_unit_text = f"  Units: {battle['attacker_units_before']}→{battle['attacker_units_after']} ({atk_unit_sign}{atk_unit_change})"
                surface.blit(font_tiny.render(atk_unit_text, True, atk_color), (name_x + 5, y_offset))
                y_offset += line_spacing - 5
                
                # 防守方信息
                if battle['defender_owner'] == 'neutral':
                    def_text = "Neutral: No resistance"
                    def_color = (120, 120, 120)
                    surface.blit(font_tiny.render(def_text, True, def_color), (name_x + 5, y_offset))
                    y_offset += line_spacing - 5
                else:
                    def_owner = "Player" if battle['defender_owner'] == 'player' else "AI"
                    def_change = battle['defender_ships_after'] - battle['defender_ships_before']
                    def_sign = "+" if def_change >= 0 else ""
                    def_text = f"{def_owner}: {battle['defender_ships_before']}→{battle['defender_ships_after']} ({def_sign}{def_change}) ships"
                    def_color = (0, 100, 200) if battle['defender_owner'] == 'player' else (200, 100, 0)
                    surface.blit(font_tiny.render(def_text, True, def_color), (name_x + 5, y_offset))
                    y_offset += line_spacing - 5
                    
                    # 单位变化
                    def_unit_change = battle['defender_units_after'] - battle['defender_units_before']
                    def_unit_sign = "+" if def_unit_change >= 0 else ""
                    def_unit_text = f"  Units: {battle['defender_units_before']}→{battle['defender_units_after']} ({def_unit_sign}{def_unit_change})"
                    surface.blit(font_tiny.render(def_unit_text, True, def_color), (name_x + 5, y_offset))
                    y_offset += line_spacing - 5
                
                # 胜利方
                if battle['winner'] == 'draw':
                    winner_text = "Result: Draw (mutual destruction)"
                    winner_color = (100, 100, 100)
                else:
                    winner_name = "Player" if battle['winner'] == 'player' else "AI"
                    winner_text = f"Winner: {winner_name}"
                    winner_color = (0, 150, 0) if battle['winner'] == battle['attacker_owner'] else (150, 0, 0)
                surface.blit(font_tiny.render(winner_text, True, winner_color), (name_x + 5, y_offset))
                y_offset += line_spacing
            
            if self.selected_body.is_star:
                base_text = f"Starbase Level: {self.selected_body.starbase}"
                base_surf = font_small.render(base_text, True, BLACK)
                surface.blit(base_surf, (name_x, y_offset))
            else:
                type_text = f"Type: {self.selected_body.planet_type.value}"
                city_text = f"City: {self.selected_body.city_districts}"
                agri_text = f"Agri: {self.selected_body.agri_districts}"
                indust_text = f"Indust: {self.selected_body.industrial_districts}"
                workers_on_planet = f"Workers: {self.selected_body.assigned_workers}"
                
                # 第一列信息 - 左上方
                item_spacing = 20 if W < 400 else 30
                surface.blit(font_small.render(type_text, True, BLACK), (name_x, y_offset))
                surface.blit(font_small.render(city_text, True, BLACK), (name_x, y_offset + item_spacing))
                surface.blit(font_small.render(agri_text, True, BLACK), (name_x, y_offset + item_spacing * 2))
                surface.blit(font_small.render(indust_text, True, BLACK), (name_x, y_offset + item_spacing * 3))
                surface.blit(font_small.render(workers_on_planet, True, BLUE), (name_x, y_offset + item_spacing * 4))
                
                # 显示该星球“盛产”标签（不显示精确上限）
                rich_y = H - (60 if W < 400 else 90)
                rich_text = "Rich in: " + ", ".join(self.selected_body.rich_in)
                surface.blit(font_small.render(rich_text, True, (80, 80, 200)), (name_x, rich_y - 60))

                # 根据开采进度显示提示：过度开发 / 枯萎（不显示数值）
                initial = max(1, getattr(self.selected_body, '_initial_total_ore', 1))
                mined = sum(self.selected_body.mined_ore.values())
                remaining = max(0, initial - mined)
                pct_remaining = remaining / initial * 100.0
                warning_text = None
                if mined >= initial * 0.5:
                    warning_text = "Overexploited"
                if pct_remaining <= 10.0:
                    warning_text = "Depleted"
                if warning_text:
                    # 红色/橙色提示
                    warn_color = (220, 100, 40) if warning_text == "Overexploited" else (160, 60, 60)
                    surface.blit(font_small.render(warning_text, True, warn_color), (name_x, rich_y - 45))
                
                # "View Mined" button
                view_mined_color = BLUE if sum(self.selected_body.mined_ore.values()) > 0 else (150,150,150)
                view_mined_text = "[View Mined]"
                view_mined_surf = font_small.render(view_mined_text, True, view_mined_color)
                surface.blit(view_mined_surf, (name_x, rich_y))

                # Dispatch and recall worker buttons - bottom
                # 只有已探索过的星球才能派遣工人
                is_explored = self.selected_body in self.player_explored_bodies
                can_dispatch = is_explored and int(self.workers) > 0
                dispatch_btn_color = BLUE if can_dispatch else (150, 150, 150)
                recall_btn_color = BLUE if self.selected_body.assigned_workers > 0 else (150, 150, 150)
                
                # 如果未探索，显示提示信息
                if not is_explored:
                    dispatch_text = f"[+Dispatch] (未探索)"
                else:
                    dispatch_text = f"[+Dispatch]"
                recall_text = f"[-Recall]"
                
                dispatch_surf = font_small.render(dispatch_text, True, dispatch_btn_color)
                recall_surf = font_small.render(recall_text, True, recall_btn_color)
                
                # Batch buttons
                dispatch10_text = "[+Dispatch 10]"
                recall_all_text = "[-Recall All]"
                can_dispatch10 = is_explored and int(self.workers) >= 10
                dispatch10_btn_color = BLUE if can_dispatch10 else (150, 150, 150)
                recall_all_btn_color = BLUE if self.selected_body.assigned_workers > 0 else (150, 150, 150)
                dispatch10_surf = font_small.render(dispatch10_text, True, dispatch10_btn_color)
                recall_all_surf = font_small.render(recall_all_text, True, recall_all_btn_color)
                
                # Button positions: display on separate lines at bottom
                btn_spacing_y = 15 if W < 400 else 30
                btn_spacing_x = 110 if W < 400 else 130
                surface.blit(dispatch_surf, (name_x, H - btn_spacing_y * 2))
                surface.blit(dispatch10_surf, (name_x + btn_spacing_x, H - btn_spacing_y * 2))
                surface.blit(recall_surf, (name_x, H - btn_spacing_y))
                surface.blit(recall_all_surf, (name_x + btn_spacing_x, H - btn_spacing_y))

        # 如果开启了已开采弹窗，绘制弹窗（覆盖在界面上）
        if getattr(self, 'show_mined_popup', False) and self.mined_popup_body:
            popup_w = int(W * 0.7) if W < 400 else W // 2
            popup_h = int(H * 0.5) if W < 400 else H // 2
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            # border
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            # title
            title = f"Mined on {self.mined_popup_body.name}"
            title_y = 5 if W < 400 else 10
            popup_surf.blit(font_medium.render(title, True, BLACK), (5, title_y))
            # list ores
            y = 30 if W < 400 else 50
            line_spacing = 16 if W < 400 else 26
            for ore in ['Gold','Silver','Rare Earth','Copper','Aluminum']:
                amt = int(self.mined_popup_body.mined_ore.get(ore, 0))
                line = f"{ore}: {amt}"
                popup_surf.blit(font_small.render(line, True, ORE_COLORS.get(ore, BLACK)), (5, y))
                y += line_spacing
            # close button
            close_w = 50 if W < 400 else 70
            close_h = 20 if W < 400 else 26
            close_rect = pygame.Rect(popup_w - close_w - 5, 5, close_w, close_h)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            close_text_surf = font_small.render('Close', True, WHITE)
            close_text_x = close_rect.x + (close_w - close_text_surf.get_width()) // 2
            popup_surf.blit(close_text_surf, (close_text_x, close_rect.y + 2))
            surface.blit(popup_surf, (popup_x, popup_y))
            # store popup rect for click handling
            self._popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # 如果开启了全局矿物总数弹窗，绘制弹窗（覆盖在界面上）
        if getattr(self, 'show_ore_popup', False) and getattr(self, '_ore_popup_totals', None):
            popup_w = int(W * 0.7) if W < 400 else W // 2
            popup_h = int(H * 0.5) if W < 400 else H // 2
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            title_y = 5 if W < 400 else 10
            popup_surf.blit(font_medium.render('Global Ores', True, BLACK), (5, title_y))
            y = 30 if W < 400 else 50
            line_spacing = 16 if W < 400 else 26
            for ore in ['Gold','Silver','Rare Earth','Copper','Aluminum']:
                amt = int(self._ore_popup_totals.get(ore, 0))
                line = f"{ore}: {amt}"
                popup_surf.blit(font_small.render(line, True, ORE_COLORS.get(ore, BLACK)), (5, y))
                y += line_spacing
            close_w = 50 if W < 400 else 70
            close_h = 20 if W < 400 else 26
            close_rect = pygame.Rect(popup_w - close_w - 5, 5, close_w, close_h)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            close_text_surf = font_small.render('Close', True, WHITE)
            close_text_x = close_rect.x + (close_w - close_text_surf.get_width()) // 2
            popup_surf.blit(close_text_surf, (close_text_x, close_rect.y + 2))
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
            popup_w = int(W * 0.85) if W < 400 else int(W * 0.6)
            popup_h = int(H * 0.8) if W < 400 else int(H * 0.7)
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            
            # 调整标题和按钮大小
            title_x = 5 if W < 400 else 10
            title_y = 5 if W < 400 else 10
            popup_surf.blit(font_big.render('Trade', True, BLACK), (title_x, title_y))

            # Close button
            close_w = 45 if W < 400 else 70
            close_h = 18 if W < 400 else 26
            close_rect = pygame.Rect(popup_w - close_w - 5, 5, close_w, close_h)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            close_text_surf = font_medium.render('Close', True, WHITE)
            close_text_x = close_rect.x + (close_w - close_text_surf.get_width()) // 2
            popup_surf.blit(close_text_surf, (close_text_x, close_rect.y + 2))

            # Buy / Sell selector
            btn_w = 55 if W < 400 else 120
            btn_h = 20 if W < 400 else 28
            btn_y = 28 if W < 400 else 60
            buy_rect = pygame.Rect(5, btn_y, btn_w, btn_h)
            sell_rect = pygame.Rect(5 + btn_w + 5, btn_y, btn_w, btn_h)
            pygame.draw.rect(popup_surf, (100,100,140), buy_rect)
            pygame.draw.rect(popup_surf, (100,100,140), sell_rect)
            buy_text_surf = font_medium.render('Buy', True, WHITE)
            sell_text_surf = font_medium.render('Sell', True, WHITE)
            popup_surf.blit(buy_text_surf, (buy_rect.x + (btn_w - buy_text_surf.get_width()) // 2, buy_rect.y + 3))
            popup_surf.blit(sell_text_surf, (sell_rect.x + (btn_w - sell_text_surf.get_width()) // 2, sell_rect.y + 3))
            # store selector rects for clicks (absolute coords)
            self._trade_buy_selector_rect = pygame.Rect(popup_x + buy_rect.x, popup_y + buy_rect.y, buy_rect.w, buy_rect.h)
            self._trade_sell_selector_rect = pygame.Rect(popup_x + sell_rect.x, popup_y + sell_rect.y, sell_rect.w, sell_rect.h)

            y = btn_y + btn_h + (8 if W < 400 else 12)
            # If selling view, show holdings and sell buttons
            line_spacing = 18 if W < 400 else 28
            text_x = 5 if W < 400 else 10
            if self.trade_view == 'sell':
                popup_surf.blit(font_medium.render('Holdings (sellable):', True, BLACK), (text_x, y))
                y += line_spacing
                # aggregate mined ores across planets + player_stock
                totals = self.aggregate_mined_totals()
                # add player_stock
                for ore in self.player_stock:
                    totals[ore] = totals.get(ore, 0) + int(self.player_stock.get(ore, 0))
                # reset action button list
                self._trade_action_buttons = []
                
                # 按钮尺寸根据屏幕大小调整 (PiTFT增大按钮)
                btn_w = 45 if W < 400 else 80
                btn_h = 20 if W < 400 else 20
                btn_x_base = popup_w - btn_w * 3 - 15 if W < 400 else 220
                
                for ore in ['Gold','Silver']:
                    amt = int(totals.get(ore, 0))
                    sell_price = self.current_trade_prices.get(ore, self.trade_price_base.get(ore, 0.0)) * 0.9
                    ore_text = f"{ore}: {amt} ${sell_price:.1f}" if W < 400 else f"{ore}: {amt}  Sell ${sell_price:.2f}"
                    popup_surf.blit(font_medium.render(ore_text, True, BLACK), (text_x, y))
                    # sell buttons: Sell 10, Sell 50, Sell All
                    b10_rect = pygame.Rect(btn_x_base, y, btn_w, btn_h)
                    b50_rect = pygame.Rect(btn_x_base + btn_w + 3, y, btn_w, btn_h)
                    ball_rect = pygame.Rect(btn_x_base + (btn_w + 3) * 2, y, btn_w, btn_h)
                    
                    btn_text_10 = 'S10' if W < 400 else '[Sell 10]'
                    btn_text_50 = 'S50' if W < 400 else '[Sell 50]'
                    btn_text_all = 'All' if W < 400 else '[Sell All]'
                    
                    popup_surf.blit(font_medium.render(btn_text_10, True, BLUE), (b10_rect.x + 2, b10_rect.y))
                    popup_surf.blit(font_medium.render(btn_text_50, True, BLUE), (b50_rect.x + 2, b50_rect.y))
                    popup_surf.blit(font_medium.render(btn_text_all, True, BLUE), (ball_rect.x + 2, ball_rect.y))
                    # store absolute rects and metadata
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b10_rect.x, popup_y + b10_rect.y, b10_rect.w, b10_rect.h), 'action': 'sell', 'ore': ore, 'qty': 10})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b50_rect.x, popup_y + b50_rect.y, b50_rect.w, b50_rect.h), 'action': 'sell', 'ore': ore, 'qty': 50})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + ball_rect.x, popup_y + ball_rect.y, ball_rect.w, ball_rect.h), 'action': 'sell', 'ore': ore, 'qty': 'all'})
                    y += line_spacing

                # food and workers
                food_sell_price = self.current_trade_prices.get('Food', self.trade_price_base.get('Food', 0.0)) * 0.9
                food_text = f"Food: {int(self.player_food)} ${food_sell_price:.1f}" if W < 400 else f"Food: {int(self.player_food)}  Sell ${food_sell_price:.2f}"
                popup_surf.blit(font_medium.render(food_text, True, BLACK), (text_x, y))
                f10_rect = pygame.Rect(btn_x_base, y, btn_w, btn_h)
                fall_rect = pygame.Rect(btn_x_base + btn_w + 3, y, btn_w, btn_h)
                popup_surf.blit(font_medium.render('S10' if W < 400 else '[Sell 10]', True, BLUE), (f10_rect.x + 2, f10_rect.y))
                popup_surf.blit(font_medium.render('All' if W < 400 else '[Sell All]', True, BLUE), (fall_rect.x + 2, fall_rect.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + f10_rect.x, popup_y + f10_rect.y, f10_rect.w, f10_rect.h), 'action': 'sell_food', 'qty': 10})
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fall_rect.x, popup_y + fall_rect.y, fall_rect.w, fall_rect.h), 'action': 'sell_food', 'qty': 'all'})
                y += line_spacing
                worker_sell_price = self.current_trade_prices.get('Worker', self.trade_price_base.get('Worker', 0.0)) * 0.9
                worker_text = f"Workers: {int(self.workers)} ${worker_sell_price:.1f}" if W < 400 else f"Workers (unassigned): {int(self.workers)}  Sell ${worker_sell_price:.2f}"
                popup_surf.blit(font_medium.render(worker_text, True, BLACK), (text_x, y))
                w1_rect = pygame.Rect(btn_x_base + btn_w + 3, y, btn_w - 10 if W < 400 else 70, btn_h)
                popup_surf.blit(font_medium.render('S1' if W < 400 else '[Sell 1]', True, BLUE), (w1_rect.x + 2, w1_rect.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + w1_rect.x, popup_y + w1_rect.y, w1_rect.w, w1_rect.h), 'action': 'sell_worker', 'qty': 1})
                y += line_spacing
                popup_surf.blit(font_medium.render(f"USD: ${int(self.player_usd)}", True, BLACK), (text_x, y))

            else:
                # buy view or default - show dynamic prices and buy buttons
                popup_surf.blit(font_medium.render('Buy using USD (prices fluctuate)' if W < 400 else 'Buy using USD (prices fluctuate ±50%)', True, BLACK), (text_x, y))
                y += line_spacing
                # prepare action list
                self._trade_action_buttons = []
                
                # 按钮尺寸根据屏幕大小调整 (PiTFT增大按钮)
                btn_w = 45 if W < 400 else 70
                btn_h = 20 if W < 400 else 20
                btn_x_base = popup_w - btn_w * 2 - 10 if W < 400 else 220
                
                for ore in ['Gold','Silver']:
                    price = self.current_trade_prices.get(ore, 0.0)
                    popup_surf.blit(font_medium.render(f"{ore}: ${price:.2f}", True, BLACK), (text_x, y))
                    b1 = pygame.Rect(btn_x_base, y, btn_w, btn_h)
                    b5 = pygame.Rect(btn_x_base + btn_w + 3, y, btn_w, btn_h)
                    popup_surf.blit(font_medium.render('B1' if W < 400 else '[Buy 1]', True, BLUE), (b1.x + 2, b1.y))
                    popup_surf.blit(font_medium.render('B5' if W < 400 else '[Buy 5]', True, BLUE), (b5.x + 2, b5.y))
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b1.x, popup_y + b1.y, b1.w, b1.h), 'action': 'buy', 'ore': ore, 'qty': 1})
                    self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + b5.x, popup_y + b5.y, b5.w, b5.h), 'action': 'buy', 'ore': ore, 'qty': 5})
                    y += line_spacing
                # food
                price = self.current_trade_prices.get('Food', 0.0)
                popup_surf.blit(font_medium.render(f"Food: ${price:.2f}", True, BLACK), (text_x, y))
                fb10 = pygame.Rect(btn_x_base, y, btn_w, btn_h)
                fb50 = pygame.Rect(btn_x_base + btn_w + 3, y, btn_w, btn_h)
                popup_surf.blit(font_medium.render('B10' if W < 400 else '[Buy 10]', True, BLUE), (fb10.x + 2, fb10.y))
                popup_surf.blit(font_medium.render('B50' if W < 400 else '[Buy 50]', True, BLUE), (fb50.x + 2, fb50.y))
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fb10.x, popup_y + fb10.y, fb10.w, fb10.h), 'action': 'buy_food', 'qty': 10})
                self._trade_action_buttons.append({'rect': pygame.Rect(popup_x + fb50.x, popup_y + fb50.y, fb50.w, fb50.h), 'action': 'buy_food', 'qty': 50})

            surface.blit(popup_surf, (popup_x, popup_y))
            # store rects for click handling (we only need close rect and the popup rect)
            self._trade_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._trade_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # Unit purchase popup
        if getattr(self, 'show_unit_popup', False):
            popup_w = int(W * 0.9) if W < 400 else int(W * 0.7)
            popup_h = int(H * 0.85)  # 增加高度以容纳更多单位
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            
            # 获取所有单位列表
            all_units = []
            category = 'Warrior'
            for unit_name, unit_data in self.unit_catalog.get(category, {}).items():
                all_units.append((unit_name, unit_data, category))
            
            # 分页设置
            units_per_page = 2 if W < 400 else 3
            total_pages = (len(all_units) + units_per_page - 1) // units_per_page
            current_page = getattr(self, 'unit_popup_page', 0)
            current_page = max(0, min(current_page, total_pages - 1))
            self.unit_popup_page = current_page
            
            # 标题显示当前页码
            title_text = f'Units {current_page + 1}/{total_pages}' if W < 400 else f'Warrior Units (Page {current_page + 1}/{total_pages})'
            title_x = 5 if W < 400 else 10
            title_y = 5 if W < 400 else 10
            popup_surf.blit(font_medium.render(title_text, True, BLACK), (title_x, title_y))

            # Close button
            close_w = 45 if W < 400 else 70
            close_h = 18 if W < 400 else 26
            close_rect = pygame.Rect(popup_w - close_w - 5, 5, close_w, close_h)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            close_text_surf = font_small.render('Close', True, WHITE)
            close_text_x = close_rect.x + (close_w - close_text_surf.get_width()) // 2
            popup_surf.blit(close_text_surf, (close_text_x, close_rect.y + 2))
            
            # 上一页/下一页按钮
            nav_btn_w = 45 if W < 400 else 80
            nav_btn_h = 22 if W < 400 else 30
            prev_rect = pygame.Rect(5, popup_h - nav_btn_h - 5, nav_btn_w, nav_btn_h)
            next_rect = pygame.Rect(popup_w - nav_btn_w - 5, popup_h - nav_btn_h - 5, nav_btn_w, nav_btn_h)
            
            prev_color = (60, 120, 200) if current_page > 0 else (150, 150, 150)
            next_color = (60, 120, 200) if current_page < total_pages - 1 else (150, 150, 150)
            
            pygame.draw.rect(popup_surf, prev_color, prev_rect)
            pygame.draw.rect(popup_surf, next_color, next_rect)
            pygame.draw.rect(popup_surf, WHITE, prev_rect, 1 if W < 400 else 2)
            pygame.draw.rect(popup_surf, WHITE, next_rect, 1 if W < 400 else 2)
            
            prev_text = '<' if W < 400 else '< Prev'
            next_text = '>' if W < 400 else 'Next >'
            prev_text_surf = font_small.render(prev_text, True, WHITE)
            next_text_surf = font_small.render(next_text, True, WHITE)
            popup_surf.blit(prev_text_surf, (prev_rect.x + (nav_btn_w - prev_text_surf.get_width()) // 2, prev_rect.y + 4))
            popup_surf.blit(next_text_surf, (next_rect.x + (nav_btn_w - next_text_surf.get_width()) // 2, next_rect.y + 4))
            
            self._unit_prev_button = pygame.Rect(popup_x + prev_rect.x, popup_y + prev_rect.y, prev_rect.w, prev_rect.h)
            self._unit_next_button = pygame.Rect(popup_x + next_rect.x, popup_y + next_rect.y, next_rect.w, next_rect.h)
            self._unit_can_prev = current_page > 0
            self._unit_can_next = current_page < total_pages - 1

            y = 28 if W < 400 else 60
            self._unit_buy_buttons = []
            
            # Display player's current resources
            popup_surf.blit(font_small.render(f"USD: ${int(self.player_usd)}", True, (60,60,60)), (title_x, y))
            y += 14 if W < 400 else 28
            # Aggregate available ores (mined + stock) - display in two lines to avoid overlap
            avail_ores = self.aggregate_mined_totals()
            for ore in avail_ores:
                avail_ores[ore] += int(self.player_stock.get(ore, 0))
            
            if W < 400:
                # 小屏幕：显示简化版
                ore_line1 = f"G:{avail_ores.get('Gold',0)} S:{avail_ores.get('Silver',0)} R:{avail_ores.get('Rare Earth',0)}"
                ore_line2 = f"C:{avail_ores.get('Copper',0)} A:{avail_ores.get('Aluminum',0)}"
            else:
                ore_line1 = f"Gold: {avail_ores.get('Gold',0)}  Silver: {avail_ores.get('Silver',0)}  Rare Earth: {avail_ores.get('Rare Earth',0)}"
                ore_line2 = f"Copper: {avail_ores.get('Copper',0)}  Aluminum: {avail_ores.get('Aluminum',0)}"
            
            popup_surf.blit(font_small.render(ore_line1, True, (60,60,60)), (title_x, y))
            y += 13 if W < 400 else 26
            popup_surf.blit(font_small.render(ore_line2, True, (60,60,60)), (title_x, y))
            y += 20 if W < 400 else 40

            # 只显示当前页的单位
            start_idx = current_page * units_per_page
            end_idx = min(start_idx + units_per_page, len(all_units))
            page_units = all_units[start_idx:end_idx]
            
            for unit_name, unit_data, category in page_units:
                hp = unit_data['hp']
                attack = unit_data['attack']
                price = unit_data['price']
                special = unit_data.get('special', None)
                
                # Unit name and attributes (bold display)
                unit_line = f"{unit_name} HP:{hp} ATK:{attack}" if W < 400 else f"{unit_name}  HP:{hp}  ATK:{attack}"
                popup_surf.blit(font_medium.render(unit_line, True, BLACK), (title_x, y))
                y += 16 if W < 400 else 22
                
                # Special ability description
                if special == 'anti_starbot':
                    special_text = "+100% vs Starbot" if W < 400 else "Special: +100% vs Starbot"
                    popup_surf.blit(font_small.render(special_text, True, (200, 50, 50)), (title_x, y))
                    y += 14 if W < 400 else 18
                elif special == 'convert':
                    special_text = "Convert enemy" if W < 400 else "Special: Convert enemy"
                    popup_surf.blit(font_small.render(special_text, True, (50, 100, 200)), (title_x, y))
                    y += 14 if W < 400 else 18
                else:
                    y += 3 if W < 400 else 5
                
                # Price details - split into multiple lines if too long to avoid overlap
                price_parts = []
                for res, amt in price.items():
                    if res == 'USD':
                        price_parts.append(f"${amt}")
                    else:
                        # 缩短矿物名称以适配小屏幕
                        if W < 400:
                            res_short = {'Gold': 'G', 'Silver': 'S', 'Rare Earth': 'RE', 'Copper': 'C', 'Aluminum': 'A'}.get(res, res)
                            price_parts.append(f"{amt}{res_short}")
                        else:
                            price_parts.append(f"{amt} {res}")
                
                # Split price display into two lines if there are many resources
                if len(price_parts) > 3:
                    # First line: first 3 items
                    price_line1 = "Price: " + ", ".join(price_parts[:3])
                    popup_surf.blit(font_small.render(price_line1, True, (80,80,80)), (title_x, y))
                    y += 14 if W < 400 else 18
                    # Second line: remaining items
                    price_line2 = "       " + ", ".join(price_parts[3:])
                    popup_surf.blit(font_small.render(price_line2, True, (80,80,80)), (title_x, y))
                    y -= 14 if W < 400 else 18  # Move back up for button positioning
                else:
                    price_text = ("P: " if W < 400 else "Price: ") + ", ".join(price_parts)
                    popup_surf.blit(font_small.render(price_text, True, (80,80,80)), (title_x, y))
                
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
                btn_w = 60 if W < 400 else 110
                btn_h = 26 if W < 400 else 32
                btn_x = popup_w - btn_w - 5 if W < 400 else popup_w - 130
                btn_y = y - 4
                buy_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                pygame.draw.rect(popup_surf, buy_color, buy_rect)
                pygame.draw.rect(popup_surf, WHITE, buy_rect, 1 if W < 400 else 2)  # white border
                buy_text_surf = font_small.render('Buy', True, WHITE)
                popup_surf.blit(buy_text_surf, (buy_rect.x + (btn_w - buy_text_surf.get_width()) // 2, buy_rect.y + 4))
                
                # 存储按钮信息
                self._unit_buy_buttons.append({
                    'rect': pygame.Rect(popup_x + buy_rect.x, popup_y + buy_rect.y, buy_rect.w, buy_rect.h),
                    'unit_name': unit_name,
                    'category': category,
                    'can_afford': can_afford,
                    'price': price,
                    'hp': hp,
                    'attack': attack,
                    'special': unit_data.get('special', None)
                })
                
                # Add extra spacing if price was split into two lines
                if len(price_parts) > 3:
                    y += 35 if W < 400 else 50
                else:
                    y += 28 if W < 400 else 40

            # Display current owned units count at bottom
            y += 10 if W < 400 else 15
            owned_text = f"Owned: {len(self.player_units)}" if W < 400 else f"Owned Units: {len(self.player_units)}"
            popup_surf.blit(font_small.render(owned_text, True, BLUE), (title_x, y))
            
            surface.blit(popup_surf, (popup_x, popup_y))
            self._unit_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._unit_popup_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

        # Unit selection popup (for choosing which units to send with fleet)
        if getattr(self, 'show_unit_select_popup', False):
            popup_w = int(W * 0.7)
            popup_h = int(H * 0.8)
            popup_x = (W - popup_w) // 2
            popup_y = (H - popup_h) // 2
            popup_surf = pygame.Surface((popup_w, popup_h))
            popup_surf.fill(WHITE)
            popup_surf.set_alpha(250)
            pygame.draw.rect(popup_surf, BLACK, popup_surf.get_rect(), 2)
            
            # Title
            ship_count = self.unit_select_ship_count
            max_units = ship_count * 5
            title = f"Select Units to Send ({ship_count} ships, max {max_units} units)"
            popup_surf.blit(font_medium.render(title, True, BLACK), (10, 10))
            
            # Close button
            close_rect = pygame.Rect(popup_w - 80, 10, 70, 26)
            pygame.draw.rect(popup_surf, (200,50,50), close_rect)
            popup_surf.blit(font_small.render('Close', True, WHITE), (popup_w - 60, 12))
            
            # Destination info
            dest_text = f"Destination: {self.unit_select_destination.name}"
            popup_surf.blit(font_small.render(dest_text, True, (80, 80, 80)), (10, 45))
            
            # Selected units count
            selected_count = len(self.selected_units_to_send)
            count_text = f"Selected: {selected_count}/{max_units}"
            count_color = (60, 200, 100) if selected_count <= max_units else RED
            popup_surf.blit(font_small.render(count_text, True, count_color), (10, 65))
            
            # 分页设置
            source_units = getattr(self.unit_select_source, 'units', [])
            units_per_page = 20  # 每页显示20个单位
            total_units = len(source_units)
            total_pages = max(1, (total_units + units_per_page - 1) // units_per_page)
            current_page = getattr(self, 'unit_select_scroll_offset', 0)
            current_page = max(0, min(current_page, total_pages - 1))
            self.unit_select_scroll_offset = current_page
            
            # 显示页码信息
            if total_units > units_per_page:
                page_info = f"Page {current_page + 1}/{total_pages}"
                popup_surf.blit(font_small.render(page_info, True, (100, 100, 100)), (popup_w - 150, 65))
            
            # List all units on source planet
            y = 95
            popup_surf.blit(font_small.render("Available units (click to select):", True, BLACK), (10, y))
            y += 25
            
            self._unit_select_buttons = []
            
            if not source_units:
                popup_surf.blit(font_small.render("No units on this planet", True, (150, 150, 150)), (10, y))
            else:
                # 只显示当前页的单位
                start_idx = current_page * units_per_page
                end_idx = min(start_idx + units_per_page, total_units)
                page_units = source_units[start_idx:end_idx]
                
                for idx, i in enumerate(range(start_idx, end_idx)):
                    unit = source_units[i]
                    unit_name = unit.get('name', 'Unknown')
                    unit_hp = unit.get('hp', 0)
                    unit_atk = unit.get('attack', 0)
                    
                    # Check if this specific unit index is selected
                    is_selected = i in self.selected_units_to_send
                    
                    # Unit info - add index number for clarity
                    unit_text = f"#{i+1} {unit_name}  HP:{unit_hp}  ATK:{unit_atk}"
                    text_color = BLUE if is_selected else BLACK
                    popup_surf.blit(font_small.render(unit_text, True, text_color), (20, y))
                    
                    # Select/Deselect button
                    btn_x = popup_w - 120
                    btn_rect = pygame.Rect(btn_x, y - 2, 100, 20)
                    btn_color = (180, 100, 100) if is_selected else (100, 180, 100)
                    btn_text = "Deselect" if is_selected else "Select"
                    pygame.draw.rect(popup_surf, btn_color, btn_rect)
                    pygame.draw.rect(popup_surf, WHITE, btn_rect, 1)
                    popup_surf.blit(font_small.render(btn_text, True, WHITE), (btn_x + 20, y))
                    
                    # Store button info with unit index
                    self._unit_select_buttons.append({
                        'rect': pygame.Rect(popup_x + btn_x, popup_y + y - 2, 100, 20),
                        'unit_index': i,
                        'is_selected': is_selected
                    })
                    
                    y += 22
            
            # 上一页/下一页按钮（如果有多页）
            if total_pages > 1:
                prev_rect = pygame.Rect(10, popup_h - 90, 80, 30)
                next_rect = pygame.Rect(popup_w - 90, popup_h - 90, 80, 30)
                
                prev_color = (60, 120, 200) if current_page > 0 else (150, 150, 150)
                next_color = (60, 120, 200) if current_page < total_pages - 1 else (150, 150, 150)
                
                pygame.draw.rect(popup_surf, prev_color, prev_rect)
                pygame.draw.rect(popup_surf, next_color, next_rect)
                pygame.draw.rect(popup_surf, WHITE, prev_rect, 2)
                pygame.draw.rect(popup_surf, WHITE, next_rect, 2)
                popup_surf.blit(font_small.render('< Prev', True, WHITE), (prev_rect.x + 15, prev_rect.y + 8))
                popup_surf.blit(font_small.render('Next >', True, WHITE), (next_rect.x + 15, next_rect.y + 8))
                
                self._unit_select_prev_button = pygame.Rect(popup_x + prev_rect.x, popup_y + prev_rect.y, prev_rect.w, prev_rect.h)
                self._unit_select_next_button = pygame.Rect(popup_x + next_rect.x, popup_y + next_rect.y, next_rect.w, next_rect.h)
                self._unit_select_can_prev = current_page > 0
                self._unit_select_can_next = current_page < total_pages - 1
            
            # Confirm button at bottom
            confirm_y = popup_h - 50
            confirm_rect = pygame.Rect(10, confirm_y, 150, 35)
            can_confirm = selected_count > 0 and selected_count <= max_units
            confirm_color = (60, 150, 60) if can_confirm else (120, 120, 120)
            pygame.draw.rect(popup_surf, confirm_color, confirm_rect)
            pygame.draw.rect(popup_surf, WHITE, confirm_rect, 2)
            popup_surf.blit(font_medium.render('Confirm Send', True, WHITE), (confirm_rect.x + 10, confirm_rect.y + 8))
            self._unit_select_confirm_button = pygame.Rect(popup_x + confirm_rect.x, popup_y + confirm_rect.y, confirm_rect.w, confirm_rect.h)
            self._unit_select_can_confirm = can_confirm
            
            surface.blit(popup_surf, (popup_x, popup_y))
            self._unit_select_popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
            self._unit_select_close_rect = pygame.Rect(popup_x + close_rect.x, popup_y + close_rect.y, close_rect.w, close_rect.h)

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
            popup_surf.blit(font_small.render("(Each ship carries 5 units)", True, (100, 100, 100)), (10, 68))
            
            # Show units on this planet
            units_on_planet = getattr(self.fleet_popup_source, 'units', [])
            if units_on_planet:
                y_units = 70
                popup_surf.blit(font_small.render("Units on planet:", True, (100, 50, 150)), (10, y_units))
                y_units += 18
                # Count unit types
                unit_counts = {}
                for unit in units_on_planet:
                    name = unit.get('name', 'Unknown')
                    unit_counts[name] = unit_counts.get(name, 0) + 1
                # Display unit counts
                for unit_name, count in unit_counts.items():
                    unit_text = f"  {unit_name}: {count}"
                    popup_surf.blit(font_small.render(unit_text, True, (60, 60, 120)), (10, y_units))
                    y_units += 16
            
            # Get adjacent bodies
            adjacent = self.get_adjacent_bodies(self.fleet_popup_source)
            
            y = 120  # 调整起始位置，为单位信息留出空间
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
        
        # 游戏结束UI（类似暂停界面）
        if self.game_over:
            # 半透明黑色背景
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            # 胜利/失败文字（英文）
            if self.winner == 'player':
                result_text = "VICTORY!"
                result_color = (100, 255, 100)
                msg = "You conquered the AI's home planet!"
            else:
                result_text = "DEFEAT!"
                result_color = (255, 100, 100)
                msg = "AI conquered your home planet!"
            
            # 绘制结果
            result_surf = font_big.render(result_text, True, result_color)
            result_rect = result_surf.get_rect(center=(W//2, H//2 - 50))
            surface.blit(result_surf, result_rect)
            
            # 绘制消息
            msg_surf = font_medium.render(msg, True, WHITE)
            msg_rect = msg_surf.get_rect(center=(W//2, H//2 + 20))
            surface.blit(msg_surf, msg_rect)
            
            # 提示按ESC返回菜单
            hint_surf = font_small.render("Press ESC to return to menu", True, (200, 200, 200))
            hint_rect = hint_surf.get_rect(center=(W//2, H//2 + 60))
            surface.blit(hint_surf, hint_rect)
        
        # 如果游戏暂停，显示暂停提示（在所有弹窗之上）
        if self.paused and not self.game_over:
            pause_overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 120))
            surface.blit(pause_overlay, (0, 0))
            pause_text_surf = font_big.render("PAUSED", True, WHITE)
            surface.blit(pause_text_surf, pause_text_surf.get_rect(center=(W//2, H//2)))

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
        global pitft
        
        # 游戏结束时，只处理退出按钮，忽略其他所有交互
        if self.game_over:
            if hasattr(self, '_quit_btn_rect') and self._quit_btn_rect.collidepoint(x, y):
                try:
                    if SFX.get('click'):
                        audio_manager.play_sfx(SFX.get('click'))
                except Exception:
                    pass
                
                # 停止LED显示
                clear_all_leds()
                
                # 触发pygame退出事件来正常关闭游戏
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            # 游戏结束时忽略其他所有点击
            return False
        
        # 检查是否点击了退出按钮
        if hasattr(self, '_quit_btn_rect') and self._quit_btn_rect.collidepoint(x, y):
            try:
                if SFX.get('click'):
                    audio_manager.play_sfx(SFX.get('click'))
            except Exception:
                pass
            
            # 停止LED显示
            clear_all_leds()
            
            # 触发pygame退出事件来正常关闭游戏
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return False
        
        # 检查是否点击了暂停按钮
        if hasattr(self, '_pause_btn_rect') and self._pause_btn_rect.collidepoint(x, y):
            self.paused = not self.paused
            try:
                if SFX.get('click'):
                    audio_manager.play_sfx(SFX.get('click'))
            except Exception:
                pass
            return True
        
        # If unit selection popup is open, handle its controls first
        if getattr(self, 'show_unit_select_popup', False):
            # close button
            if hasattr(self, '_unit_select_close_rect') and self._unit_select_close_rect.collidepoint(x, y):
                self.show_unit_select_popup = False
                self.selected_units_to_send = []
                self.unit_select_scroll_offset = 0  # 重置滚动
                return True
            
            # 上一页按钮
            if hasattr(self, '_unit_select_prev_button') and self._unit_select_prev_button.collidepoint(x, y):
                if getattr(self, '_unit_select_can_prev', False):
                    self.unit_select_scroll_offset -= 1
                    try:
                        if SFX.get('slight_click'):
                            audio_manager.play_sfx(SFX.get('slight_click'))
                    except Exception:
                        pass
                return True
            
            # 下一页按钮
            if hasattr(self, '_unit_select_next_button') and self._unit_select_next_button.collidepoint(x, y):
                if getattr(self, '_unit_select_can_next', False):
                    self.unit_select_scroll_offset += 1
                    try:
                        if SFX.get('slight_click'):
                            audio_manager.play_sfx(SFX.get('slight_click'))
                    except Exception:
                        pass
                return True
            
            # Unit select/deselect buttons
            for btn in getattr(self, '_unit_select_buttons', []):
                if btn['rect'].collidepoint(x, y):
                    unit_index = btn['unit_index']
                    max_units = self.unit_select_ship_count * 5
                    
                    if btn['is_selected']:
                        # Deselect - remove index from list
                        if unit_index in self.selected_units_to_send:
                            self.selected_units_to_send.remove(unit_index)
                    else:
                        # Select (if not exceeding limit) - add index to list
                        if len(self.selected_units_to_send) < max_units:
                            self.selected_units_to_send.append(unit_index)
                    return True
            
            # Confirm button
            if hasattr(self, '_unit_select_confirm_button') and self._unit_select_confirm_button.collidepoint(x, y):
                if self._unit_select_can_confirm:
                    # Execute the fleet send with selected units
                    source = self.unit_select_source
                    dest = self.unit_select_destination
                    qty = self.unit_select_ship_count
                    
                    # Get actual unit objects from indices
                    selected_indices = sorted(self.selected_units_to_send, reverse=True)  # Sort in reverse to remove from back
                    units_to_send = []
                    
                    # Collect and remove units from source planet
                    for idx in selected_indices:
                        if idx < len(source.units):
                            unit = source.units.pop(idx)  # Remove and get the unit
                            units_to_send.append(unit)
                    
                    # Deduct ships
                    source.fleet_count -= qty
                    
                    # Create moving fleet with actual unit objects
                    fleet = MovingFleet(source, dest, qty, units_to_send)
                    fleet.owner = 'player'  # 标记舰队所有者为玩家
                    self.moving_fleets.append(fleet)
                    
                    # Play sound
                    try:
                        if SFX.get('ding'):
                            audio_manager.play_sfx(SFX.get('ding'))
                    except Exception:
                        pass
                    
                    # Close popup
                    self.show_unit_select_popup = False
                    self.selected_units_to_send = []
                    print(f"Dispatched {qty} ships carrying {len(units_to_send)} units to {dest.name}")
                    return True
            
            # clicks inside popup are consumed
            if hasattr(self, '_unit_select_popup_rect') and self._unit_select_popup_rect.collidepoint(x, y):
                return True
            return True
        
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
                    # 打开单位选择界面
                    qty = btn['qty']
                    dest = btn['dest']
                    source = self.fleet_popup_source
                    
                    # 保存选择信息并打开单位选择界面
                    self.unit_select_ship_count = qty
                    self.unit_select_destination = dest
                    self.unit_select_source = source
                    self.selected_units_to_send = []
                    self.show_unit_select_popup = True
                    self.show_fleet_popup = False  # 关闭舰队窗口
                    
                    # 播放音效
                    try:
                        if SFX.get('slight_click'):
                            audio_manager.play_sfx(SFX.get('slight_click'))
                    except Exception:
                        pass
                    
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
            
            # 上一页按钮
            if hasattr(self, '_unit_prev_button') and self._unit_prev_button.collidepoint(x, y):
                if getattr(self, '_unit_can_prev', False):
                    self.unit_popup_page -= 1
                    try:
                        if SFX.get('slight_click'):
                            audio_manager.play_sfx(SFX.get('slight_click'))
                    except Exception:
                        pass
                return True
            
            # 下一页按钮
            if hasattr(self, '_unit_next_button') and self._unit_next_button.collidepoint(x, y):
                if getattr(self, '_unit_can_next', False):
                    self.unit_popup_page += 1
                    try:
                        if SFX.get('slight_click'):
                            audio_manager.play_sfx(SFX.get('slight_click'))
                    except Exception:
                        pass
                return True
            
            # buy buttons
            for btn in getattr(self, '_unit_buy_buttons', []):
                if btn['rect'].collidepoint(x, y) and btn.get('can_afford', False):
                    # 检查是否有选中的己方星球
                    target_planet = None
                    if self.selected_body and self.selected_body.owner == 'player':
                        target_planet = self.selected_body
                    else:
                        # 如果没有选中星球，找第一个己方星球
                        for system in self.systems:
                            for planet in system.planets:
                                if planet.owner == 'player':
                                    target_planet = planet
                                    break
                            if target_planet:
                                break
                    
                    if not target_planet:
                        # 没有己方星球，无法购买
                        print("Need to occupy a planet first to purchase units!")
                        return True
                    
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
                        'attack': btn['attack'],
                        'special': btn.get('special', None),  # 特殊能力
                        'last_convert_time': 0  # 僧侣转化冷却时间
                    }
                    # 将单位添加到目标星球
                    target_planet.units.append(unit)
                    # 同时保留在全局列表中（用于统计）
                    self.player_units.append(unit)
                    # 更新星球的舰队数量
                    target_planet.fleet_count += 1
                    
                    print(f"Purchased {unit['name']} at {target_planet.name}")
                    
                    # 播放确认声音（优先 ding）
                    try:
                        if SFX.get('ding'):
                            audio_manager.play_sfx(SFX.get('ding'))
                        elif SFX.get('medium_click'):
                            audio_manager.play_sfx(SFX.get('medium_click'))
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
                                    audio_manager.play_sfx(SFX.get('delete'))
                                elif SFX.get('slight_click'):
                                    audio_manager.play_sfx(SFX.get('slight_click'))
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
                                    audio_manager.play_sfx(SFX.get('delete'))
                            except Exception:
                                pass
                    elif act == 'sell_worker':
                        qty = int(btn.get('qty', 1))
                        if self.workers >= qty:
                            self.workers -= qty
                            self.player_usd += self.current_trade_prices.get('Worker', 0.0) * 0.9 * qty
                            try:
                                if SFX.get('delete'):
                                    audio_manager.play_sfx(SFX.get('delete'))
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
                                    audio_manager.play_sfx(SFX.get('ding'))
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
                                    audio_manager.play_sfx(SFX.get('ding'))
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
                        audio_manager.play_sfx(SFX.get('ding'))
                    elif SFX.get('medium_click'):
                        audio_manager.play_sfx(SFX.get('medium_click'))
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
                            audio_manager.play_sfx(SFX.get('medium_click'))
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
                                audio_manager.play_sfx(SFX.get('ding'))
                        except Exception:
                            pass
                    return True

                # 派遣工人按钮 (Dispatch Worker)
                dispatch_btn_rect = pygame.Rect(10, H - 60, 100, 20)
                if dispatch_btn_rect.collidepoint(x, y):
                    # 只有已探索过的星球才能派遣工人
                    if self.selected_body in self.player_explored_bodies and int(self.workers) > 0:
                        self.selected_body.assigned_workers += 1
                        self.workers -= 1  # 减去1个完整工人
                        try:
                            if SFX.get('slight_click'):
                                audio_manager.play_sfx(SFX.get('slight_click'))
                        except Exception:
                            pass
                    return True
                
                # Dispatch 10 按钮
                btn_spacing_x = 110 if W < 400 else 130
                dispatch10_btn_rect = pygame.Rect(10 + btn_spacing_x, H - 60, 130, 20)
                if dispatch10_btn_rect.collidepoint(x, y):
                    if self.selected_body in self.player_explored_bodies and int(self.workers) >= 10:
                        dispatch_amount = min(10, int(self.workers))
                        self.selected_body.assigned_workers += dispatch_amount
                        self.workers -= dispatch_amount
                        try:
                            if SFX.get('slight_click'):
                                audio_manager.play_sfx(SFX.get('slight_click'))
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
                                audio_manager.play_sfx(SFX.get('slight_click'))
                        except Exception:
                            pass
                    return True
                
                # Recall All 按钮
                recall_all_btn_rect = pygame.Rect(10 + btn_spacing_x, H - 30, 130, 20)
                if recall_all_btn_rect.collidepoint(x, y):
                    if self.selected_body.assigned_workers > 0:
                        recall_amount = self.selected_body.assigned_workers
                        self.selected_body.assigned_workers = 0
                        self.workers += recall_amount
                        try:
                            if SFX.get('slight_click'):
                                audio_manager.play_sfx(SFX.get('slight_click'))
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
    
    def handle_multi_touch(self, touches):
        """
        处理多点触控（双指缩放和平移）
        touches: dict of {touch_id: (x, y)}
        """
        touch_list = list(touches.values())
        
        if len(touch_list) == 2:
            # 双指操作
            p1, p2 = touch_list[0], touch_list[1]
            
            # 计算当前双指距离和中心点
            current_distance = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            current_center = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            
            # 双指缩放
            if self.last_pinch_distance is not None:
                distance_change = current_distance - self.last_pinch_distance
                zoom_factor = distance_change * 0.005  # 调整缩放灵敏度
                self.handle_zoom(zoom_factor)
            
            # 双指平移
            if self.last_two_finger_center is not None:
                dx = current_center[0] - self.last_two_finger_center[0]
                dy = current_center[1] - self.last_two_finger_center[1]
                # 移动相机（反向）
                self.camera_x -= dx / self.zoom
                self.camera_y -= dy / self.zoom
            
            self.last_pinch_distance = current_distance
            self.last_two_finger_center = current_center
        else:
            # 重置双指状态
            self.last_pinch_distance = None
            self.last_two_finger_center = None
    
    
    def get_ai_owned_bodies(self):
        """获取AI拥有的所有星体"""
        owned = []
        for system in self.systems:
            if system.star.owner == 'ai':
                owned.append(system.star)
            for planet in system.planets:
                if planet.owner == 'ai':
                    owned.append(planet)
        return owned
    
    def evaluate_target_priority(self, source, target):
        """评估目标的优先级分数（越高越优先）"""
        score = 0
        
        # 获取AI进攻性系数（困难模式更激进）
        aggression = getattr(self, 'ai_aggression', 1.0)
        
        # 1. 根据目标所有者评分
        if target.owner == 'player':
            score += 100 * aggression  # 优先攻击玩家（困难模式更激进）
            # 如果是玩家主星，更高优先级
            if hasattr(self, 'player_home_planet') and target == self.player_home_planet:
                score += 200 * aggression
        elif target.owner is None:
            score += 50  # 其次是中立星球
        elif target.owner == 'ai':
            return -1000  # 不攻击自己的星球
        
        # 2. 资源价值评分
        if hasattr(target, 'resource_rate'):
            score += target.resource_rate * 10
        
        # 3. 战力对比评分
        if source.fleet_count > target.fleet_count * 1.5:
            score += 80  # 我方优势大，高优先级
        elif source.fleet_count > target.fleet_count:
            score += 40  # 我方略占优势
        elif source.fleet_count * 1.5 < target.fleet_count:
            # 困难模式即使劣势也敢打
            score -= 60 * (2.0 - aggression)  # aggression=1.4时减分少，aggression=0.6时减分多
        
        # 4. 距离因素（更近的目标优先级更高）
        dx = target.x - source.x
        dy = target.y - source.y
        distance = math.sqrt(dx*dx + dy*dy)
        score -= distance * 0.1
        
        # 5. 战略位置（连接数多的星球更重要）
        adjacent_count = len(self.get_adjacent_bodies(target))
        score += adjacent_count * 15
        
        return score
    
    def ai_should_defend(self, body):
        """判断星球是否需要防御"""
        # 检查是否有敌方舰队正在接近
        for fleet in self.moving_fleets:
            if fleet.target == body and fleet.owner == 'player':
                # 计算舰队到达时间
                dx = fleet.target.x - fleet.current_x
                dy = fleet.target.y - fleet.current_y
                distance = math.sqrt(dx*dx + dy*dy)
                if distance < 100:  # 舰队快到了
                    return True, fleet.ship_count
        return False, 0
    
    def ai_make_decision(self):
        """AI决策：智能选择派遣舰队（支持LLM AI）"""
        # 使用原来的规则AI
        current_time = time.time()
        
        # 检查是否到了决策时间
        if current_time - self.ai_last_decision_time < self.ai_decision_interval:
            return
        
        # 检查是否有待处理的AI决策结果
        with self.ai_thread_lock:
            if self.ai_pending_action is not None:
                action = self.ai_pending_action
                self.ai_pending_action = None
                if action:
                    source, target, ship_count = action
                    self.ai_send_fleet(source, target, ship_count)
                self.ai_last_decision_time = current_time
                return
        
        # 如果AI正在思考，跳过本次决策
        if self.ai_thinking:
            return
        
        self.ai_last_decision_time = current_time
        
        # 如果启用了LLM AI，在后台线程中执行决策
        if self.use_llm_ai and self.llm_ai:
            self.ai_thinking = True
            thread = threading.Thread(target=self._llm_ai_thread_worker, daemon=True)
            thread.start()
            return
        
        # 获取AI拥有的星球
        ai_bodies = self.get_ai_owned_bodies()
        if not ai_bodies:
            return
        
        # 第一优先级：防御受威胁的星球
        for body in ai_bodies:
            under_attack, enemy_ships = self.ai_should_defend(body)
            if under_attack:
                # 寻找最近的援军来源
                for source in ai_bodies:
                    if source == body:
                        continue
                    if source.fleet_count > enemy_ships * 0.7:
                        # 派遣足够的援军
                        ship_count = min(source.fleet_count - 3, enemy_ships + 5)
                        if ship_count > 0:
                            self.ai_send_fleet(source, body, ship_count)
                            print(f"AI防御: {ship_count} 艘舰船从 {source.name} 增援 {body.name}")
                            return
        
        # 第二优先级：智能进攻
        best_action = None
        best_score = -float('inf')
        
        for source in ai_bodies:
            # 保留最少3艘舰船防御
            if source.fleet_count < 8:
                continue
            
            # 评估所有可能的目标
            adjacent = self.get_adjacent_bodies(source)
            for target in adjacent:
                score = self.evaluate_target_priority(source, target)
                
                if score > best_score:
                    best_score = score
                    # 根据战力对比决定派遣数量
                    if target.owner == 'player':
                        # 攻击玩家：派遣足够多的舰船确保胜利
                        # 困难模式更保守估计，派遣更多兵力
                        aggression = getattr(self, 'ai_aggression', 1.0)
                        safety_margin = 10 + (1.5 - aggression) * 5  # easy:15, normal:10, hard:7
                        ship_count = min(
                            source.fleet_count - 3,
                            max(target.fleet_count + safety_margin, source.fleet_count * 0.7 * aggression)
                        )
                    else:
                        # 占领中立：派遣适量舰船
                        ship_count = min(
                            source.fleet_count - 3,
                            max(target.fleet_count + 5, source.fleet_count * 0.5)
                        )
                    
                    if ship_count > 0:
                        best_action = (source, target, ship_count)
        
        # 执行最佳行动
        if best_action and best_score > 0:
            source, target, ship_count = best_action
            self.ai_send_fleet(source, target, int(ship_count))
            action_type = "攻击" if target.owner == 'player' else "占领"
            print(f"AI{action_type}: {int(ship_count)} 艘舰船从 {source.name} -> {target.name} (评分: {best_score:.1f})")
        
        # 第三优先级：集结兵力（如果没有好的进攻目标）
        elif random.random() < 0.3:  # 30%概率集结兵力
            # 找到兵力最多的星球作为集结点
            strongest = max(ai_bodies, key=lambda b: b.fleet_count)
            for source in ai_bodies:
                if source != strongest and source.fleet_count > 10:
                    adjacent = self.get_adjacent_bodies(source)
                    if strongest in adjacent:
                        ship_count = source.fleet_count // 3
                        if ship_count > 0:
                            self.ai_send_fleet(source, strongest, ship_count)
                            print(f"AI集结: {ship_count} 艘舰船从 {source.name} -> {strongest.name}")
                            return
    
    def _llm_ai_thread_worker(self):
        """LLM AI后台线程工作函数（异步执行）"""
        try:
            action = self.llm_ai.make_decision(self)
            with self.ai_thread_lock:
                self.ai_pending_action = action
        except Exception as e:
            print(f"✗ LLM AI决策失败: {e}，回退到规则AI")
            with self.ai_thread_lock:
                self.ai_pending_action = None
        finally:
            self.ai_thinking = False
    
    def ai_send_fleet(self, source, target, ship_count):
        """AI派遣舰队"""
        if source.fleet_count >= ship_count:
            source.fleet_count -= ship_count
            # 创建移动舰队
            fleet = MovingFleet(source, target, ship_count, units=[])
            fleet.owner = 'ai'  # 标记舰队所有者为AI
            self.moving_fleets.append(fleet)
    
    def check_win_condition(self):
        """检查胜负条件：谁家的战士率先进入对方的初始恒星"""
        if self.game_over:
            return
        
        # 检查玩家是否占领了AI的初始星球
        if hasattr(self, 'ai_home_planet') and self.ai_home_planet.owner == 'player':
            self.game_over = True
            self.paused = True  # 暂停游戏
            self.winner = 'player'
            clear_all_leds()  # 游戏结束时清除LED
            print("玩家胜利！")
        
        # 检查AI是否占领了玩家的初始星球
        if hasattr(self, 'player_home_planet') and self.player_home_planet.owner == 'ai':
            self.game_over = True
            self.paused = True  # 暂停游戏
            self.winner = 'ai'
            clear_all_leds()  # 游戏结束时清除LED
            print("AI胜利！")
    
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

    def update_led_display(self):
        """更新LED显示以反映玩家占领的星球数量"""
        player_planet_count = 0
        for system in self.systems:
            # 计算星星
            if system.star.owner == 'player':
                player_planet_count += 1
            # 计算行星
            for planet in system.planets:
                if planet.owner == 'player':
                    player_planet_count += 1
        
        # 更新LED显示
        update_planet_leds(player_planet_count)
        return player_planet_count

# 根据屏幕大小调整按钮间距
btn_spacing = 45 if W < 400 else 80
level1_buttons = {'Start': (W//2, H//2 + 30)}
level2_buttons = {'Single Player vs AI': (W//2, H//2), 'Back': (W//2, H//2 + 150)}
level3_buttons = {'Small': (W//2, H//2 - 50), 'Large': (W//2, H//2 + 50), 'Back': (W//2, H//2 + 150)}
difficulty_buttons = {'Easy': (W//2, H//2 - 60), 'Normal': (W//2, H//2), 'Hard': (W//2, H//2 + 60), 'Back': (W//2, H//2 + 150)}

def draw_title():
    title_y = 80 if W < 400 else 100
    lcd.blit(font_big.render("STELLARIS", True, WHITE), font_big.render("STELLARIS", True, WHITE).get_rect(center=(W//2, title_y)))

def draw_button(text, position, font=font_medium, color=WHITE):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=position)
    
    # 创建更大的可点击区域
    padding_x = 30 if W < 400 else 40
    padding_y = 12 if W < 400 else 15
    click_rect = text_rect.inflate(padding_x * 2, padding_y * 2)
    
    # 检测鼠标悬停或触摸
    is_hover = click_rect.collidepoint(pygame.mouse.get_pos())
    
    # 绘制按钮背景
    bg_color = (60, 60, 80) if is_hover else (40, 40, 60)
    pygame.draw.rect(lcd, bg_color, click_rect)
    pygame.draw.rect(lcd, BLUE if is_hover else WHITE, click_rect, 2)
    
    # 绘制文字
    text_color = BLUE if is_hover else color
    text_surface = font.render(text, True, text_color)
    lcd.blit(text_surface, text_rect)
    
    return click_rect

def draw_buttons(buttons, font=font_medium):
    return {text: draw_button(text, pos, font) for text, pos in buttons.items()}

def reset_audio_device():
    """重置音频设备，解决pygame后的音频播放问题"""
    try:
        import subprocess
        import time

        # 只有在pygame已经初始化时才尝试停止pygame
        try:
            import pygame
            # 检查pygame是否已经初始化
            if pygame.get_init():
                # 强制停止所有pygame音频
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                    pygame.quit()
                    print("[DEBUG] 停止了已初始化的pygame")
                except Exception as pygame_e:
                    print(f"[WARN] 停止pygame失败: {pygame_e}")
            else:
                print("[DEBUG] pygame未初始化，跳过pygame清理")
        except ImportError:
            print("[DEBUG] pygame未导入，跳过pygame清理")

        # 根据当前使用的音频驱动进行相应的重置
        current_driver = os.environ.get('SDL_AUDIODRIVER', 'auto')
        print(f"[DEBUG] 当前音频驱动: {current_driver}")

        if current_driver == 'alsa' or current_driver == 'auto':
            # 尝试ALSA重置（如果系统支持）
            try:
                print("[DEBUG] 尝试ALSA音频设备重置...")
                result = subprocess.run(['sudo', 'alsa', 'force-reload'],
                                      capture_output=True, text=True, timeout=10)
                print(f"[DEBUG] ALSA重置结果: 退出码={result.returncode}")
                if result.returncode != 0:
                    print(f"[WARN] ALSA重置可能失败: {result.stderr[:200]}")
            except Exception as alsa_e:
                print(f"[WARN] ALSA重置异常: {alsa_e}")
        elif current_driver == 'pulseaudio':
            # PulseAudio重置
            try:
                print("[DEBUG] 尝试PulseAudio重启...")
                result = subprocess.run(['pulseaudio', '-k'],
                                      capture_output=True, text=True, timeout=5)
                time.sleep(1)
                result2 = subprocess.run(['pulseaudio', '--start'],
                                       capture_output=True, text=True, timeout=5)
                print(f"[DEBUG] PulseAudio重启结果: {result2.returncode}")
            except Exception as pulse_e:
                print(f"[WARN] PulseAudio重启失败: {pulse_e}")

        # 等待设备重置完成
        time.sleep(2)

        print("[DEBUG] ✓ 音频设备重置完成")
        return True
    except Exception as e:
        print(f"[WARN] 音频重置失败: {e}")
        return False

def main():
    import time
    global pitft

    # 注意：不再在启动时重置音频设备，因为这会干扰pygame初始化
    # 音频设备重置只在游戏退出时进行

    game_state = GameState.MENU
    game_world = None
    running = True
    selected_difficulty = 'normal'  # 默认难度
    
    # GPIO按钮去抖动状态
    button_last_state = {17: True, 22: True, 23: True, 27: True}  # True表示未按下（上拉）
    button_last_time = {17: 0, 22: 0, 23: 0, 27: 0}
    DEBOUNCE_TIME = 0.2  # 200ms去抖动

    while running:
        lcd.fill(BLACK)
        
        # 检测GPIO按钮 (仅在游戏进行中且GPIO可用时)
        if GPIO_AVAILABLE and game_state == GameState.SINGLE_PLAYER and game_world:
            current_time = time.time()
            
            # 检测GPIO 17 - Pause按钮
            button_state = GPIO.input(BUTTON_17)
            if button_state == False and button_last_state[17] == True:  # 按钮被按下（下降沿）
                if current_time - button_last_time[17] > DEBOUNCE_TIME:
                    # 触发暂停/恢复
                    game_world.paused = not game_world.paused
                    try:
                        if SFX.get('click'):
                            audio_manager.play_sfx(SFX.get('click'))
                    except Exception:
                        pass
                    print(f"GPIO 17: Pause toggled to {game_world.paused}")
                    button_last_time[17] = current_time
            button_last_state[17] = button_state
            
            # 检测GPIO 22 - Buy Worker按钮
            button_state = GPIO.input(BUTTON_22)
            if button_state == False and button_last_state[22] == True:  # 按钮被按下（下降沿）
                if current_time - button_last_time[22] > DEBOUNCE_TIME:
                    # 购买工人（需要5食物）
                    if game_world.player_food >= 5:
                        game_world.player_food -= 5
                        game_world.workers += 1
                        try:
                            if SFX.get('ding'):
                                audio_manager.play_sfx(SFX.get('ding'))
                            elif SFX.get('medium_click'):
                                audio_manager.play_sfx(SFX.get('medium_click'))
                        except Exception:
                            pass
                        print(f"GPIO 22: Bought worker (Food: {game_world.player_food}, Workers: {game_world.workers})")
                    else:
                        print(f"GPIO 22: Not enough food to buy worker (need 5, have {game_world.player_food})")
                    button_last_time[22] = current_time
            button_last_state[22] = button_state
            
            # 检测GPIO 23 - Trade按钮
            button_state = GPIO.input(BUTTON_23)
            if button_state == False and button_last_state[23] == True:  # 按钮被按下（下降沿）
                if current_time - button_last_time[23] > DEBOUNCE_TIME:
                    # 切换交易面板显示
                    game_world.show_trade_popup = not getattr(game_world, 'show_trade_popup', False)
                    if game_world.show_trade_popup:
                        game_world.trade_view = 'buy'
                    try:
                        if SFX.get('click'):
                            audio_manager.play_sfx(SFX.get('click'))
                    except Exception:
                        pass
                    print(f"GPIO 23: Trade popup toggled to {game_world.show_trade_popup}")
                    button_last_time[23] = current_time
            button_last_state[23] = button_state
        
        # 检测GPIO 27 - Exit按钮 (在任何状态下都可用)
        if GPIO_AVAILABLE:
            current_time = time.time()
            button_state = GPIO.input(BUTTON_27)
            if button_state == False and button_last_state[27] == True:  # 按钮被按下（下降沿）
                if current_time - button_last_time[27] > DEBOUNCE_TIME:
                    # 退出游戏并关闭窗口
                    print("GPIO 27: Exit button pressed")
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                    button_last_time[27] = current_time
            button_last_state[27] = button_state
        
        # 在主循环中更新触摸事件
        if pitft:
            try:
                pitft.update()  # 将 evdev 触摸事件转换为 pygame 事件
            except Exception as e:
                print(f"PiTFT update error: {e}")
            
            # 处理pigame的多点触控 (如果支持)
            if game_state == GameState.SINGLE_PLAYER and game_world and hasattr(pitft, 'touches'):
                if len(pitft.touches) >= 2:
                    # 转换pigame的触摸点格式为我们的格式
                    touch_dict = {}
                    for i, (touch_id, pos) in enumerate(pitft.touches.items()):
                        if i < 2:  # 只处理前两个触摸点
                            touch_dict[touch_id] = pos
                    if len(touch_dict) == 2:
                        game_world.handle_multi_touch(touch_dict)
                elif len(pitft.touches) < 2:
                    # 重置双指状态
                    game_world.last_pinch_distance = None
                    game_world.last_two_finger_center = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == GameState.SINGLE_PLAYER:
                        # 退出游戏界面时清除LED
                        clear_all_leds()
                        game_state = GameState.MODE_SELECT
                    else:
                        running = False
            
            # 多点触控支持 (FINGERDOWN, FINGERUP, FINGERMOTION)
            elif event.type == pygame.FINGERDOWN:
                if game_state == GameState.SINGLE_PLAYER and game_world:
                    finger_id = event.finger_id
                    x, y = int(event.x * W), int(event.y * H)
                    game_world.touch_points[finger_id] = (x, y)
            
            elif event.type == pygame.FINGERUP:
                if game_state == GameState.SINGLE_PLAYER and game_world:
                    finger_id = event.finger_id
                    if finger_id in game_world.touch_points:
                        del game_world.touch_points[finger_id]
                    # 重置双指状态
                    if len(game_world.touch_points) < 2:
                        game_world.last_pinch_distance = None
                        game_world.last_two_finger_center = None
            
            elif event.type == pygame.FINGERMOTION:
                if game_state == GameState.SINGLE_PLAYER and game_world:
                    finger_id = event.finger_id
                    x, y = int(event.x * W), int(event.y * H)
                    game_world.touch_points[finger_id] = (x, y)
                    
                    # 处理双指缩放和平移
                    if len(game_world.touch_points) >= 2:
                        game_world.handle_multi_touch(game_world.touch_points)
            
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
                # 获取点击坐标 - 优先使用event.pos
                if hasattr(event, 'pos'):
                    raw_x, raw_y = event.pos
                else:
                    raw_x, raw_y = pygame.mouse.get_pos()
                
                # PiTFT坐标旋转修正
                # 从数据看：原始x在0-319之间变化，原始y几乎总是0
                # 但y坐标是倒的：按上方得到小值，按下方得到大值
                # 需要反转y坐标
                if use_pitft:
                    # 直接使用原始坐标，不做转换（先测试）
                    x = raw_x
                    y = raw_y
                    # print(f"Touch raw: ({raw_x}, {raw_y}) -> using: ({x}, {y})")
                else:
                    x, y = raw_x, raw_y
                
                if event.button == 1:  # 左键点击
                    if game_state == GameState.MENU:
                        button_rects = draw_buttons(level1_buttons, font_big)
                        for text, rect in button_rects.items():
                            if rect.collidepoint(x, y):
                                print(f"Button '{text}' clicked!")
                                # 播放点击音效（优先 medium_click -> click）
                                try:
                                    if SFX.get('medium_click'):
                                        audio_manager.play_sfx(SFX.get('medium_click'))
                                    elif SFX.get('click'):
                                        audio_manager.play_sfx(SFX.get('click'))
                                except Exception:
                                    pass
                                if text == 'Start':
                                    game_state = GameState.MODE_SELECT
                    elif game_state == GameState.MODE_SELECT:
                        for text, rect in draw_buttons(level2_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效（优先 medium_click -> click）
                                try:
                                    if SFX.get('medium_click'):
                                        audio_manager.play_sfx(SFX.get('medium_click'))
                                    elif SFX.get('click'):
                                        audio_manager.play_sfx(SFX.get('click'))
                                except Exception:
                                    pass
                                if text == 'Single Player vs AI':
                                    game_state = GameState.DIFFICULTY_SELECT  # 先进入难度选择界面
                                elif text == 'Back':
                                    game_state = GameState.MENU
                    elif game_state == GameState.DIFFICULTY_SELECT:
                        for text, rect in draw_buttons(difficulty_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效
                                try:
                                    if SFX.get('medium_click'):
                                        audio_manager.play_sfx(SFX.get('medium_click'))
                                    elif SFX.get('click'):
                                        audio_manager.play_sfx(SFX.get('click'))
                                except Exception:
                                    pass
                                if text == 'Easy':
                                    selected_difficulty = 'easy'
                                    game_state = GameState.SCALE_SELECT
                                elif text == 'Normal':
                                    selected_difficulty = 'normal'
                                    game_state = GameState.SCALE_SELECT
                                elif text == 'Hard':
                                    selected_difficulty = 'hard'
                                    game_state = GameState.SCALE_SELECT
                                elif text == 'Back':
                                    game_state = GameState.MODE_SELECT
                    elif game_state == GameState.SCALE_SELECT:
                        for text, rect in draw_buttons(level3_buttons, font_medium).items():
                            if rect.collidepoint(x, y):
                                # 播放点击音效
                                try:
                                    if SFX.get('medium_click'):
                                        audio_manager.play_sfx(SFX.get('medium_click'))
                                    elif SFX.get('click'):
                                        audio_manager.play_sfx(SFX.get('click'))
                                except Exception:
                                    pass
                                if text == 'Small':
                                    game_state = GameState.SINGLE_PLAYER
                                    game_world = GameWorld(scale='small')
                                    game_world.ai_difficulty = selected_difficulty  # 应用难度设置
                                    # 重新初始化AI参数
                                    if game_world.ai_difficulty == 'easy':
                                        game_world.ai_decision_interval = 5.0
                                        game_world.ai_aggression = 0.6
                                        game_world.ai_resource_bonus = 0.8
                                    elif game_world.ai_difficulty == 'hard':
                                        game_world.ai_decision_interval = 2.0
                                        game_world.ai_aggression = 1.4
                                        game_world.ai_resource_bonus = 1.3
                                    else:
                                        game_world.ai_decision_interval = 3.0
                                        game_world.ai_aggression = 1.0
                                        game_world.ai_resource_bonus = 1.0
                                    
                                    # 初始化LED显示 - 进入战斗界面
                                    update_planet_leds(1)  # 初始1个星球
                                    
                                    # Immediately draw once so UI element rects are initialized
                                    try:
                                        game_world.draw(lcd)
                                        pygame.display.flip()
                                    except Exception:
                                        pass
                                elif text == 'Large':
                                    game_state = GameState.SINGLE_PLAYER
                                    game_world = GameWorld(scale='large')
                                    game_world.ai_difficulty = selected_difficulty  # 应用难度设置
                                    # 重新初始化AI参数
                                    if game_world.ai_difficulty == 'easy':
                                        game_world.ai_decision_interval = 5.0
                                        game_world.ai_aggression = 0.6
                                        game_world.ai_resource_bonus = 0.8
                                    elif game_world.ai_difficulty == 'hard':
                                        game_world.ai_decision_interval = 2.0
                                        game_world.ai_aggression = 1.4
                                        game_world.ai_resource_bonus = 1.3
                                    else:
                                        game_world.ai_decision_interval = 3.0
                                        game_world.ai_aggression = 1.0
                                        game_world.ai_resource_bonus = 1.0
                                    
                                    # 初始化LED显示 - 进入战斗界面  
                                    update_planet_leds(1)  # 初始1个星球
                                    
                                    # Immediately draw once so UI element rects are initialized
                                    try:
                                        game_world.draw(lcd)
                                        pygame.display.flip()
                                    except Exception:
                                        pass
                                elif text == 'Back':
                                    game_state = GameState.DIFFICULTY_SELECT
                    elif game_state == GameState.SINGLE_PLAYER:
                        if not game_world.handle_click(x, y):  # 如果没有点击到星体，记录拖拽起点
                            game_world.drag_start_pos = (x, y)
                            game_world.last_mouse_pos = (x, y)
                            game_world.dragging = False  # 先不开始拖拽，等移动超过阈值
                elif event.button == 4:  # 滚轮向上 (legacy)
                    if game_state == GameState.SINGLE_PLAYER and game_world:
                        # only zoom if mouse is outside the left info panel
                        if not (game_world.selected_body and x < W//3):
                            game_world.handle_zoom(0.1)
                elif event.button == 5:  # 滚轮向下。 
                    if game_state == GameState.SINGLE_PLAYER and game_world:
                        if not (game_world.selected_body and x < W//3):
                            game_world.handle_zoom(-0.1)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and game_state == GameState.SINGLE_PLAYER:  # 左键释放
                    game_world.dragging = False
                    game_world.drag_start_pos = None
            elif event.type == pygame.MOUSEMOTION and game_state == GameState.SINGLE_PLAYER:
                if game_world.last_mouse_pos is not None:
                    x, y = pygame.mouse.get_pos()
                    
                    # 如果还没开始拖拽，检查是否移动超过阈值
                    if not game_world.dragging and game_world.drag_start_pos is not None:
                        dx_total = abs(x - game_world.drag_start_pos[0])
                        dy_total = abs(y - game_world.drag_start_pos[1])
                        if dx_total > game_world.drag_threshold or dy_total > game_world.drag_threshold:
                            game_world.dragging = True  # 超过阈值，开始拖拽
                    
                    # 如果正在拖拽，更新相机位置
                    if game_world.dragging:
                        dx = x - game_world.last_mouse_pos[0]
                        dy = y - game_world.last_mouse_pos[1]
                        # PiTFT降低移动速度到3%，PC保持原速
                        drag_speed = 0.03 if W < 400 else 1.0
                        # 正确的拖拽方向：向右拖应该向右移动（相机向左）
                        game_world.camera_x -= (dx / game_world.zoom) * drag_speed
                        game_world.camera_y -= (dy / game_world.zoom) * drag_speed
                    
                    game_world.last_mouse_pos = (x, y)

        # 绘制当前状态
        if game_state == GameState.MENU:
            draw_title()
            draw_buttons(level1_buttons, font_big)
        elif game_state == GameState.MODE_SELECT:
            draw_buttons(level2_buttons, font_big)
        elif game_state == GameState.DIFFICULTY_SELECT:
            # 显示难度选择标题
            title_y = 50 if W < 400 else 70
            title_text = font_small.render("Select Difficulty", True, WHITE)
            lcd.blit(title_text, title_text.get_rect(center=(W//2, title_y)))
            draw_buttons(difficulty_buttons, font_medium)
        elif game_state == GameState.SCALE_SELECT:
            draw_buttons(level3_buttons, font_medium)
        elif game_state == GameState.SINGLE_PLAYER:
            # AI决策更新（仅在游戏运行时）
            if game_world and not game_world.game_over:
                game_world.ai_make_decision()
            
            game_world.draw(lcd)
            
            # 更新LED游戏状态指示（基于双方占领星球数量）
            if game_world:
                player_count = len([b for system in game_world.systems 
                                   for b in [system.star] + system.planets 
                                   if b.owner == 'player'])
                ai_count = len([b for system in game_world.systems 
                               for b in [system.star] + system.planets 
                               if b.owner == 'ai'])
                update_game_status_leds(player_count, ai_count)

        pygame.display.flip()
        clock.tick(60)

    # 清理LED并清理NeoPixel资源
    clear_all_leds()
    cleanup_neopixel()
    
    # 清理音频资源（释放音频设备）
    print("[DEBUG] 清理音频设备...")
    try:
        # 停止并淡出BGM
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(300)
            pygame.time.wait(350)  # 等待淡出完成
        pygame.mixer.music.stop()

        # 停止所有音效
        pygame.mixer.stop()

        # 停止所有mplayer进程
        audio_manager.cleanup()

        # 关闭mixer释放音频设备
        pygame.mixer.quit()
        print("[DEBUG] ✓ 音频设备已释放")

        # 额外的音频设备重置（针对ALSA设备独占问题）
        try:
            import subprocess
            import time

            # 强制重置ALSA音频设备
            print("[DEBUG] 执行ALSA音频设备重置...")
            result = subprocess.run(['sudo', 'alsa', 'force-reload'],
                                  capture_output=True, text=True, timeout=10)
            print(f"[DEBUG] ALSA重置结果: {result.returncode}")

            # 等待设备重置完成
            time.sleep(2)

        except Exception as alsa_e:
            print(f"[WARN] ALSA重置失败: {alsa_e}")

    except Exception as e:
        print(f"[WARN] 音频清理警告: {e}")

    # 显式清理 PiTFT 资源
    if pitft:
        try:
            if hasattr(pitft, 'stop'):
                pitft.stop()
        except Exception as e:
            print(f"PiTFT清理警告: {e}")
        pitft = None

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()