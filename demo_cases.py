"""岗位框架库 — 方向二专用"""

from models import CapabilityFramework, SkillPoint, SkillLevel


def get_demo_framework(position_name: str) -> CapabilityFramework:
    """获取岗位能力框架（预配置，不调LLM）"""
    framework_map = {
        "Java后端开发工程师": CapabilityFramework(
            position_name="Java后端开发工程师",
            position_description="负责企业级后端系统开发与维护",
            summary="要求Java核心技术扎实，熟悉Spring生态和分布式架构",
            skill_categories=["编程基础", "框架与工具", "数据与中间件", "架构与设计"],
            skill_points=[
                SkillPoint("SKILL_001", "Java核心技术", "Java语言、JVM、多线程",
                           "编程基础", SkillLevel.ADVANCED, keywords=["Java", "并发"]),
                SkillPoint("SKILL_002", "Spring生态", "Spring Boot/Cloud/MyBatis",
                           "框架与工具", SkillLevel.ADVANCED, keywords=["Spring"]),
                SkillPoint("SKILL_003", "数据库设计与优化", "MySQL、SQL优化、索引",
                           "数据与中间件", SkillLevel.INTERMEDIATE, keywords=["MySQL"]),
                SkillPoint("SKILL_004", "分布式系统", "微服务、RPC、分布式事务",
                           "架构与设计", SkillLevel.INTERMEDIATE, keywords=["分布式"]),
            ],
            required_qualities=["逻辑思维强", "团队协作", "责任心"],
        ),
        "前端开发工程师": CapabilityFramework(
            position_name="前端开发工程师",
            position_description="负责Web前端界面开发和交互设计",
            summary="要求前端三件套精通，熟悉主流前端框架",
            skill_categories=["基础知识", "框架技术", "工程化"],
            skill_points=[
                SkillPoint("SKILL_001", "HTML/CSS/JS", "前端三件套基本功",
                           "基础知识", SkillLevel.ADVANCED, keywords=["HTML"]),
                SkillPoint("SKILL_002", "前端框架", "React/Vue.js/Angular",
                           "框架技术", SkillLevel.ADVANCED, keywords=["React"]),
                SkillPoint("SKILL_003", "工程化", "Webpack/Vite/TypeScript",
                           "工程化", SkillLevel.JUNIOR, keywords=["工程化"]),
            ],
        ),
        "Python开发工程师": CapabilityFramework(
            position_name="Python开发工程师",
            position_description="负责Python后端服务开发和数据处理",
            summary="要求Python技术栈精通",
            skill_categories=["编程基础", "Web框架", "数据处理"],
            skill_points=[
                SkillPoint("SKILL_001", "Python核心", "Python语法、异步编程、装饰器",
                           "编程基础", SkillLevel.ADVANCED, keywords=["Python"]),
                SkillPoint("SKILL_002", "Web框架", "Django/FastAPI/Flask",
                           "Web框架", SkillLevel.INTERMEDIATE, keywords=["Web"]),
                SkillPoint("SKILL_003", "数据处理", "Pandas/NumPy/ETL",
                           "数据处理", SkillLevel.INTERMEDIATE, keywords=["数据处理"]),
            ],
        ),
    }
    return framework_map.get(position_name, _build_generic_framework(position_name))


def _build_generic_framework(position_name: str) -> CapabilityFramework:
    """根据岗位名智能拆解技能点"""
    keyword_skills = {
        "agent": ["Agent架构设计", "LLM集成与调用", "工具链/Function Calling", "多Agent协作", "提示词工程"],
        "开发": ["编程语言", "开发框架", "数据库设计", "API设计", "版本控制"],
        "前端": ["HTML/CSS", "JavaScript/TypeScript", "React/Vue", "构建工具"],
        "后端": ["服务端编程", "数据库管理", "API开发", "系统设计", "中间件使用"],
        "算法": ["数据结构", "算法分析", "数学基础", "编程实现"],
        "数据": ["数据采集", "数据清洗", "统计分析", "可视化"],
        "测试": ["测试方法论", "自动化测试", "性能测试", "CI/CD"],
        "运维": ["Linux管理", "网络基础", "容器技术", "监控告警"],
        "java": ["Java核心", "Spring框架", "JVM调优", "并发编程"],
        "python": ["Python编程", "Web框架", "数据科学", "异步编程"],
    }

    pos_lower = position_name.lower()
    matched = []
    for kw, skills in keyword_skills.items():
        if kw in pos_lower:
            matched.extend(skills)

    if not matched:
        matched = ["核心技能一", "核心技能二", "核心技能三"]

    seen = set()
    unique = []
    for s in matched:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    return CapabilityFramework(
        position_name=position_name,
        position_description=f"{position_name}岗位能力要求",
        summary=f"{position_name}的核心能力框架",
        skill_categories=["核心技能"],
        skill_points=[
            SkillPoint(f"SKILL_{i+1:03d}", name, f"掌握{name}", "核心技能",
                       SkillLevel.INTERMEDIATE, keywords=[name])
            for i, name in enumerate(unique[:6])
        ],
    )
