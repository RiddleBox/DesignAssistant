"""
生成100条样本数据
用于MVP版本测试
"""

import yaml
import random
from pathlib import Path

# 文档模板库
GAME_DESIGN_TEMPLATES = [
    {
        "title": "{game}的战斗系统设计分析",
        "content": """{game}的战斗系统具有以下设计特点：

核心机制：
1. {mechanic1}：{desc1}
2. {mechanic2}：{desc2}
3. {mechanic3}：{desc3}

设计亮点：
- 操作深度与上手难度的平衡
- 正向反馈循环设计
- 角色差异化定位

成功要素：
- 清晰的战斗目标
- 丰富的策略空间
- 优秀的打击感

适用场景：{scenario}
""",
        "tags": ["战斗系统", "核心玩法"],
        "sources": ["GDC演讲", "开发者访谈", "设计文档分析"]
    },
    {
        "title": "{game}的经济系统设计",
        "content": """{game}的经济系统采用了{model}模式：

货币体系：
- 硬通货：{currency1}（获取方式：{acquire1}）
- 软通货：{currency2}（获取方式：{acquire2}）

平衡策略：
1. 产出控制：每日/每周产出上限
2. 消耗设计：多样化消耗途径
3. 通货膨胀控制：{inflation_control}

商业化设计：
- 付费点分布
- 性价比设计
- 免费玩家体验保障

数据分析：
- 平均付费率：{arpu}%
- 付费用户ARPPU：${arppu}
""",
        "tags": ["经济系统", "数值设计"],
        "sources": ["行业分析报告", "数据拆解"]
    },
]

MARKET_TREND_TEMPLATES = [
    {
        "title": "{region}手游市场{year}年度报告",
        "content": """{region}手游市场在{year}年呈现以下特点：

市场规模：
- 总收入：${revenue}亿
- 同比增长：{growth}%
- 下载量：{downloads}亿次

用户特征：
- 活跃用户：{mau}亿
- 平均时长：{avg_time}分钟/日
- 付费率：{pay_rate}%

热门品类：
1. {genre1}：占比{share1}%
2. {genre2}：占比{share2}%
3. {genre3}：占比{share3}%

趋势预测：
- {trend1}
- {trend2}
- {trend3}
""",
        "tags": ["市场分析", "数据报告"],
        "sources": ["Sensor Tower", "App Annie", "行业报告"]
    },
]

TECH_INNOVATION_TEMPLATES = [
    {
        "title": "{tech}技术在游戏中的应用",
        "content": """{tech}技术正在改变游戏开发：

技术原理：
{principle}

应用场景：
1. {app1}：{app_desc1}
2. {app2}：{app_desc2}
3. {app3}：{app_desc3}

实施效果：
- 效率提升：{efficiency}%
- 成本降低：{cost_reduction}%
- 质量改善：{quality_improvement}

代表案例：
- {case1}
- {case2}

发展前景：
{prospect}
""",
        "tags": ["技术创新", "开发工具"],
        "sources": ["技术峰会", "公司博客", "学术论文"]
    },
]

# 填充数据
GAMES = [
    ("王者荣耀", "MOBA", "腾讯"),
    ("和平精英", "战术竞技", "腾讯"),
    ("原神", "开放世界ARPG", "米哈游"),
    ("崩坏：星穹铁道", "回合制RPG", "米哈游"),
    ("明日方舟", "塔防", "鹰角网络"),
    ("蛋仔派对", "派对游戏", "网易"),
    ("金铲铲之战", "自走棋", "腾讯"),
    ("幻塔", "MMO", "完美世界"),
    ("阴阳师", "回合制", "网易"),
    ("光·遇", "社交冒险", "thatgamecompany"),
]

REGIONS = ["中国", "日本", "美国", "东南亚", "欧洲"]
YEARS = ["2022", "2023", "2024"]
TECHS = [
    ("云游戏", "通过云端渲染，降低设备要求"),
    ("AI生成", "使用生成式AI辅助内容创作"),
    ("实时渲染", "光线追踪和实时全局光照"),
    ("程序化生成", "算法自动生成游戏内容"),
    ("跨平台同步", "多端数据实时同步"),
]

