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
