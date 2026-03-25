# EvoScripts

基于 **TDD + 数据驱动迭代** 的 JSONL 数据清洗脚本自动生成系统。

通过 LLM Agent 自动编写、测试、优化 Python 清洗脚本，直到达到目标精确率。

## 核心特性

- **自动化脚本生成** — Code Agent (Claude) 根据需求生成清洗脚本
- **智能评判系统** — Judge Agent (GPT-4o) 评估脚本效果，避免自评偏见
- **人机协作 (HITL)** — 关键节点人工确认，保证方向正确
- **模版系统** — 支持代码模版、正反例数据、输出格式定义
- **进化循环** — 自动迭代优化直到 Precision ≥ 90%

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd EvoScripts

# 安装依赖
pip install -e .

# 或使用 pip install
pip install -e ".[dev]"  # 包含开发依赖
```

## 配置

设置 API 密钥（环境变量或 `.env` 文件）：

```bash
export EVOSCRIPTS_ANTHROPIC_API_KEY="sk-ant-..."
export EVOSCRIPTS_OPENAI_API_KEY="sk-..."
```

查看当前配置：

```bash
evoscripts config
```

## 快速开始

### 基础用法

```bash
# 运行进化流程
evoscripts evolve data.jsonl "过滤掉不完整的对话记录"

# 使用模版
evoscripts evolve data.jsonl "提取多轮中文对话" --templates ./templates

# 指定输出路径和精确率阈值
evoscripts evolve data.jsonl "筛选高质量问答" \
    --templates ./templates \
    --output cleaner.py \
    --precision 0.95
```

### 其他命令

```bash
# 预览数据样本
evoscripts preview data.jsonl -n 10

# 测试已有脚本
evoscripts test cleaner.py data.jsonl -n 20

# 查看配置
evoscripts config
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1: Taste Alignment                      │
├─────────────────────────────────────────────────────────────────┤
│  1. 抽样 3-5 条数据                                               │
│  2. Judge Agent 生成评分规则 (Rubric)                             │
│  3. 人工审核/调整 Rubric                                          │
│  4. 锁定 Rubric 作为后续唯一标准                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Phase 2: Evolution Loop                         │
├─────────────────────────────────────────────────────────────────┤
│  1. Code Agent 生成清洗脚本                                       │
│  2. 抽样 30 条数据试跑                                            │
│  3. Judge Agent 评判结果 (TP/FP/TN/FN)                           │
│  4. 若 Precision < 90%，将 Bad Cases 反馈给 Code Agent            │
│  5. 重复直到达标或达到最大迭代次数                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    输出最终脚本 cleaner_final.py
```

## 模版系统

将参考资料放入 `templates/` 目录，系统会自动加载：

```
templates/
├── manifest.yaml              # 可选：元数据说明
├── code/                      # Python 代码模版
│   └── validation.py          # 数据验证模式参考
├── examples/
│   ├── target/                # 目标数据示例（应被选中）
│   │   └── good_conversation.json
│   └── non_target/            # 非目标数据示例（应被过滤）
│       └── incomplete.json
└── output/                    # 输出格式定义
    └── expected_format.json
```

### 各类型模版的作用

| 目录 | 内容 | 用途 |
|------|------|------|
| `code/` | `.py` 文件 | Code Agent 参考代码风格和模式 |
| `examples/target/` | `.json` / `.jsonl` | 正例 — 这些数据应该被选中 |
| `examples/non_target/` | `.json` / `.jsonl` | 反例 — 这些数据应该被过滤 |
| `output/` | `.json` / `.schema.json` | 定义期望的输出格式 |

### 示例：目标数据 (target)

```json
// templates/examples/target/multi_turn.json
{
  "messages": [
    {"role": "user", "content": "什么是机器学习？"},
    {"role": "assistant", "content": "机器学习是人工智能的一个分支..."},
    {"role": "user", "content": "有哪些常见算法？"},
    {"role": "assistant", "content": "常见的机器学习算法包括..."}
  ],
  "source": "wiki_qa",
  "language": "zh"
}
```

### 示例：非目标数据 (non_target)

```json
// templates/examples/non_target/incomplete.json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "source": "unknown"
}
```

## 配置选项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `EVOSCRIPTS_ANTHROPIC_API_KEY` | - | Anthropic API 密钥 |
| `EVOSCRIPTS_OPENAI_API_KEY` | - | OpenAI API 密钥 |
| `EVOSCRIPTS_CODE_AGENT_MODEL` | `claude-sonnet-4-20250514` | 代码生成模型 |
| `EVOSCRIPTS_JUDGE_MODEL` | `gpt-4o` | 评判模型 |
| `EVOSCRIPTS_TASTE_SAMPLE_SIZE` | `5` | Taste Alignment 抽样数 |
| `EVOSCRIPTS_EVOLUTION_SAMPLE_SIZE` | `30` | 每轮进化抽样数 |
| `EVOSCRIPTS_PRECISION_THRESHOLD` | `0.9` | 目标精确率 |
| `EVOSCRIPTS_MAX_ITERATIONS` | `10` | 最大迭代次数 |
| `EVOSCRIPTS_HITL_INTERVAL` | `2` | 每 N 轮人工确认 |
| `EVOSCRIPTS_SANDBOX_TIMEOUT` | `30` | 脚本执行超时(秒) |

## 项目结构

```
EvoScripts/
├── pyproject.toml
├── evoscripts/
│   ├── cli.py                 # CLI 入口
│   ├── config.py              # 配置管理
│   ├── orchestrator/
│   │   ├── engine.py          # 主控状态机
│   │   ├── sampler.py         # 数据抽样
│   │   └── state.py           # 状态定义
│   ├── agents/
│   │   ├── base.py            # Agent 基类
│   │   ├── code_agent.py      # Claude 代码生成
│   │   └── judge_agent.py     # GPT-4o 评判
│   ├── sandbox/
│   │   └── executor.py        # 安全执行沙盒
│   ├── templates/
│   │   └── __init__.py        # 模版加载器
│   └── prompts/
│       ├── code_gen.py        # Code Agent prompts
│       └── judge.py           # Judge prompts
├── templates/                  # 用户模版目录
│   ├── code/
│   ├── examples/
│   │   ├── target/
│   │   └── non_target/
│   └── output/
├── tests/
└── docs/
    └── base.md                # 系统设计文档
```

## 生成的脚本格式

EvoScripts 生成的清洗脚本遵循统一接口：

```python
def is_target(data: dict) -> bool:
    """判断数据是否为目标数据。

    Args:
        data: JSONL 中的单条记录 (dict)

    Returns:
        True 如果是目标数据，False 如果应该被过滤
    """
    # 生成的清洗逻辑
    ...
```

使用示例：

```python
import json
from cleaner_final import is_target

with open("data.jsonl") as f:
    for line in f:
        record = json.loads(line)
        if is_target(record):
            print(json.dumps(record, ensure_ascii=False))
```

## License

MIT
