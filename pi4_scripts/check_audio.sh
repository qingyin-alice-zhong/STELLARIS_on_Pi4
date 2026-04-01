#!/bin/bash
echo "=== Pi4音频配置检查 ==="
echo ""

echo "1. 当前音频配置 (/boot/config.txt):"
grep -i audio /boot/config.txt || echo "  无音频相关配置"

echo ""
echo "2. ALSA音频设备:"
aplay -l 2>/dev/null || echo "  无法获取ALSA设备信息"

echo ""
echo "3. 当前音频模块:"
lsmod | grep -E "(snd|audio)" || echo "  无音频模块加载"

echo ""
echo "4. PulseAudio状态:"
pulseaudio --check && echo "  PulseAudio正在运行" || echo "  PulseAudio未运行"

echo ""
echo "5. 当前音频输出设备:"
amixer cget numid=3 2>/dev/null | grep ": values=" | sed 's/.*values=//' | while read val; do
    case $val in
        0) echo "  自动检测" ;;
        1) echo "  模拟输出 (3.5mm耳机孔)" ;;
        2) echo "  HDMI输出" ;;
        *) echo "  未知输出: $val" ;;
    esac
done

echo ""
echo "6. 测试音频播放:"
echo "  运行以下命令测试音频:"
echo "  speaker-test -c 2 -t wav -l 1"
echo "  aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || echo '无测试音频文件'"

echo ""
echo "=== 快速修复建议 ==="
echo "1. 设置音频输出:"
echo "   sudo raspi-config"
echo "   -> 6 System Options -> S2 Audio -> 选择输出设备"
echo ""
echo "2. 重启ALSA:"
echo "   sudo alsa force-reload"
echo ""
echo "3. 测试音频:"
echo "   speaker-test -c 2 -t wav"