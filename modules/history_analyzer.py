# modules/history_analyzer.py
import json
from collections import defaultdict
from .logger_manager import get_logger
from .visualization import create_visualizations

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
