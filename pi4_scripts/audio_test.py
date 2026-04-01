#!/usr/bin/env python3
"""
Pi4音频诊断脚本
用于测试pygame音频功能和BGM播放
"""
import pygame
import os
import sys

def test_audio():
    print("=== Pi4音频诊断 ===")

    # 检查音频文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, 'audio')
    bgm_path = os.path.join(audio_dir, 'bgm.wav')

    print(f"音频目录: {audio_dir}")
    print(f"BGM文件: {bgm_path}")
    print(f"BGM文件存在: {os.path.exists(bgm_path)}")

    if os.path.exists(bgm_path):
        print(f"BGM文件大小: {os.path.getsize(bgm_path)} bytes")

    # 测试pygame音频初始化
    print("\n--- 测试pygame音频初始化 ---")
    try:
        # 设置环境变量
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        print("设置SDL_AUDIODRIVER=alsa")

        pygame.init()
        print("✓ pygame.init() 成功")

        # 初始化音频
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        freq_info = pygame.mixer.get_init()
        print(f"✓ 音频初始化: {freq_info[0]}Hz, {freq_info[2]}声道, buffer=4096")

        # 测试BGM加载
        print("\n--- 测试BGM加载 ---")
        if os.path.exists(bgm_path):
            pygame.mixer.music.load(bgm_path)
            print("✓ BGM加载成功")

            pygame.mixer.music.set_volume(0.3)
            print("✓ 设置音量为0.3")

            pygame.mixer.music.play(-1)  # 循环播放
            print("✓ 开始播放BGM（循环播放）")

            pygame.time.wait(2000)  # 等待2秒

            if pygame.mixer.music.get_busy():
                print("✓ BGM正在播放 - 音频工作正常！")
            else:
                print("✗ BGM播放失败 - 检查音频驱动")

                # 尝试备用方法
                print("\n--- 尝试备用播放方法 ---")
                try:
                    pygame.mixer.music.stop()
                    pygame.time.wait(100)

                    bgm_sound = pygame.mixer.Sound(bgm_path)
                    bgm_sound.set_volume(0.2)
                    bgm_sound.play(-1)
                    pygame.time.wait(2000)

                    print("✓ 使用Sound对象播放BGM")
                except Exception as e:
                    print(f"✗ 备用方法也失败: {e}")
        else:
            print("✗ BGM文件不存在")

    except Exception as e:
        print(f"✗ 音频测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            pygame.mixer.music.stop()
            pygame.quit()
            print("\n✓ 清理完成")
        except:
            pass

if __name__ == '__main__':
    test_audio()