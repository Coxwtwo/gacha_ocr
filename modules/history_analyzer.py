# modules/history_analyzer.py
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import defaultdict
import matplotlib
from pathlib import Path
import sys
from .logger_manager import get_logger

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 设置中文字体
matplotlib.rcParams['axes.unicode_minus'] = False  # 正常显示负号


def load_json_files(history_file_path, catalog_file_path):
    """加载JSON文件"""
    # 加载抽卡记录
    with open(history_file_path, 'r', encoding='utf-8') as f:
        gacha_data = json.load(f)
    
    # 加载游戏目录
    with open(catalog_file_path, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)
    
    return gacha_data, catalog_data


def create_item_mapping(catalog_data):
    """创建物品名称到详情的映射"""
    item_mapping = {}
    for item_id, item_info in catalog_data.get('item', {}).items():
        display_name = item_info.get('display_name', '')
        item_mapping[display_name] = {
            'id': item_id,
            'rarity': item_info.get('rarity', 0),
            'item_type': item_info.get('item_type', '')
        }
    return item_mapping


def create_pool_mapping(catalog_data):
    """创建卡池名称到详情的映射"""
    pool_mapping = {}
    for pool_id, pool_info in catalog_data.get('pool', {}).items():
        display_name = pool_info.get('display_name', '')
        pool_mapping[display_name] = {
            'id': pool_id,
            'pool_type': pool_info.get('pool_type', ''),
            'alias': pool_info.get('alias', ''),
            'carry_over': pool_info.get('carry_over', False),
            'carry_over_target': pool_info.get('carry_over_target', [])
        }
    return pool_mapping


