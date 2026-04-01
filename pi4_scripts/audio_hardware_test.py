#!/usr/bin/env python3
"""
Pi4音频硬件测试脚本
测试不同的音频输出设备和配置
"""
import pygame
import os
import time

def test_audio_output():
    print("=== Pi4音频硬件测试 ===")

    # 检查音频文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, 'audio')
    bgm_path = os.path.join(audio_dir, 'bgm.wav')

    if not os.path.exists(bgm_path):
        print("✗ BGM文件不存在")
        return

    print(f"BGM文件: {bgm_path}")
    print(f"文件大小: {os.path.getsize(bgm_path)} bytes")

    # 测试不同的音频配置
    configs = [
        {"name": "ALSA默认", "driver": "alsa", "freq": 44100, "buffer": 4096},
        {"name": "ALSA大缓冲", "driver": "alsa", "freq": 44100, "buffer": 8192},
        {"name": "ALSA低频", "driver": "alsa", "freq": 22050, "buffer": 4096},
        {"name": "SDL默认", "driver": "", "freq": 44100, "buffer": 4096},
    ]

    for config in configs:
        print(f"\n--- 测试配置: {config['name']} ---")

        try:
            # 清理之前的音频状态
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                pygame.quit()
            except:
                pass

            # 设置环境变量
            if config['driver']:
                os.environ['SDL_AUDIODRIVER'] = config['driver']
                print(f"设置SDL_AUDIODRIVER={config['driver']}")
            else:
                os.environ.pop('SDL_AUDIODRIVER', None)
                print("使用SDL默认音频驱动")

            # 重新初始化pygame
            pygame.init()
            print("✓ pygame.init() 成功")

            # 初始化音频混音器
            pygame.mixer.pre_init(
                frequency=config['freq'],
                size=-16,
                channels=2,
                buffer=config['buffer']
            )
            pygame.mixer.init()
            print("✓ pygame.mixer.init() 成功")

            pygame.mixer.set_num_channels(8)

            freq_info = pygame.mixer.get_init()
            print(f"✓ 音频初始化: {freq_info[0]}Hz, {freq_info[2]}声道, buffer={config['buffer']}")

            # 加载并播放BGM
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.5)  # 提高音量到50%
            pygame.mixer.music.play(-1)

            print("✓ BGM开始播放 (音量50%)")
            print("请注意听是否有声音... (5秒)")

            # 等待5秒让用户听到
            time.sleep(5)

            if pygame.mixer.music.get_busy():
                print("✓ pygame报告音乐正在播放")
            else:
                print("✗ pygame报告音乐未播放")

            pygame.mixer.music.stop()

        except Exception as e:
            print(f"✗ 配置 {config['name']} 失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n=== 系统音频信息 ===")
    try:
        # 检查ALSA设备
        result = os.popen("aplay -l").read()
        print("ALSA播放设备:")
        print(result)
    except:
        print("无法获取ALSA设备信息")

    try:
        # 检查音频模块
        result = os.popen("lsmod | grep snd").read()
        print("\n加载的音频模块:")
        print(result)
    except:
        print("无法获取音频模块信息")

    print("\n=== 建议的解决方案 ===")
    print("1. 检查音频输出设备:")
    print("   - 确保HDMI或3.5mm耳机孔连接正确")
    print("   - 运行: raspi-config -> System Options -> Audio")
    print("2. 测试系统音频:")
    print("   - speaker-test -c 2 -t wav")
    print("   - aplay /usr/share/sounds/alsa/Front_Center.wav")
    print("3. 检查音频配置:")
    print("   - cat /boot/config.txt | grep audio")
    print("4. 重启音频服务:")
    print("   - sudo alsa force-reload")

if __name__ == '__main__':
    test_audio_output()