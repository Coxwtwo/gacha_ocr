# modules/visualization.py
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import os
from .logger_manager import get_logger

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_visualizations(game_name, game_id, uid, results):
    """
    创建可视化图表
    """
    # 创建出金间隔图表
    create_gold_pull_intervals_chart(game_name, game_id, uid, results)
    # 创建稀有度分析图表
    create_rarity_analysis_charts(game_name, game_id, uid, results)

def create_gold_pull_intervals_chart(game_name, game_id, uid, results):
    """
    创建出金间隔图表
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for pool_name, stats in results.items():
        gold_pulls = stats['gold_pulls_history']
        if gold_pulls:
            x_values = range(1, len(gold_pulls) + 1)
            ax.plot(x_values, gold_pulls, marker='o', label=pool_name, linewidth=2, markersize=6)
    
    ax.set_title(f'出金间隔统计 - {game_name} - UID: {uid}')
    ax.set_xlabel('第N次获得6星')
    ax.set_ylabel('抽数')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # 只有在有标签的情况下才显示图例
    handles, labels = ax.get_legend_handles_labels()
    if handles and labels:
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(f'gold_pull_intervals_{game_id}_{uid}.png', dpi=300, bbox_inches='tight')
    logger = get_logger()
    logger.info(f"gold_pull_intervals_{game_id}_{uid}.png: 出金间隔图表已保存")
    plt.close()
def create_rarity_analysis_charts(game_name, game_id, uid, results):
    """
    创建稀有度分析图表
    """
    fig, ax = plt.subplots(figsize=(15, 12))
    fig.suptitle(f'稀有度分析 - {game_name} - UID: {uid}', fontsize=16)

    # 计算总体稀有度分布
    total_rarities = defaultdict(int)
    for stats in results.values():
        for star_level, count in stats['rarity_distribution'].items():
            total_rarities[star_level] += count
    
    labels = [f'{key} ({value}个)' for key, value in total_rarities.items() if value > 0]
    sizes = [value for value in total_rarities.values() if value > 0]
    
    if sizes:  # 只有在有数据时才绘制
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title('总体稀有度分布')
    else:
        ax.text(0.5, 0.5, '无数据', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title('总体稀有度分布')

    plt.tight_layout()
    plt.savefig(f'gacha_analysis_{game_id}_{uid}.png', dpi=300, bbox_inches='tight')
    logger = get_logger()
    logger.info(f"gacha_analysis_{game_id}_{uid}.png: 稀有度分布图表已保存")
    plt.close()  # 关闭图形以释放内存
