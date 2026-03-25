# 代码模版说明

将你的参考代码放在此目录下。Code Agent 会学习这些代码的：
- 命名风格
- 错误处理模式
- API 调用方式
- 数据验证逻辑

## 支持的文件类型
- `.py` - Python 源代码

## 示例文件命名建议
- `api_client.py` - API 调用模式
- `data_validation.py` - 数据验证逻辑
- `text_processing.py` - 文本处理函数
- `field_extraction.py` - 字段提取逻辑

## 模版编写建议

1. **保持简洁** - 只包含相关的代码片段
2. **添加注释** - 解释关键逻辑
3. **展示模式** - 体现你希望生成代码遵循的模式

```python
# 示例：数据验证模式
def validate_conversation(data: dict) -> bool:
    """检查对话数据是否完整。

    Args:
        data: JSONL 中的单条记录

    Returns:
        True 如果数据有效
    """
    # 必需字段检查
    required_fields = ["messages", "source", "timestamp"]
    if not all(field in data for field in required_fields):
        return False

    # 消息列表验证
    messages = data.get("messages", [])
    if not isinstance(messages, list) or len(messages) < 2:
        return False

    return True
```
