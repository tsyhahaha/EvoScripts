# 非目标数据示例

将应该被过滤掉的数据样本放在此目录。

## 用途
- 帮助 Judge Agent 理解什么数据应该被排除
- 为 Code Agent 提供反例参考
- 明确边界条件

## 文件格式
- `.json` - 单条示例
- `.jsonl` - 多条示例

## 命名建议
使用描述性名称说明为什么被排除，例如：
- `incomplete_messages.json` - 消息不完整
- `wrong_language.json` - 语言不符合要求
- `too_short.json` - 对话太短
- `missing_fields.json` - 缺少必要字段
