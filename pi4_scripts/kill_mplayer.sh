#!/bin/bash
# MPlayer进程清理脚本
# 用于手动结束所有正在运行的mplayer进程

echo "=== MPlayer进程清理工具 ==="

# 检查是否有mplayer进程
MPLAYER_COUNT=$(pgrep -f mplayer | wc -l)

if [ $MPLAYER_COUNT -eq 0 ]; then
    echo "✓ 没有找到正在运行的mplayer进程"
    exit 0
fi

echo "找到 $MPLAYER_COUNT 个mplayer进程:"
pgrep -f mplayer | xargs ps -f

echo ""
echo "正在结束mplayer进程..."

# 先尝试优雅结束
pkill mplayer 2>/dev/null

# 等待1秒
sleep 1

# 检查是否还有进程存活
REMAINING=$(pgrep -f mplayer | wc -l)

if [ $REMAINING -gt 0 ]; then
    echo "还有 $REMAINING 个进程未结束，强制结束..."
    pkill -9 mplayer 2>/dev/null
    sleep 0.5
fi

# 最终检查
FINAL_COUNT=$(pgrep -f mplayer | wc -l)

if [ $FINAL_COUNT -eq 0 ]; then
    echo "✓ 所有mplayer进程已成功结束"
else
    echo "⚠ 还有 $FINAL_COUNT 个进程未能结束"
    echo "剩余进程:"
    pgrep -f mplayer | xargs ps -f
fi

echo "清理完成"