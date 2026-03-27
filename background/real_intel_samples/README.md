# Real Intel Samples for Phase 2.1 Testing
# Format: IntelligenceDecodeRequest (schemas.py)
# Source: daily_intel_collector.py auto-collected 2026-03-24

---

## 样本列表

### 有效信号（7条）

| 文件 | source_id | signal_type | 核心事件 |
|------|-----------|-------------|---------|
| sample_001 | real_001 | capital | 沙特Savvy 60亿美元收购沐瞳 |
| sample_002 | real_002 | capital | 中国游戏市场2月收入332亿，同比+19% |
| sample_003 | real_003 | team | Ubisoft关闭Red Storm游戏开发，裁员105人 |
| sample_004 | real_004 | technical | Capcom宣布引入生成式AI加速生产 |
| sample_005 | real_005 | market | 三角洲行动开年达成5000万DAU |
| sample_006 | real_006 | technical | Square Enix与Google合作，Gemini驱动Dragon Quest NPC对话 |
| sample_007 | real_007 | team | Xbox再次出现高层离职潮 |
| sample_008 | real_008 | market | Crimson Desert首日销量突破200万 |
| sample_009 | real_009 | technical | 网易AI工具替代外包测试结果初现 |
| sample_010 | real_010 | capital | Epic赢得反垄断诉讼，Fortnite重返Google Play |
| sample_011 | real_011 | market | 独立游戏自发行趋势：内容平台削弱传统发行商渠道价值 |

### 噪音样本（3条，预期decoder输出低强度或空信号）

| 文件 | source_id | 噪音类型 | 说明 |
|------|-----------|---------|------|
| noise_001 | noise_001 | 财报套话 | 标准季报措辞，无具体战略变化 |
| noise_002 | noise_002 | 常规版本更新 | 原神4.5版本上线公告，运营例行内容 |
| noise_003 | noise_003 | 公关稿 | Ubisoft游戏10周年纪念视频，无实质信号 |

---

## 使用方法

```python
import json
from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest

decoder = IntelligenceDecoder(api_key=YOUR_KEY)

with open("background/real_intel_samples/sample_001_capital_moonton_acquisition.json") as f:
    data = json.load(f)
    # 移除 _noise_label 字段（噪音样本专用，非schema字段）
    data.pop("_noise_label", None)

request = IntelligenceDecodeRequest(**data)
result = decoder.decode(request)
print(result.model_dump_json(indent=2))
```

## 预期结果

- **有效信号**：intensity_score >= 6，signals 列表非空
- **噪音样本**：signals 为空列表，或 intensity_score <= 3
- **noise_001**（财报）：可能提取到 market 信号但强度极低
- **noise_002**（版本更新）：预期 signals = []
- **noise_003**（公关稿）：预期 signals = []

---

## Ground Truth 判断标准

**信号（正例）的充要条件：内容描述了一个对行业格局有实质影响、或预示范式转移的具体事实。**

### ✅ 构成信号

- 具体数字 + 具体主体 + 具体变化（收购金额、裁员人数、销量里程碑）
- 新技术/新政策首次落地（Capcom 引入生成式 AI、欧盟 DMA 处罚）
- 结构性变化（工作室关闭、高管离职潮、市场份额转移）

### ❌ 不构成信号

| 类型 | 例子 | 原因 |
|------|------|------|
| 经验分享 / GDC 演讲 | Warframe 13年live service经验（_029） | 已验证的历史模式，非新变化 |
| 泛战略表态 | Disney"游戏是核心收入支柱"（_028） | 无具体行动，无时间节点 |
| 续报 / 更新 | Crimson Desert第5天3M销量（_040） | 基准已在首日建立，续报无新格局意义 |
| 跨行业无关联 | Zuckerberg AI co-CEO（_032） | 与游戏行业无直接因果关系 |
| 常规运营 | DLC路线图公告、赛事赛程 | 行业例行内容，无结构变化 |

### 边界原则

- **有具体数字但影响弱**（如 _noise_005 澳大利亚140万澳元拨款）：可抽取但 intensity ≤ 5
- **演讲中夹带的具体事实**（如 Switch 2 移植）：若只是顺带一提、非演讲主旨，intensity ≤ 4，可判噪音
- **续报原则**：同一事件的后续报道，若无新的格局变化（仅数字增长），视为噪音
