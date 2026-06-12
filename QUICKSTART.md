# 🚀 快速开始指南

5分钟上手学练测一体化能力提升系统。

## 前置条件

- Python 3.10+
- Node.js 18+（前端开发）
- 一个兼容OpenAI API的LLM API Key

## 步骤1：安装依赖

```bash
cd LLMs/skill_trainer
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

## 步骤2：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的API Key：

```env
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
```

## 步骤3：启动系统

### 方式1：完整系统（推荐）

```bash
python run.py
```

自动启动后端API（端口8000）和前端界面（端口5173），访问 http://localhost:5173

### 方式2：命令行直接生成

```bash
# 完整流程
python run.py "Java后端开发工程师" --name "张三" --level "初级"

# 指定学生数据
python run.py "前端开发" --name "李四" --level "中级" --data student.json
```

### 方式3：仅启动后端API

```bash
python run.py --no-frontend
# 访问 http://localhost:8000/docs 查看API文档
```

## 步骤4：使用系统

1. **首次使用**：输入姓名 → 填写目标岗位和级别 → 等待3-5分钟自动生成
2. **再次使用**：输入已有姓名 → 进入伴学模式
3. **查看报告**：顶部标签切换学习/训练/考核/评估
4. **伴学对话**：在伴学模式中与AI助手交流

## 步骤5：查看输出

所有输出保存在 `output/` 目录：

```bash
output/
├── result_张三.json        # 完整结构化数据
├── 能力画像_张三.json       # 能力画像（含雷达图数据）
├── 能力画像_张三.xlsx       # Excel含雷达图
├── 学习任务_张三.pdf        # 学习任务PDF
├── 学习任务_张三.docx       # 学习任务Word
├── 01_岗位分析_张三.md      # 阶段输出
├── 02_学习内容_张三.md
├── 03_训练任务_张三.md
├── 04_测试试卷_张三.md
└── 05_评估报告_张三.md
```

## 常见问题

**Q: 提示API Key错误？**
A: 检查 `.env` 文件中 `LLM_API_KEY` 是否正确设置。

**Q: 生成很慢？**
A: 完整流程需要3-5分钟，涉及6次LLM调用。可在终端查看实时进度。

**Q: 训练任务为空？**
A: 系统有自动重试和降级机制，通常可自动恢复。如仍失败，检查LLM服务状态。

**Q: 前端白屏？**
A: 确认前端依赖已安装（`cd frontend && npm install`），且后端API已启动。

**Q: 如何切换LLM模型？**
A: 修改 `.env` 中的 `LLM_MODEL` 和 `LLM_BASE_URL`。
