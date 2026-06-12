# 部署指南

## 1. 环境要求

| 组件 | 最低版本 |
|------|---------|
| Python | 3.10+ |
| pip | 23.0+ |
| 操作系统 | Windows / Linux / macOS |

## 2. 安装

```bash
# 克隆/进入项目目录
cd LLMs/skill_trainer

# 安装依赖
pip install -r requirements.txt
```

## 3. 配置 LLM API

```bash
# 创建 .env 文件（从模板复制）
cp .env.example .env

# 编辑 .env，填入你的 API 密钥
```

`.env` 内容示例:
```ini
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
OUTPUT_DIR=output
```

支持的LLM服务:
- OpenAI: `LLM_BASE_URL=https://api.openai.com/v1`
- 通义千问: `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- DeepSeek: `LLM_BASE_URL=https://api.deepseek.com/v1`
- 本地模型 (vLLM/Ollama): `LLM_BASE_URL=http://localhost:8000/v1`

## 4. 启动服务

### 方式一：直接启动

```bash
# 默认 8000 端口
python api.py

# 指定端口
python api.py --port 8080
```

### 方式二：uvicorn命令行

```bash
# 开发模式（热重载）
uvicorn api:app --reload --port 8000

# 生产模式（多worker）
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### 方式三：Docker（可选）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t skill-trainer .
docker run -p 8000:8000 --env-file .env skill-trainer
```

## 5. 验证

```bash
# 健康检查
curl http://localhost:8000/api/health

# 演示模式
curl http://localhost:8000/api/demo

# 访问 API 文档
open http://localhost:8000/docs
```

## 6. CLI 模式

无需启动服务，直接命令行使用：

```bash
# 演示模式
python run.py demo

# 能力画像
python run.py profile --name "张三" --major "计算机"

# 岗位匹配
python run.py match --name "张三" --positions "Java后端,数据分析"

# 路径规划
python run.py plan --name "张三" --position "Java后端开发工程师"

# 完整学练测流程（需LLM）
python run.py "Java后端开发工程师" --name "张三"
```

## 7. 常见问题

**Q: 启动报 `ModuleNotFoundError: No module named 'fastapi'`**
```bash
pip install -r requirements.txt
```

**Q: LLM调用报401**
检查 `.env` 中的 `LLM_API_KEY` 是否正确。

**Q: Windows 乱码**
系统已内置 UTF-8 编码兼容，如果仍有问题，运行前设置:
```bash
set PYTHONIOENCODING=utf-8
python api.py
```

**Q: PDF中文乱码**
系统会自动搜索系统字体。Windows 通常有 `simsun.ttc`。
