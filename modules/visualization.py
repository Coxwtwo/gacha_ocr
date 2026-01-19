# modules/visualization.py
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import os

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_visualizations(uid, pool_stats, results, catalog_data):
    """
    创建可视化图表
    """
    # 创建主分析图表
    create_main_analysis_charts(uid, pool_stats, results)
    
    # 创建单独的出金间隔图表
    create_gold_pull_intervals_chart(uid, pool_stats, results)

def create_main_analysis_charts(uid, pool_stats, results):
    """
    创建主分析图表
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'抽卡分析报告 - UID: {uid}', fontsize=16)

    # 1. 稀有度分布饼图
    plot_rarity_distribution_pie(axes[0, 0], results)

    # 2. 各卡池总抽数对比
    plot_total_pulls_comparison(axes[0, 1], results)

    # 3. 各卡池出金率对比
    plot_gold_rate_comparison(axes[1, 0], results)

    # 4. 保底进度展示
    plot_pity_progress(axes[1, 1], results)

    plt.tight_layout()
    plt.savefig(f'gacha_analysis_{uid}.png', dpi=300, bbox_inches='tight')
    plt.close()  # 关闭图形以释放内存

def create_gold_pull_intervals_chart(uid, pool_stats, results):
    """
    创建出金间隔图表
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for pool_name, stats in results.items():
        gold_pulls = stats['gold_pulls_history']
        if gold_pulls:
            x_values = range(1, len(gold_pulls) + 1)
            ax.plot(x_values, gold_pulls, marker='o', label=pool_name, linewidth=2, markersize=6)
    
    ax.set_title(f'出金间隔统计 - UID: {uid}')
    ax.set_xlabel('第N次获得6星')
    ax.set_ylabel('抽数')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # 只有在有标签的情况下才显示图例
    handles, labels = ax.get_legend_handles_labels()
    if handles and labels:
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(f'gold_pull_intervals_{uid}.png', dpi=300, bbox_inches='tight')
    plt.close()

def plot_rarity_distribution_pie(ax, results):
    """
    绘制稀有度分布饼图
    """
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

def plot_total_pulls_comparison(ax, results):
    """
    绘制各卡池总抽数对比
    """
    pool_names = list(results.keys())
    total_pulls = [results[pool_name]['total_pulls'] for pool_name in pool_names]
    
    if pool_names:  # 只有在有数据时才绘制
        bars = ax.bar(pool_names, total_pulls)
        ax.set_title('各卡池总抽数对比')
        ax.set_ylabel('抽数')
        
        # 在柱子上显示数值
        for bar, value in zip(bars, total_pulls):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(value)}',
                   ha='center', va='bottom')
        
        # 旋转x轴标签以防重叠
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    else:
        ax.text(0.5, 0.5, '无数据', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title('各卡池总抽数对比')

def plot_gold_rate_comparison(ax, results):
    """
    绘制各卡池出金率对比
    """
    pool_names = [name for name, stats in results.items() if stats['total_pulls'] > 0]
    gold_rates = [results[pool_name]['gold_rate'] for pool_name in pool_names]
    
    if pool_names:  # 只有在有数据时才绘制
        bars = ax.bar(pool_names, gold_rates)
        ax.set_title('各卡池6星获取率对比')
        ax.set_ylabel('6星获取率 (%)')
        
        # 在柱子上显示数值
        for bar, value in zip(bars, gold_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.2f}%',
                   ha='center', va='bottom')
        
        # 旋转x轴标签以防重叠
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    else:
        ax.text(0.5, 0.5, '无数据', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title('各卡池6星获取率对比')

def plot_pity_progress(ax, results):
    """
    绘制保底进度展示
    """
    pool_names = list(results.keys())
    pity_progresses = [results[pool_name]['pity_progress'] for pool_name in pool_names]
    
    if pool_names:  # 只有在有数据时才绘制
        bars = ax.bar(pool_names, pity_progresses)
        ax.set_title('当前保底进度')
        ax.set_ylabel('未出6星抽数')
        
        # 在柱子上显示数值
        for bar, value in zip(bars, pity_progresses):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(value)}',
                   ha='center', va='bottom')
        
        # 旋转x轴标签以防重叠
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    else:
        ax.text(0.5, 0.5, '无数据', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title('当前保底进度')