# DesignAssistant 链路观察面板

## 启动

```bash
cd data-layer/projects/proj_004/dashboard
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`

## 功能

- **配置区**：API Key / Base URL / 模型（自动从 .env 读取）
- **样本预览**：显示 incoming/ 目录当前文件
- **边跑边看**：点击运行后实时显示每步进度
- **2.1 情报解码**：每条样本的信号提取详情，支持点击展开原文/字段
- **2.2 机会判断**：机会标题/论点/支持证据/反对证据/关键假设/why_now/2.4证据追溯
- **2.3 行动设计**：鹰鸽辩论过程/分阶段计划/风险/退出条件
- **2.5 复盘归因**：关键发现（按严重度标色）/根因/Phase3优先项
- **报告下载**：直接下载生成的 Markdown 报告

## 依赖

```
pip install streamlit
```

其余依赖与主项目相同（已在项目环境中安装）。

## 目录位置

`dashboard/` 与 `phase2.x_implementation/` 平级，独立模块，
消费所有阶段的输出，不属于任何单一 phase。
