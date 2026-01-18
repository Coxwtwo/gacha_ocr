
from matplotlib import pyplot as plt
import matplotlib
import numpy as np


matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 设置中文字体
matplotlib.rcParams['axes.unicode_minus'] = False  # 正常显示负号

def create_visualizations(uid, pool_stats, results, catalog_data):
    """创建可视化图表"""
    pool_names = list(pool_stats.keys())
    num_pools = len(pool_names)
    
    # 创建第一个图形：综合分析和各卡池稀有度分布
    if num_pools <= 3:
        # 如果卡池数量少，使用2行3列布局
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        fig.suptitle(f'{catalog_data["game_info"]["game_name"]} 抽卡数据分析 - UID: {uid}', fontsize=18, fontweight='bold')
        
        # 1. 各卡池抽取次数柱状图
        ax1 = axes[0, 0]
        total_pulls = [results[pool]['total_pulls'] for pool in pool_names]
        bars1 = ax1.bar(pool_names, total_pulls, color=['#FF6B6B', '#4ECDC4', '#45B7D1'][:num_pools])
        ax1.set_title('各卡池总抽取次数', fontsize=12, fontweight='bold')
        ax1.set_ylabel('抽取次数')
        ax1.tick_params(axis='x', rotation=15)
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # 2. 综合稀有度分布饼图
        ax2 = axes[0, 1]
        # 汇总所有卡池的稀有度
        total_rarity_counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        for stats in pool_stats.values():
            for rarity, count in stats['rarity_counts'].items():
                total_rarity_counts[rarity] += count
        
        labels = ['2星', '3星', '4星', '5星', '6星']
        sizes = [total_rarity_counts[2], total_rarity_counts[3], 
                 total_rarity_counts[4], total_rarity_counts[5], 
                 total_rarity_counts[6]]
        colors = ['#C0C0C0', '#A9A9A9', '#9370DB', '#FFD700', '#FF4500']
        # 过滤掉0值
        filtered_labels = [labels[i] for i in range(5) if sizes[i] > 0]
        filtered_sizes = [s for s in sizes if s > 0]
        filtered_colors = [colors[i] for i in range(5) if sizes[i] > 0]
        
        if filtered_sizes:
            ax2.pie(filtered_sizes, labels=filtered_labels, autopct='%1.1f%%',
                    colors=filtered_colors, startangle=90)
            ax2.set_title('综合稀有度分布', fontsize=12, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '无数据', ha='center', va='center')
            ax2.set_title('综合稀有度分布', fontsize=12, fontweight='bold')
        
        # 3. 平均出金抽数柱状图
        ax3 = axes[0, 2]
        avg_gold_data = []
        valid_pools = []
        for pool in pool_names:
            avg = results[pool]['avg_gold_pulls']
            if avg is not None:
                avg_gold_data.append(avg)
                valid_pools.append(pool)
        
        if avg_gold_data:
            bars3 = ax3.bar(valid_pools, avg_gold_data, color=['#FF6B6B', '#45B7D1'][:len(valid_pools)])
            ax3.set_title('平均出金（6星）抽数', fontsize=12, fontweight='bold')
            ax3.set_ylabel('平均抽数/6星')
            ax3.tick_params(axis='x', rotation=15)
            for bar in bars3:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}', ha='center', va='bottom')
        else:
            ax3.text(0.5, 0.5, '无6星数据', ha='center', va='center')
            ax3.set_title('平均出金（6星）抽数', fontsize=12, fontweight='bold')
        
        # 各卡池稀有度分布饼图
        for idx, pool_name in enumerate(pool_names):
            row, col = 1, idx
            ax = axes[row, col]
            
            rarity_counts = pool_stats[pool_name]['rarity_counts']
            sizes = [rarity_counts[2], rarity_counts[3], rarity_counts[4], 
                     rarity_counts[5], rarity_counts[6]]
            
            # 过滤掉0值
            filtered_labels = [labels[i] for i in range(5) if sizes[i] > 0]
            filtered_sizes = [s for s in sizes if s > 0]
            filtered_colors = [colors[i] for i in range(5) if sizes[i] > 0]
            
            if filtered_sizes:
                ax.pie(filtered_sizes, labels=filtered_labels, autopct='%1.1f%%',
                       colors=filtered_colors, startangle=90)
                ax.set_title(f'{pool_name}\n稀有度分布', fontsize=10, fontweight='bold')
            else:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center')
                ax.set_title(f'{pool_name}\n稀有度分布', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('gacha_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        
    else:
        # 如果卡池数量多，使用单独的图表
        # 创建综合图表
        fig1, axes1 = plt.subplots(1, 3, figsize=(15, 5))
        fig1.suptitle('重返未来：1999 抽卡数据分析', fontsize=18, fontweight='bold')
        
        # 1. 各卡池抽取次数柱状图
        ax1 = axes1[0]
        total_pulls = [results[pool]['total_pulls'] for pool in pool_names]
        bars1 = ax1.bar(pool_names, total_pulls, color=plt.cm.Set3(np.arange(len(pool_names))/len(pool_names)))
        ax1.set_title('各卡池总抽取次数', fontsize=12, fontweight='bold')
        ax1.set_ylabel('抽取次数')
        ax1.tick_params(axis='x', rotation=45)
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # 2. 综合稀有度分布饼图
        ax2 = axes1[1]
        total_rarity_counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        for stats in pool_stats.values():
            for rarity, count in stats['rarity_counts'].items():
                total_rarity_counts[rarity] += count
        
        labels = ['2星', '3星', '4星', '5星', '6星']
        sizes = [total_rarity_counts[2], total_rarity_counts[3], 
                 total_rarity_counts[4], total_rarity_counts[5], 
                 total_rarity_counts[6]]
        colors = ['#C0C0C0', '#A9A9A9', '#9370DB', '#FFD700', '#FF4500']
        
        filtered_labels = [labels[i] for i in range(5) if sizes[i] > 0]
        filtered_sizes = [s for s in sizes if s > 0]
        filtered_colors = [colors[i] for i in range(5) if sizes[i] > 0]
        
        if filtered_sizes:
            ax2.pie(filtered_sizes, labels=filtered_labels, autopct='%1.1f%%',
                    colors=filtered_colors, startangle=90)
            ax2.set_title('综合稀有度分布', fontsize=12, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '无数据', ha='center', va='center')
            ax2.set_title('综合稀有度分布', fontsize=12, fontweight='bold')
        
        # 3. 平均出金抽数柱状图
        ax3 = axes1[2]
        avg_gold_data = []
        valid_pools = []
        for pool in pool_names:
            avg = results[pool]['avg_gold_pulls']
            if avg is not None:
                avg_gold_data.append(avg)
                valid_pools.append(pool)
        
        if avg_gold_data:
            bars3 = ax3.bar(valid_pools, avg_gold_data, 
                           color=plt.cm.Set3(np.arange(len(valid_pools))/max(1, len(valid_pools))))
            ax3.set_title('平均出金（6星）抽数', fontsize=12, fontweight='bold')
            ax3.set_ylabel('平均抽数/6星')
            ax3.tick_params(axis='x', rotation=45)
            for bar in bars3:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}', ha='center', va='bottom')
        else:
            ax3.text(0.5, 0.5, '无6星数据', ha='center', va='center')
            ax3.set_title('平均出金（6星）抽数', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('gacha_analysis_summary.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 创建各卡池稀有度分布图表
        fig2, axes2 = plt.subplots((num_pools + 2) // 3, 3, figsize=(15, 4*((num_pools + 2) // 3)))
        fig2.suptitle('各卡池稀有度分布', fontsize=18, fontweight='bold')
        
        # 展平axes数组以便遍历
        if num_pools <= 3:
            axes_flat = axes2.flatten() if num_pools > 1 else [axes2]
        else:
            axes_flat = axes2.flatten()
        
        for idx, (pool_name, ax) in enumerate(zip(pool_names, axes_flat)):
            if idx >= len(axes_flat):
                break
                
            rarity_counts = pool_stats[pool_name]['rarity_counts']
            sizes = [rarity_counts[2], rarity_counts[3], rarity_counts[4], 
                     rarity_counts[5], rarity_counts[6]]
            
            # 过滤掉0值
            filtered_labels = [labels[i] for i in range(5) if sizes[i] > 0]
            filtered_sizes = [s for s in sizes if s > 0]
            filtered_colors = [colors[i] for i in range(5) if sizes[i] > 0]
            
            if filtered_sizes:
                ax.pie(filtered_sizes, labels=filtered_labels, autopct='%1.1f%%',
                       colors=filtered_colors, startangle=90)
                ax.set_title(pool_name, fontsize=10, fontweight='bold')
            else:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center')
                ax.set_title(pool_name, fontsize=10, fontweight='bold')
        
        # 隐藏多余的子图
        for idx in range(len(pool_names), len(axes_flat)):
            axes_flat[idx].axis('off')
        
        plt.tight_layout()
        plt.savefig('gacha_analysis_by_pool.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    # 创建出金间隔柱状图
    fig3 = None
    has_gold_data = False
    gold_pools = []
    gold_intervals = []
    
    for pool_name in pool_names:
        gold_pulls = results[pool_name]['gold_pulls_history']
        if gold_pulls:
            has_gold_data = True
            gold_pools.append(pool_name)
            gold_intervals.append(gold_pulls)
    
    if has_gold_data:
        fig3, ax4 = plt.subplots(figsize=(10, 6))
        
        # 准备数据
        max_intervals = max(len(intervals) for intervals in gold_intervals)
        x = np.arange(max_intervals)
        bar_width = 0.8 / len(gold_pools)
        
        for i, (pool_name, intervals) in enumerate(zip(gold_pools, gold_intervals)):
            x_pos = x[:len(intervals)] + i * bar_width
            bars = ax4.bar(x_pos, intervals, width=bar_width, 
                          label=pool_name, alpha=0.8)
            
            # 添加数值标签
            for bar, val in zip(bars, intervals):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(val)}', ha='center', va='bottom', fontsize=8)
        
        ax4.set_xlabel('出金次数')
        ax4.set_ylabel('所需抽数')
        ax4.set_title('各卡池每次出金所需抽数', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.set_xticks(x + bar_width * (len(gold_pools) - 1) / 2)
        ax4.set_xticklabels([f'第{i+1}次出金' for i in range(max_intervals)])
        
        plt.tight_layout()
        plt.savefig('gold_pull_intervals.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    return True

