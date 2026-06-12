# 学练测一体化能力提升系统 v2.0

> 🏆 桂林电子科技大学第二十一届研电赛"润建"专项赛 — **方向二：学练测一体化能力提升**

基于大语言模型多Agent协同的自适应学习系统，打通学习、训练与测评全过程，实现能力成长的可量化、可验证与可追踪。

## 🎯 核心功能

| 模块 | 功能 | 输出 |
|------|------|------|
| 📋 **岗位分析** | 目标岗位技能图谱 + 能力框架 | 10-25个技能点 · DAG依赖图 |
| 📄 **简历评估** | PDF简历解析 → 技能掌握度评估 | 初始能力画像 · 优劣势分析 |
| 📚 **学习内容** | AI生成模块化学习材料 | Markdown正文 · 20-60min/模块 |
| 🏋️ **训练任务** | 5种任务类型 + 综合场景模拟 | 练习/案例/项目 + 评价标准 |
| 📝 **测试考核** | 7种题型综合试卷 | 试卷 + 答案解析 |
| 📊 **能力评估** | 四维评分 + 雷达图 + 成长趋势 | 综合评分0-100 · 下阶段计划 |
| 🤖 **伴学助手** | 三层记忆个性化辅导 | 流式对话 · 记忆增强 |
| 📦 **多格式导出** | 自动生成4种格式 | JSON / Excel / PDF / Word |

## 🚀 快速开始

```bash
cd LLMs/skill_trainer
pip install -r requirements.txt
cp .env.example .env   # 填入 LLM_API_KEY

# 启动完整系统（API + 前端）
python run.py

# 或命令行直接生成
python run.py "Java后端开发工程师" --name "张三" --level "初级"
```

## 📡 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/full/stream` | SSE流式完整流程 |
| POST | `/api/tutor` | 伴学对话（三层记忆） |
| GET | `/api/students` | 学生列表 |
| GET | `/api/students/{name}/full` | 学生完整数据 |
| POST | `/api/students/{name}/progress` | 切换学习/训练进度 |
| POST | `/api/students/{name}/test-score` | 保存考核成绩 |
| POST | `/api/regenerate` | 重新生成指定阶段 |

## 🏗️ 项目结构

```
skill_trainer/
├── run.py              # 主程序入口（启动API+前端）
├── api.py              # FastAPI服务（REST + SSE）
├── coordinator.py      # 协调器（6阶段流水线 + 导出）
├── agents.py           # 7个Agent（含TutorAgent三层记忆）
├── models.py           # Pydantic数据模型
├── promt.py            # 9个提示词模板
├── tools.py            # 7层级联JSON解析器
├── database.py         # SQLite数据库（7张表）
├── config.py           # 配置管理
├── demo_cases.py       # 演示数据
├── requirements.txt    # Python依赖
├── .env.example        # 环境变量模板
├── .gitignore
├── README.md
├── 技术论文.md          # 技术论文
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_DOCS.md
│   └── DEPLOY.md
└── frontend/           # React前端
    ├── src/
    │   ├── pages/      # 首页/学习/训练/考核/评估/伴学
    │   ├── components/ # 通用组件
    │   ├── api/        # API客户端
    │   └── store.jsx   # 全局状态管理
    ├── package.json
    └── vite.config.js
```

## 📁 输出文件

系统在 `output/` 目录自动生成：

```
output/
├── result_{name}.json      # 完整结构化数据
├── 能力画像_{name}.json     # 能力画像JSON
├── 能力画像_{name}.xlsx     # Excel含雷达图
├── 学习任务_{name}.pdf      # 学习任务PDF
├── 学习任务_{name}.docx     # 学习任务Word
├── 01_岗位分析_{name}.md    # 阶段输出Markdown
├── 02_学习内容_{name}.md
├── 03_训练任务_{name}.md
├── 04_测试试卷_{name}.md
└── 05_评估报告_{name}.md
```

## 🏛️ 系统架构

```
前端 (React 18) ──REST/SSE──▶ 后端 (FastAPI)
                                    │
                              协调器 (Coordinator)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              岗位分析Agent    学习内容Agent    训练任务Agent
              简历评估Agent    测试考核Agent    能力评估Agent
                                    │
                              LLM (qwen-flash)
                                    │
                        JSON解析器 (7层级联)
                                    │
                        SQLite数据库 (7张表)
```

## 🔧 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + TailwindCSS |
| 后端 | FastAPI + SSE流式 |
| LLM | OpenAI SDK → DashScope (qwen-max) |
| 数据库 | SQLite (WAL模式) |
| 导出 | openpyxl / ReportLab / python-docx |

## 📄 License

本项目为桂林电子科技大学研究生电子设计竞赛参赛作品。