def generate_document(doc_id: int, category: str) -> dict:
    """生成单条文档"""

    if category == "game_design":
        game, genre, company = random.choice(GAMES)
        template = random.choice(GAME_DESIGN_TEMPLATES)

        doc = {
            "id": f"kb_{doc_id:03d}",
            "title": template["title"].format(game=game),
            "category": category,
            "tags": template["tags"] + [genre, company],
            "content": template["content"].format(
                game=game,
                mechanic1="技能组合",
                desc1="通过不同技能搭配创造连招",
                mechanic2="资源管理",
                desc2="能量/怒气等资源的合理分配",
                mechanic3="位置策略",
                desc3="站位和走位的战术意义",
                model="双货币" if random.random() > 0.5 else "单货币",
                currency1="钻石",
                acquire1="充值获得",
                currency2="金币",
                acquire2="游戏内获取",
                inflation_control="定期回收机制",
                arpu=random.randint(3, 8),
                arppu=random.randint(50, 200),
                scenario="中重度手游"
            ),
            "metadata": {
                "source": random.choice(template["sources"]),
                "confidence": round(random.uniform(0.75, 0.95), 2),
                "last_updated": f"2024-{random.randint(1, 3):02d}-{random.randint(1, 28):02d}"
            }
        }

    elif category == "market_trend":
        region = random.choice(REGIONS)
        year = random.choice(YEARS)
        template = random.choice(MARKET_TREND_TEMPLATES)

        doc = {
            "id": f"kb_{doc_id:03d}",
            "title": template["title"].format(region=region, year=year),
            "category": category,
            "tags": template["tags"] + [region, year],
            "content": template["content"].format(
                region=region,
                year=year,
                revenue=random.randint(100, 500),
                growth=random.randint(5, 30),
                downloads=random.randint(10, 100),
                mau=random.randint(1, 10),
                avg_time=random.randint(30, 90),
                pay_rate=random.randint(2, 15),
                genre1="RPG",
                share1=random.randint(25, 40),
                genre2="策略",
                share2=random.randint(15, 25),
                genre3="休闲",
                share3=random.randint(10, 20),
                trend1="二次元品类持续增长",
                trend2="中重度游戏用户时长增加",
                trend3="跨平台游戏成为新趋势"
            ),
            "metadata": {
                "source": random.choice(template["sources"]),
                "confidence": round(random.uniform(0.80, 0.92), 2),
                "last_updated": f"2024-{random.randint(1, 3):02d}-{random.randint(1, 28):02d}"
            }
        }

    else:  # tech_innovation
        tech, principle = random.choice(TECHS)
        template = random.choice(TECH_INNOVATION_TEMPLATES)

        doc = {
            "id": f"kb_{doc_id:03d}",
            "title": template["title"].format(tech=tech),
            "category": category,
            "tags": template["tags"] + ["前沿技术"],
            "content": template["content"].format(
                tech=tech,
                principle=principle,
                app1="内容创作",
                app_desc1="加速美术和文本资产生成",
                app2="智能NPC",
                app_desc2="AI驱动的非玩家角色",
                app3="个性化推荐",
                app_desc3="基于AI的内容推荐系统",
                efficiency=random.randint(30, 60),
                cost_reduction=random.randint(20, 50),
                quality_improvement="显著提升",
                case1="米哈游在《原神》中的应用",
                case2="腾讯在《王者荣耀》中的应用",
                prospect="预计未来3年内成为行业标准"
            ),
            "metadata": {
                "source": random.choice(template["sources"]),
                "confidence": round(random.uniform(0.85, 0.95), 2),
                "last_updated": f"2024-{random.randint(1, 3):02d}-{random.randint(1, 28):02d}"
            }
        }

    return doc


def main():
    """生成100条样本数据"""
    output_dir = Path(__file__).parent / "data" / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧文件（保留kb_001-003示例）
    for f in output_dir.glob("kb_*.yaml"):
        if f.stem not in ["kb_001", "kb_002", "kb_003"]:
            f.unlink()

    print("📝 生成样本数据...")

    # 生成97条新数据（已有3条示例）
    categories = ["game_design", "market_trend", "tech_innovation"]
    category_distribution = [40, 30, 30]  # 40条设计，30条市场，30条技术

    doc_id = 4
    for i, category in enumerate(categories):
        count = category_distribution[i]
        for _ in range(count):
            doc = generate_document(doc_id, category)

            output_path = output_dir / f"{doc['id']}.yaml"
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(doc, f, allow_unicode=True, sort_keys=False)

            doc_id += 1

    print(f"✅ 生成完成！共 {doc_id - 1} 条文档")
    print(f"📁 保存位置: {output_dir}")


if __name__ == '__main__':
    main()
