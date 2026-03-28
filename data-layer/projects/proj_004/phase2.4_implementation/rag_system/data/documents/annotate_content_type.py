"""
批量给 43 条文档补标 content_type 字段
标注依据：PHASE2_4_CONTEXT_PACKET_PROTOCOL.md v1.0

标注规则：
- case_record：必须有主体+动作+结果三要素，否则降级为 background
- market_data：必须包含可引用的具体数字和来源
- background：泛知识/介绍/分析，无具体案例或数字
- glossary：以术语定义为主
- few_shot_example：含输入输出对的样例（当前无此类文档）
- constraint_rule：规则/边界约束（当前无此类文档）
"""

import yaml
import os

# 人工标注结果（基于 title + category + tags 判断）
ANNOTATIONS = {
    # game_design 类：大多是方法/原则/设计介绍 → background
    # 但 kb_036 是 NPC AI 设计，kb_005 是 F2P 经济系统（含设计规则）
    "kb_001": "background",         # 原神开放世界设计范式 —— 以设计介绍为主，无具体结果数据
    "kb_004": "background",         # Roguelike 核心机制 —— 设计原则介绍
    "kb_005": "constraint_rule",    # F2P 经济系统设计 —— 含货币/变现边界约束规则
    "kb_008": "background",         # Battle Royale 设计要素 —— 设计原则
    "kb_011": "background",         # SLG 核心玩法设计 —— 设计原则
    "kb_013": "background",         # 超休闲游戏设计 —— 设计+发行介绍
    "kb_014": "background",         # 游戏内社交系统设计 —— 设计原则
    "kb_017": "constraint_rule",    # 游戏数值策划基础 —— 数值平衡规则/成长曲线约束
    "kb_020": "background",         # 卡牌构筑游戏设计 —— 设计介绍
    "kb_022": "background",         # 游戏音效设计基础 —— 技术介绍
    "kb_023": "background",         # MMORPG 副本设计原则 —— 设计原则
    "kb_024": "background",         # 放置游戏设计 —— 设计原则
    "kb_025": "background",         # 新手引导设计 —— UX 设计原则
    "kb_030": "background",         # 关卡设计原则 —— 设计原则
    "kb_033": "background",         # 游戏 UI/UX 设计原则 —— 设计原则
    "kb_036": "background",         # 游戏 AI/NPC 行为树 —— 技术原理介绍（无真实案例结果）
    "kb_039": "background",         # 游戏音乐与情感设计 —— 设计原则
    "kb_043": "few_shot_example",   # 提取射击留存核心洞察 —— 人工精选insight，含分析逻辑，可作少样本参考

    # market_trend 类：有些含数字/趋势分析 → market_data；有些是泛分析 → background
    "kb_002": "market_data",        # 二次元手游市场趋势2024 —— 含市场规模、增长率数据
    "kb_006": "market_data",        # 全球手游市场规模与增长预测2024-2026 —— 含规模/增长数据
    "kb_009": "market_data",        # 中国游戏出海市场分析2024 —— 含出海收入/市场份额数据
    "kb_012": "background",         # 日本手游市场特征 —— 特征描述为主，本地化策略
    "kb_015": "market_data",        # 东南亚游戏市场机会 —— 含市场规模/渗透率数据
    "kb_018": "background",         # 游戏 UA 策略 —— 策略方法论，非数据
    "kb_021": "market_data",        # 游戏直播与电竞市场分析 —— 含收视/收入数据
    "kb_026": "market_data",        # 2024 全球游戏并购趋势 —— 含并购金额/数量数据
    "kb_029": "background",         # 独立游戏发行策略 —— 策略方法论
    "kb_031": "background",         # 游戏本地化策略 —— 策略方法论
    "kb_035": "market_data",        # 游戏付费模式对比分析 —— 含各模式收入占比数据
    "kb_038": "background",         # 游戏运营活动设计 —— 运营方法论
    "kb_040": "background",         # 游戏社区管理 —— 方法论介绍
    "kb_042": "market_data",        # 市场趋势日报2026-03-23 —— 含 capital/market 数据（auto-collected）

    # tech_innovation 类：技术介绍为主 → background；kb_041 是技术日报（可能含事件）
    "kb_003": "background",         # AIGC 在游戏开发中的应用 —— 技术介绍
    "kb_007": "background",         # Unity vs Unreal 选型指南 —— 技术对比介绍
    "kb_010": "background",         # 云游戏技术架构与商业模式 —— 技术+商业介绍
    "kb_016": "background",         # 游戏服务器架构设计 —— 技术原理
    "kb_019": "background",         # UE5 Nanite/Lumen —— 技术特性介绍
    "kb_027": "background",         # 游戏反外挂技术 —— 技术介绍
    "kb_028": "background",         # 游戏数据分析与 BI —— 技术方法论
    "kb_032": "background",         # VR/AR 游戏设计 —— 技术+设计介绍
    "kb_034": "background",         # 版本管理与更新策略 —— 技术方法论
    "kb_037": "background",         # 游戏性能优化技术 —— 技术原理
    "kb_041": "background",         # 技术创新日报2026-03-23 —— 日报摘要（auto-collected，无具体案例结果）
}

# 执行标注
docs_dir = os.path.dirname(os.path.abspath(__file__))
changed = 0
skipped = 0

for doc_id, ct in ANNOTATIONS.items():
    fpath = os.path.join(docs_dir, f"{doc_id}.yaml")
    if not os.path.exists(fpath):
        print(f"[SKIP] {doc_id} 文件不存在")
        skipped += 1
        continue

    with open(fpath, encoding='utf-8') as f:
        content = f.read()
        data = yaml.safe_load(content)

    existing = data.get('content_type')
    if existing == ct:
        print(f"[OK]   {doc_id} content_type 已是 {ct}，跳过")
        skipped += 1
        continue

    # 写入 content_type 字段（追加到 yaml 末尾，保持原文件其余内容不变）
    if 'content_type:' in content:
        # 替换已有字段
        import re
        content = re.sub(r'^content_type:.*$', f'content_type: {ct}', content, flags=re.MULTILINE)
    else:
        # 追加新字段
        content = content.rstrip('\n') + f'\ncontent_type: {ct}\n'

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[SET]  {doc_id} → {ct}")
    changed += 1

print(f"\n完成：{changed} 条已标注，{skipped} 条跳过")

# 打印缺口摘要
from collections import Counter
ct_counts = Counter(ANNOTATIONS.values())
print("\n标注分布：")
for ct, n in sorted(ct_counts.items(), key=lambda x: -x[1]):
    print(f"  {ct:<20} {n} 条")
print(f"\n⚠️  case_record = {ct_counts.get('case_record', 0)} 条（严重不足，需补充真实案例文档）")
