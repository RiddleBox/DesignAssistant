# Phase 2.3 行动设计与资源承诺模块 - MVP实现

## 概述

Phase 2.3 将Phase 2.2的机会对象转化为可分阶段承诺、可控制风险、可动态调整的行动决策对象。

## 核心功能

- **行动姿态判断**：watch / validate / pilot / escalate / hold / stop
- **分阶段计划设计**：基于假设验证的阶段划分
- **Go/No-Go门槛**：每个阶段的继续/退出条件
- **资源承诺逻辑**：承诺递增机制
- **风险约束映射**：风险直接影响行动结构

## 目录结构

```
phase2.3_implementation/
├── src/
│   ├── models.py           # 数据模型定义
│   └── action_designer.py  # 核心处理器
├── examples/
│   ├── example_01.py       # 高优先级机会示例
│   └── example_02.py       # 低优先级机会示例
└── docs/                   # 设计文档
```

## 快速开始

```python
from models import OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner

# 创建机会对象
opportunity = OpportunityObject(
    opportunity_title="Your Opportunity",
    opportunity_thesis="Why this matters",
    supporting_evidence=["Evidence 1", "Evidence 2"],
    counter_evidence=["Risk 1"],
    key_assumptions=["Assumption 1", "Assumption 2"],
    uncertainty_map={"Factor": "Uncertainty level"},
    priority_level="high"
)

# 生成行动决策
request = ActionDesignRequest(request_id="req_001", opportunity_object=opportunity)
designer = ActionDesigner()
result = designer.design_action(request)

# 访问结果
print(result.action_decision.decision_posture)
print(result.action_decision.phased_plan)
```

## 运行示例

```bash
cd examples
python example_01.py  # 高优先级机会 -> validate姿态
python example_02.py  # 低优先级机会 -> watch姿态
```

## MVP范围

当前实现包含：
- ✅ 行动姿态判断（基于优先级和假设数量）
- ✅ 分阶段计划生成（1-3个阶段）
- ✅ Go/No-Go条件设计
- ✅ 退出条件设计
- ✅ 风险识别与映射
- ✅ 资源承诺逻辑生成

当前不包含：
- ❌ 完整预算系统
- ❌ 复杂决策树
- ❌ 多Agent编排
- ❌ 长篇建议文档生成

## 设计文档

详细设计方案见：
- [phase2.3_设计方案.md](../phase2_plan/phase2.3_设计方案.md)
- [phase2.3_roles.md](../phase2_plan/phase2_roles/phase2.3_roles.md)

## 版本

v0.1-mvp (2026-03-16)
