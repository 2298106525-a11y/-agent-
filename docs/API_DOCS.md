# API 接口文档

Base URL: `http://localhost:8000`

## 1. 健康检查

```
GET /api/health
```

```json
{"status": "ok", "version": "2.0.0", "time": "2025-05-26T..."}
```

## 2. 演示模式

```
GET /api/demo
```

返回预设案例的完整画像 + 匹配 + 路径规划。≤3秒响应。

```bash
curl http://localhost:8000/api/demo | python -m json.tool
```

## 3. 能力画像

```
POST /api/profile
```

**请求体**:
```json
{
  "student": {
    "name": "张明", "major": "计算机科学与技术",
    "grade": "大四", "school": "XX大学",
    "raw_data": {"GPA": "3.6", "课程成绩": {"数据结构": 88}}
  }
}
```

**响应**: 画像JSON + `json_file` + `excel_file` 路径

```bash
curl -X POST http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"student":{"name":"张明","major":"计算机"}}'
```

## 4. 岗位匹配

```
POST /api/match
```

**请求体**:
```json
{
  "name": "张明", "major": "计算机",
  "scores": {"knowledge": 82, "skill": 75, "competency": 70, "experience": 55},
  "positions": ["Java后端开发工程师", "数据分析工程师", "前端开发工程师"]
}
```

**响应**: 匹配数组 + 差距明细 + 推荐理由

## 5. 路径规划

```
POST /api/plan
```

**请求体**:
```json
{
  "name": "张明",
  "position": "Java后端开发工程师",
  "match_score": 75.0
}
```

**响应**: `plan` JSON + `files` (json/excel/pdf/docx/md)

## 错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 422 | 请求体验证失败 |
| 500 | 服务器错误（自动降级） |
