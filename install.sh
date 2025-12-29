#!/bin/bash

echo "🔄 Discord会员充值机器人 - Py-cord安装脚本"
echo "=============================================="

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
   echo "❌ 请不要使用root用户运行此脚本"
   exit 1
fi

echo "📦 正在卸载可能存在的discord相关包..."
pip uninstall discord.py py-cord discord -y 2>/dev/null

echo ""
echo "⬇️  正在安装Py-cord..."
pip install py-cord>=2.4.0 aiohttp>=3.8.0

echo ""
echo "✅ 验证安装..."
python3 -c "import discord; print('✅ Py-cord版本:', discord.__version__)"

echo ""
echo "🎉 安装完成！"
echo "现在运行机器人:"
echo "python3 main.py"
echo ""
echo "如果遇到问题，请检查config.json配置是否正确。"
