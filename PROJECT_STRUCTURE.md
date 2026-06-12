# 📁 项目结构说明

## 目录结构

```
skill_trainer/
│
├── run.py              # 主程序入口（启动API+前端）
├── api.py              # FastAPI服务（REST + SSE + 伴学对话）
├── coordinator.py      # 协调器（6阶段流水线 + 多格式导出）
├── agents.py           # 7个Agent（含TutorAgent三层记忆系统）
├── models.py           # Pydantic数据模型（25+类）
├── promt.py            # 9个提示词模板
├── tools.py            # 7层级联JSON解析器
├── database.py         # SQLite数据库（7张表）
├── config.py           # 配置管理（环境变量）
├── demo_cases.py       # 演示数据
├── requirements.txt    # Python依赖（8个包）
├── .env.example        # 环境变量模板
├── .gitignore
├── README.md           # 项目文档
├── QUICKSTART.md       # 快速开始
├── PROJECT_STRUCTURE.md # 本文档
├── 技术论文.md          # 技术论文
├── docs/               # 补充文档
│   ├── ARCHITECTURE.md
│   ├── API_DOCS.md
│   └── DEPLOY.md
└── frontend/           # React前端
    ├── src/
    │   ├── pages/      # 首页/学习/训练/考核/评估/伴学
    │   ├── components/ # 通用组件（Layout/RadarChart等）
    │   ├── api/        # API客户端（client.js）
    │   ├── store.jsx   # 全局状态管理（Context API）
    │   └── index.jsx   # 入口
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

## 数据流

```
用户输入 (姓名 + 岗位 + 级别 + 可选简历)
    │
    ▼
api.py (SSE流式端点)
    │
    ▼
coordinator.run_full()
    │
    ├── 阶段0: RequirementAgent.analyze()
    │   └── 输出: CapabilityFramework (能力框架)
    │
    ├── 阶段0.5: ResumeEvaluatorAgent.evaluate() [可选]
    │   └── 输出: ResumeProfile (简历评估)
    │
    ├── 阶段1: LearningContentAgent.generate()
    │   └── 输出: LearningContentOutput (学习内容)
    │
    ├── 阶段2: TrainingTaskAgent.generate()
    │   └── 输出: TrainingPlan (训练计划)
    │
    ├── 阶段3: TestGeneratorAgent.generate()
    │   └── 输出: TestPaper (测试试卷)
    │
    ├── 阶段4: AssessmentAgent.evaluate()
    │   └── 输出: AssessmentReport (能力评估)
    │
    └── 自动导出: JSON + Excel + PDF + Word
```

## Agent 一览

| Agent | 功能 | 输入 | 输出 |
|-------|------|------|------|
| RequirementAgent | 岗位需求分析 | 岗位名 + 级别 | CapabilityFramework |
| ResumeEvaluatorAgent | 简历评估 | 简历文本 + 框架 | ResumeProfile |
| LearningContentAgent | 学习内容生成 | CapabilityFramework | LearningContentOutput |
| TrainingTaskAgent | 训练任务生成 | 框架 + 学习内容 | TrainingPlan |
| TestGeneratorAgent | 测试考核生成 | 框架 + 学习内容 | TestPaper |
| AssessmentAgent | 能力评估 | SystemState | AssessmentReport |
| TutorAgent | 伴学对话 | 消息 + 三层记忆 | 流式回复 |

## 数据库表

| 表名 | 用途 |
|------|------|
| students | 学生基本信息 |
| student_results | LLM生成的完整结果JSON |
| student_progress | 学习/训练完成进度 |
| student_test_scores | 考核成绩 |
| chat_messages | 对话历史（伴学助手） |
| chat_summaries | 对话摘要（长期记忆） |
| student_memory | 结构化记忆（偏好/薄弱点/话题） |

## 扩展指南

### 添加新的Agent
1. 在 `promt.py` 中添加提示词
2. 在 `models.py` 中添加相关数据模型
3. 在 `agents.py` 中创建Agent类（继承BaseAgent）
4. 在 `coordinator.py` 中注册并编排新Agent

### 切换LLM提供商
修改 `.env` 中的 `LLM_BASE_URL` 和 `LLM_MODEL`

### 自定义导出格式
在 `coordinator.py` 中添加新的 `_export_*` 方法，并在 `run_full()` 中调用
