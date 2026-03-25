# 目标数据示例

将符合你筛选条件的数据样本放在此目录。

## 用途
- 帮助 Judge Agent 理解什么是"目标数据"
- 为 Code Agent 提供正例参考
- 在 Taste Alignment 阶段辅助生成 Rubric

## 文件格式
- `.json` - 单条示例（JSON 对象）
- `.jsonl` - 多条示例（每行一个 JSON 对象）

## 命名建议
使用描述性名称，例如：
- `complete_conversation.json` - 完整对话示例
- `multi_turn_dialog.json` - 多轮对话示例
- `with_metadata.json` - 包含元数据的示例