def analyze_gacha_data(gacha_data, catalog_data):
    """分析抽卡数据"""
    # 创建映射
    item_mapping = create_item_mapping(catalog_data)
    pool_mapping = create_pool_mapping(catalog_data)
    
    # 初始化统计数据结构
    pool_stats = defaultdict(lambda: {
        'total_pulls': 0,
        'rarity_counts': {2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
        'pull_history': [],  # 记录每次抽取的详情
        'gold_pulls': [],   # 记录每次出6星的抽数间隔
        'last_gold_pull': -1,  # 上次出6星的索引
        'current_pity': 0,   # 当前保底计数
        'items': []         # 抽取到的物品列表
    })
    
    # 按时间排序（假设数据已经按时间排序，但为了安全还是排序）
    gacha_entries = sorted(gacha_data['data'], key=lambda x: x['time'])
    
    # 遍历抽卡记录
    for idx, entry in enumerate(gacha_entries):
        item_name = entry['item']
        pool_name = entry['pool']
        
        # 获取物品稀有度
        item_info = item_mapping.get(item_name, {})
        rarity = item_info.get('rarity', 0)
        
        # 更新卡池统计
        pool_stats[pool_name]['total_pulls'] += 1
        # 检查稀有度是否在有效范围内，否则跳过或记录为其他
        if rarity in pool_stats[pool_name]['rarity_counts']:
            pool_stats[pool_name]['rarity_counts'][rarity] += 1
        else:
            # 如果稀有度不在预期范围内（如0或其他值），可以选择忽略或添加到特定类别
            if rarity != 0:  # 仅对非0但无效的稀有度发出警告
                print(f"警告: 发现无效稀有度值 {rarity}，物品名称: {item_name}")
        
        pool_stats[pool_name]['pull_history'].append({
            'item': item_name,
            'rarity': rarity,
            'time': entry['time'],
            'pull_number': pool_stats[pool_name]['total_pulls']
        })
        pool_stats[pool_name]['items'].append(item_name)
        
        # 更新保底计数
        pool_stats[pool_name]['current_pity'] += 1
        
        # 检查是否出6星
        if rarity == 6:
            # 记录出金间隔
            if pool_stats[pool_name]['last_gold_pull'] == -1:
                # 第一次出金
                pool_stats[pool_name]['gold_pulls'].append(pool_stats[pool_name]['current_pity'])
            else:
                # 计算从上一次6星到现在的抽数
                pulls_since_last_gold = pool_stats[pool_name]['current_pity']
                pool_stats[pool_name]['gold_pulls'].append(pulls_since_last_gold)
            
            # 重置保底计数
            pool_stats[pool_name]['current_pity'] = 0
            pool_stats[pool_name]['last_gold_pull'] = idx
    
    return pool_stats, item_mapping, pool_mapping


def calculate_statistics(pool_stats):
    """计算统计指标"""
    results = {}
    
    for pool_name, stats in pool_stats.items():
        total_pulls = stats['total_pulls']
        rarity_counts = stats['rarity_counts']
        gold_pulls = stats['gold_pulls']
        
        # 1. 总抽取次数
        total_pulls = stats['total_pulls']
        
        # 2. 稀有度分布
        rarity_distribution = {
            '2_star': rarity_counts[2],
            '3_star': rarity_counts[3],
            '4_star': rarity_counts[4],
            '5_star': rarity_counts[5],
            '6_star': rarity_counts[6]
        }
        
        # 3. 保底进度
        pity_progress = stats['current_pity']
        
        # 4. 欧非程度分析
        if gold_pulls:
            avg_gold_pulls = sum(gold_pulls) / len(gold_pulls)
        else:
            avg_gold_pulls = None
        
        # 5. 出金率
        gold_rate = rarity_counts[6] / total_pulls * 100 if total_pulls > 0 else 0
        
        results[pool_name] = {
            'total_pulls': total_pulls,
            'rarity_distribution': rarity_distribution,
            'pity_progress': pity_progress,
            'gold_pulls_history': gold_pulls,
            'avg_gold_pulls': avg_gold_pulls,
            'gold_rate': gold_rate,
            'rarity_counts': rarity_counts
        }
    
    return results


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


def print_analysis_report(results, pool_stats, pool_mapping, item_mapping, uid):
    """打印分析报告"""
    print("=" * 60)
    print("           重返未来：1999 抽卡记录分析报告")
    print("=" * 60)
    
    # 显示UID（从原始数据中提取）
    print(f"用户UID: {uid}")  # 这里使用实际的UID
    
    total_pulls_all = sum(stats['total_pulls'] for stats in pool_stats.values())
    total_6_star = sum(stats['rarity_counts'][6] for stats in pool_stats.values())
    
    print(f"\n📊 总体统计:")
    print(f"   总抽取次数: {total_pulls_all}次")
    print(f"   6星获取数量: {total_6_star}个")
    if total_pulls_all > 0:
        print(f"   综合6星获取率: {total_6_star/total_pulls_all*100:.2f}%")
    else:
        print(f"   综合6星获取率: 0.00%")
    
    print(f"\n🔍 各卡池详细分析:")
    print("-" * 60)
    
    for pool_name, stats in results.items():
        pool_info = pool_mapping.get(pool_name, {})
        pool_type_name = pool_info.get('alias', '未知卡池类型')
        
        print(f"\n🎯 卡池: {pool_name} ({pool_type_name})")
        print(f"   ├─ 总抽取次数: {stats['total_pulls']}次")
        print(f"   ├─ 稀有度分布:")
        print(f"   │   ├─ 2星: {stats['rarity_counts'][2]}个")
        print(f"   │   ├─ 3星: {stats['rarity_counts'][3]}个")
        print(f"   │   ├─ 4星: {stats['rarity_counts'][4]}个")
        print(f"   │   ├─ 5星: {stats['rarity_counts'][5]}个")
        print(f"   │   └─ 6星: {stats['rarity_counts'][6]}个")
        
        print(f"   ├─ 当前保底进度: {stats['pity_progress']}抽未出6星")
        
        if stats['gold_pulls_history']:
            print(f"   ├─ 出金间隔: {', '.join(map(str, stats['gold_pulls_history']))}")
            print(f"   ├─ 平均出金抽数: {stats['avg_gold_pulls']:.1f}抽/6星")
            print(f"   └─ 6星获取率: {stats['gold_rate']:.2f}%")
        else:
            print(f"   └─ 尚未获得6星")
    
    print(f"\n🎲 欧非程度评估:")
    print("-" * 60)
    
    for pool_name, stats in results.items():
        if stats['avg_gold_pulls'] is not None:
            avg = stats['avg_gold_pulls']
            if avg <= 20:
                rating = "⭐⭐⭐⭐⭐ (欧皇级别)"
            elif avg <= 40:
                rating = "⭐⭐⭐⭐ (欧洲人)"
            elif avg <= 60:
                rating = "⭐⭐⭐ (正常水平)"
            elif avg <= 80:
                rating = "⭐⭐ (亚洲人)"
            else:
                rating = "⭐ (非酋)"
            
            print(f"   {pool_name}: 平均{avg:.1f}抽出6星 - {rating}")
        else:
            print(f"   {pool_name}: 尚未获得6星，无法评估")
    
    print(f"\n💡 分析建议:")
    print("-" * 60)
    
    # 找出最佳卡池
    best_pool = None
    best_rate = 0
    
    for pool_name, stats in results.items():
        if stats['gold_rate'] > best_rate and stats['total_pulls'] > 0:
            best_rate = stats['gold_rate']
            best_pool = pool_name
    
    if best_pool:
        print(f"   1. '{best_pool}'卡池表现最佳，6星获取率{best_rate:.2f}%")
    
    # 检查接近保底的卡池
    pity_warning = []
    for pool_name, stats in results.items():
        if stats['pity_progress'] >= 50:  # 假设50抽接近保底
            pity_warning.append((pool_name, stats['pity_progress']))
    
    if pity_warning:
        print(f"   2. 以下卡池接近保底:")
        for pool_name, pity in pity_warning:
            print(f"      - {pool_name}: 已{pity}抽未出6星")
    
    # 总体建议
    if total_6_star / total_pulls_all * 100 >= 3:
        print(f"   3. 总体运气不错，继续加油！")
    else:
        print(f"   3. 6星获取率偏低，建议规划抽卡资源")
    
    print(f"\n📈 可视化图表已保存:")
    print(f"   - gacha_analysis.png: 主要分析图表")
    print(f"   - gold_pull_intervals.png: 出金间隔图表")
    print("=" * 60)

def analyze_history_file(history_file_path, catalog_data):
    """分析指定的抽卡记录文件"""
    try:
        logger = get_logger()
        logger.info(f"开始分析历史记录文件: {history_file_path}")
        
        # 1. 加载抽卡数据
        print("正在加载数据...")
        with open(history_file_path, 'r', encoding='utf-8') as f:
            gacha_data = json.load(f)
        
        uid = gacha_data['info']['uid']
        print(f"用户UID: {uid}")
        
        # 2. 分析抽卡数据
        print("正在分析抽卡记录...")
        pool_stats, item_mapping, pool_mapping = analyze_gacha_data(gacha_data, catalog_data)
        
        # 3. 计算统计指标
        print("正在计算统计指标...")
        results = calculate_statistics(pool_stats)
        
        # 4. 创建可视化图表
        print("正在生成可视化图表...")
        create_visualizations(uid, pool_stats, results, catalog_data)
        
        # 5. 打印分析报告
        print("\n" + "="*60)
        print_analysis_report(results, pool_stats, pool_mapping, item_mapping, uid)
        
        print("\n✅ 分析完成！")
        
        # 6. 返回分析结果
        return {
            'success': True,
            'pool_stats': pool_stats,
            'results': results,
            'item_mapping': item_mapping,
            'pool_mapping': pool_mapping
        }
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        return {'success': False, 'error': str(e)}
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


class GachaAnalyzer:
    """抽卡记录分析器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = get_logger()
    
    def analyze(self, history_file_path, game_id):
        """分析指定游戏的抽卡记录"""
        try:
            # 使用配置管理器加载目录数据
            catalog_data = self.config_manager.load_catalog_data(game_id)
            if not catalog_data:
                raise ValueError(f"无法加载游戏ID {game_id} 的目录数据")
                
            # 直接传递catalog_data字典而不是路径
            return analyze_history_file(history_file_path, catalog_data)
        except Exception as e:
            self.logger.error(f"分析过程出错: {e}")
            return {'success': False, 'error': str(e)}
