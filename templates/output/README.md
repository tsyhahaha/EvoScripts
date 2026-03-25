# 输出格式示例

定义清洗后数据的期望格式。

## 用途
- 如果需要数据转换（不仅仅是过滤），这里定义输出结构
- 可以包含 JSON Schema 用于验证

## 文件格式
- `.json` - 输出数据示例
- `.schema.json` - JSON Schema 定义

## 示例

### 输出示例 (output_format.json)
```json
{
  "id": "conv_001",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "source": "...",
    "quality_score": 0.95
  }
}
```

### JSON Schema (output.schema.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "messages"],
  "properties": {
    "id": {"type": "string"},
    "messages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {"enum": ["user", "assistant", "system"]},
          "content": {"type": "string"}
        }
      }
    }
  }
}
```
