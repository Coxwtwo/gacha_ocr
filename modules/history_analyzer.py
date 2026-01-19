import json
from collections import defaultdict
from .logger_manager import get_logger
from .visualization import create_visualizations

logger = get_logger()

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
    """分析抽卡数据逻辑"""
    # 创建映射
    item_mapping = create_item_mapping(catalog_data)
    pool_mapping = create_pool_mapping(catalog_data)

    # 初始化统计数据结构
    pool_stats = defaultdict(lambda: {
        'total_pulls': 0,
        'rarity_counts': {rarity: 0 for rarity in range(2, 7)},
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
                logger.warning(f"发现无效稀有度值 {rarity}，物品名称: {item_name}")
        
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
            # 记录当前的抽数
            pool_stats[pool_name]['gold_pulls'].append(pool_stats[pool_name]['current_pity'])
            pool_stats[pool_name]['last_gold_pull'] = idx
            pool_stats[pool_name]['current_pity'] = 0

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
        
        # 4. 出金率
        gold_rate = rarity_counts[6] / total_pulls * 100 if total_pulls > 0 else 0
        
        results[pool_name] = {
            'total_pulls': total_pulls,
            'rarity_distribution': rarity_distribution,
            'pity_progress': pity_progress,
            'gold_pulls_history': gold_pulls,
            'gold_rate': gold_rate,
            'rarity_counts': rarity_counts
        }
    
    return results


def analysis_report(results, pool_stats, pool_mapping, game_name, uid):
    current_logger = get_logger()
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"{game_name}抽卡记录分析报告")
    report_lines.append(f"用户UID: {uid}")
    report_lines.append("=" * 60)

    total_pulls_all = sum(stats['total_pulls'] for stats in pool_stats.values())
    total_6_star = sum(stats['rarity_counts'][6] for stats in pool_stats.values())

    report_lines.append(f"\n📊 总体统计:")
    report_lines.append(f"   总抽取次数: {total_pulls_all}次")
    report_lines.append(f"   6星获取数量: {total_6_star}个")
    if total_pulls_all > 0:
        report_lines.append(f"   综合6星获取率: {total_6_star/total_pulls_all*100:.2f}%")
    else:
        report_lines.append(f"   尚未获得6星")

    report_lines.append(f"\n🔍 各卡池详细分析:")
    report_lines.append("-" * 60)

    for pool_name, stats in results.items():
        this_pool = pool_mapping.get(pool_name, {})
        pool_type_name = this_pool.get('alias', '未知卡池类型')

        report_lines.append(f"\n🎯 卡池: {pool_name} ({pool_type_name})")
        report_lines.append(f"   ├─ 总抽取次数: {stats['total_pulls']}次")
        report_lines.append(f"   ├─ 稀有度分布:")
        report_lines.append(f"   │   ├─ 2星: {stats['rarity_counts'][2]}个")
        report_lines.append(f"   │   ├─ 3星: {stats['rarity_counts'][3]}个")
        report_lines.append(f"   │   ├─ 4星: {stats['rarity_counts'][4]}个")
        report_lines.append(f"   │   ├─ 5星: {stats['rarity_counts'][5]}个")
        report_lines.append(f"   │   └─ 6星: {stats['rarity_counts'][6]}个")

        report_lines.append(f"   ├─ 当前保底进度: {stats['pity_progress']}抽未出6星")

        if stats['rarity_counts'][6] > 0:
            avg_gold_pull = stats['total_pulls'] / stats['rarity_counts'][6]
            report_lines.append(f"   ├─ 平均出金抽数: {avg_gold_pull:.1f}抽")
            report_lines.append(f"   └─ 6星获取率: {stats['gold_rate']:.2f}%")
        else:
            report_lines.append(f"   └─ 尚未获得6星")
    report_lines.append("=" * 60)

    return "\n".join(report_lines)

def analyze_history_file(history_file_path, catalog_data):
    """分析指定的抽卡记录文件"""
    try:
        logger = get_logger()
        logger.info(f"开始分析历史记录文件: {history_file_path}")

        # 1. 加载抽卡数据
        logger.info("正在加载数据...")
        with open(history_file_path, 'r', encoding='utf-8') as f:
            gacha_data = json.load(f)

        game_id = gacha_data['info']['game_id']
        game_name = gacha_data['info']['game_name']
        uid = gacha_data['info']['uid']
        logger.info(f"用户UID: {uid}")

        # 2. 分析抽卡数据
        logger.info("正在分析抽卡记录...")
        pool_stats, item_mapping, pool_mapping = analyze_gacha_data(gacha_data, catalog_data)

        # 3. 计算统计指标
        logger.info("正在计算统计指标...")
        results = calculate_statistics(pool_stats)

        # 4. 创建可视化图表
        logger.info("正在生成可视化图表...")
        create_visualizations(game_name, game_id, uid, results)

        # 5. 文字分析报告
        logger.info("生成文字分析报告...")
        report = analysis_report(results, pool_stats, pool_mapping, game_name, uid)
        logger.info(f"{report}")

        logger.info("\n✅ 分析完成！")

        # 6. 返回分析结果
        return {
            'success': True,
            'pool_stats': pool_stats,
            'report': report,
            'visualizations': {
                'gold_pull_intervals': f'gold_pull_intervals_{game_id}_{uid}.png',
                'rarity_analysis': f'gacha_analysis_{game_id}_{uid}.png'
            }
        }

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        return {'success': False, 'error': str(e)}
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
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
                
            return analyze_history_file(history_file_path, catalog_data)
        except Exception as e:
            self.logger.error(f"分析过程出错: {e}")
            return {'success': False, 'error': str(e)}
