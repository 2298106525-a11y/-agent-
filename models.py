"""
学练测一体化能力提升系统 - 数据模型模块

定义系统中所有核心数据结构：
- 岗位能力框架与技能图谱
- 学习内容与课程
- 训练任务与项目
- 测试考核与评分
- 能力评估与成长报告
- 能力画像+匹配+路径规划+案例数据
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================
# 枚举类型
# ============================================================

class SkillLevel(str, Enum):
    """技能等级"""
    BEGINNER = "beginner"          # 入门
    JUNIOR = "junior"              # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"          # 高级
    EXPERT = "expert"              # 专家


class LearningPhase(str, Enum):
    """学习阶段"""
    PROFILING = "profiling"                         # 能力画像
    REQUIREMENT_ANALYSIS = "requirement_analysis"   # 需求分析
    MATCHING = "matching"                           # 岗位匹配
    CONTENT_GENERATION = "content_generation"       # 内容生成
    TRAINING = "training"                           # 实践训练
    TESTING = "testing"                             # 测试考核
    ASSESSMENT = "assessment"                       # 能力评估
    PATH_PLANNING = "path_planning"                 # 路径规划
    COMPLETED = "completed"                         # 完成


class QuestionType(str, Enum):
    """题目类型"""
    SINGLE_CHOICE = "single_choice"     # 单选题
    MULTI_CHOICE = "multi_choice"       # 多选题
    TRUE_FALSE = "true_false"           # 判断题
    SHORT_ANSWER = "short_answer"       # 简答题
    CODING = "coding"                   # 编程题
    CASE_ANALYSIS = "case_analysis"     # 案例分析
    PROJECT = "project"                 # 项目考核


class TrainingType(str, Enum):
    """训练类型"""
    EXERCISE = "exercise"               # 练习题
    CASE_STUDY = "case_study"           # 案例分析
    SIMULATION = "simulation"           # 模拟实操
    MINI_PROJECT = "mini_project"       # 小项目
    FULL_PROJECT = "full_project"       # 完整项目
    PEER_REVIEW = "peer_review"         # 互评


# ============================================================
# 能力框架
# ============================================================

@dataclass
class SkillPoint:
    """技能点"""
    id: str
    name: str
    description: str
    category: str                        # 技能分类（如：编程基础、框架使用、架构设计）
    required_level: SkillLevel = SkillLevel.JUNIOR
    prerequisites: List[str] = field(default_factory=list)  # 前置技能点ID列表
    keywords: List[str] = field(default_factory=list)


@dataclass
class CapabilityFramework:
    """能力框架 - 完整的能力图谱"""
    position_name: str                    # 岗位名称
    position_description: str            # 岗位描述
    summary: str                         # 能力要求总结
    skill_categories: List[str] = field(default_factory=list)   # 技能分类列表
    skill_points: List[SkillPoint] = field(default_factory=list)  # 所有技能点
    required_qualities: List[str] = field(default_factory=list)  # 软素质要求
    career_path: List[str] = field(default_factory=list)        # 职业发展路径

    def get_skill_points_by_category(self, category: str) -> List[SkillPoint]:
        """按分类获取技能点"""
        return [sp for sp in self.skill_points if sp.category == category]


# ============================================================
# 学习内容
# ============================================================

@dataclass
class LearningModule:
    """学习模块"""
    id: str
    title: str
    description: str
    skill_point_id: str                  # 关联的技能点ID
    difficulty: SkillLevel = SkillLevel.BEGINNER
    estimated_minutes: int = 30
    order: int = 0                       # 学习顺序
    content: str = ""                    # 完整内容（Markdown）


@dataclass
class LearningPath:
    """学习路径 - 一系列学习模块组成的路径"""
    title: str
    description: str
    modules: List[LearningModule] = field(default_factory=list)
    total_estimated_minutes: int = 0
    prerequisites: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.total_estimated_minutes = sum(m.estimated_minutes for m in self.modules)


@dataclass
class LearningContent:
    """学习内容生成结果"""
    skill_point: SkillPoint
    learning_modules: List[LearningModule] = field(default_factory=list)
    reading_materials: List[str] = field(default_factory=list)  # 推荐阅读链接/参考资料
    key_concepts: List[str] = field(default_factory=list)       # 核心概念
    summary: str = ""                       # 内容总结


@dataclass
class LearningContentOutput:
    """学习内容生成的完整输出"""
    framework: CapabilityFramework
    learning_paths: List[LearningPath] = field(default_factory=list)
    contents: List[LearningContent] = field(default_factory=list)
    total_modules: int = 0
    total_minutes: int = 0


# ============================================================
# 训练任务
# ============================================================

@dataclass
class TrainingTask:
    """训练任务"""
    id: str
    title: str
    description: str
    type: TrainingType = TrainingType.EXERCISE
    skill_point_id: str = ""               # 关联技能点
    difficulty: SkillLevel = SkillLevel.BEGINNER
    requirements: List[str] = field(default_factory=list)  # 任务要求
    hints: List[str] = field(default_factory=list)         # 提示
    reference_solution: str = ""           # 参考解法/答案
    evaluation_criteria: List[str] = field(default_factory=list)  # 评价标准
    estimated_minutes: int = 30


@dataclass
class TrainingScenario:
    """训练场景 - 模拟真实工作场景"""
    id: str
    title: str
    description: str
    context: str                           # 场景背景描述
    tasks: List[TrainingTask] = field(default_factory=list)
    difficulty: SkillLevel = SkillLevel.INTERMEDIATE
    expected_outcome: str = ""             # 预期产出


@dataclass
class TrainingPlan:
    """训练计划"""
    title: str
    description: str
    scenarios: List[TrainingScenario] = field(default_factory=list)
    tasks: List[TrainingTask] = field(default_factory=list)
    total_tasks: int = 0
    total_estimated_hours: float = 0.0


# ============================================================
# 测试考核
# ============================================================

@dataclass
class TestQuestion:
    """测试题目"""
    id: str
    question_type: QuestionType
    question_text: str
    skill_point_id: str = ""
    difficulty: SkillLevel = SkillLevel.BEGINNER
    options: List[str] = field(default_factory=list)        # 选择题选项
    correct_answer: str = ""                # 正确答案
    explanation: str = ""                   # 答案解析
    score: float = 1.0                      # 分值
    tags: List[str] = field(default_factory=list)


@dataclass
class TestPaper:
    """测试试卷"""
    id: str
    title: str
    description: str
    questions: List[TestQuestion] = field(default_factory=list)
    total_score: float = 0.0
    time_limit_minutes: int = 60
    passing_score: float = 60.0
    skill_points_covered: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.total_score = sum(q.score for q in self.questions)


@dataclass
class TestResult:
    """测试结果"""
    paper_id: str
    score: float
    total_score: float
    percentage: float                       # 得分百分比
    answers: Dict[str, str] = field(default_factory=dict)   # question_id -> answer
    correct_count: int = 0
    total_count: int = 0
    time_spent_minutes: int = 0
    weak_areas: List[str] = field(default_factory=list)     # 薄弱环节
    strong_areas: List[str] = field(default_factory=list)   # 优势环节


# ============================================================
# 能力评估
# ============================================================

@dataclass
class SkillAssessment:
    """单项技能评估"""
    skill_point_id: str
    skill_name: str
    current_level: SkillLevel = SkillLevel.BEGINNER
    previous_level: Optional[SkillLevel] = None
    score: float = 0.0                     # 0-100
    progress_percentage: float = 0.0       # 进步百分比
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    practice_recommendations: List[str] = field(default_factory=list)


@dataclass
class AssessmentReport:
    """能力评估报告"""
    user_name: str = "学员"
    position_name: str = ""
    assessment_date: str = ""
    period: str = ""                       # 评估周期，如"第一阶段 / 第1-4周"
    overall_score: float = 0.0
    overall_level: SkillLevel = SkillLevel.BEGINNER
    skill_assessments: List[SkillAssessment] = field(default_factory=list)
    overall_strengths: List[str] = field(default_factory=list)
    overall_weaknesses: List[str] = field(default_factory=list)
    growth_trend: str = ""                 # 成长趋势描述
    next_stage_plan: str = ""              # 下阶段学习计划
    conclusion: str = ""                   # 综合评语


# ============================================================
# 系统运行时状态
# ============================================================

@dataclass
class LearnerProfile:
    """学员画像"""
    name: str = "学员"
    position: str = ""                     # 目标岗位
    current_level: SkillLevel = SkillLevel.BEGINNER
    background: str = ""                   # 背景描述
    completed_modules: List[str] = field(default_factory=list)  # 已完成模块ID
    completed_tasks: List[str] = field(default_factory=list)    # 已完成任务ID
    test_results: List[TestResult] = field(default_factory=list)
    assessment_history: List[AssessmentReport] = field(default_factory=list)


@dataclass
class ResumeProfile:
    """简历分析结果"""
    name: str = ""
    education: str = ""                          # 学历信息
    experience_years: int = 0                    # 工作年限
    skills_found: List[str] = field(default_factory=list)  # 简历中发现的技能
    projects: List[Dict[str, str]] = field(default_factory=list)  # 项目经历
    work_experience: List[str] = field(default_factory=list)  # 工作经历摘要
    strengths_from_resume: List[str] = field(default_factory=list)  # 简历中的优势
    raw_text: str = ""                           # 简历原始文本


@dataclass
class SystemState:
    """系统运行时状态 - 在各Agent之间传递的上下文"""
    position: str                          # 目标岗位
    learner: LearnerProfile = field(default_factory=LearnerProfile)
    framework: Optional[CapabilityFramework] = None
    resume_profile: Optional[ResumeProfile] = None  # 简历分析结果
    learning_content: Optional[LearningContentOutput] = None
    training_plan: Optional[TrainingPlan] = None
    test_papers: List[TestPaper] = field(default_factory=list)
    assessment: Optional[AssessmentReport] = None
    current_phase: LearningPhase = LearningPhase.REQUIREMENT_ANALYSIS
    iteration: int = 1
    max_iterations: int = 3
    messages: List[str] = field(default_factory=list)

    def add_message(self, msg: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {msg}")


# ============================================================
# 能力画像 (硬性指标: 结构化输出)
# ============================================================

@dataclass
class FourDimensionScore:
    """四维分值"""
    knowledge: float = 0.0               # 知识维度 (0-100)
    skill: float = 0.0                   # 技能维度 (0-100)
    competency: float = 0.0              # 素养维度 (0-100)
    experience: float = 0.0              # 经验维度 (0-100)

    def to_dict(self) -> Dict[str, float]:
        return {
            "knowledge": self.knowledge,
            "skill": self.skill,
            "competency": self.competency,
            "experience": self.experience,
        }

    def radar_data(self) -> List[Dict]:
        """雷达图数据格式"""
        return [
            {"axis": "知识", "value": self.knowledge},
            {"axis": "技能", "value": self.skill},
            {"axis": "素养", "value": self.competency},
            {"axis": "经验", "value": self.experience},
        ]


@dataclass
class CapabilityProfile:
    """能力画像 - JSON/Excel输出"""
    # 基础信息
    student_id: str = ""
    name: str = ""
    major: str = ""                      # 专业
    grade: str = ""                      # 年级
    school: str = ""                     # 学校

    # 四维分值
    dimension_scores: FourDimensionScore = field(default_factory=FourDimensionScore)
    overall_score: float = 0.0           # 综合分

    # 技能详情
    skill_scores: Dict[str, float] = field(default_factory=dict)  # skill_point_id -> score
    skill_assessments: List[SkillAssessment] = field(default_factory=list)

    # TOP5匹配岗位
    top_matches: List["MatchResult"] = field(default_factory=list)

    # 画像描述
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_json_dict(self) -> Dict:
        """转JSON字典(用于Excel/JSON导出)"""
        return {
            "基础信息": {
                "学号": self.student_id,
                "姓名": self.name,
                "专业": self.major,
                "年级": self.grade,
                "学校": self.school,
            },
            "四维分值": self.dimension_scores.to_dict(),
            "综合评分": self.overall_score,
            "雷达图数据": self.dimension_scores.radar_data(),
            "优势": self.strengths,
            "待提升": self.weaknesses,
            "画像总结": self.summary,
            "TOP5匹配岗位": [
                {
                    "岗位": m.position_name,
                    "匹配度": m.match_score,
                    "排名": i + 1,
                }
                for i, m in enumerate(self.top_matches[:5])
            ],
        }


# ============================================================
# 岗位匹配 (硬性指标: 匹配结果)
# ============================================================

@dataclass
class GapItem:
    """差距明细项"""
    skill_name: str
    current_score: float                  # 当前得分
    required_score: float                 # 要求分值
    gap: float                            # 差距 (required - current)
    priority: str = "medium"              # high/medium/low
    suggestion: str = ""                  # 提升建议


@dataclass
class MatchResult:
    """匹配结果 - 可视化报表数据"""
    position_name: str
    position_description: str = ""
    match_score: float = 0.0              # 匹配度 0-100
    dimension_breakdown: Dict[str, float] = field(default_factory=dict)  # 各维度匹配度
    gaps: List[GapItem] = field(default_factory=list)  # 差距明细
    strengths: List[str] = field(default_factory=list)  # 优势
    recommendation: str = ""              # 推荐理由
    rank: int = 0                         # 排名

    def to_json_dict(self) -> Dict:
        return {
            "岗位": self.position_name,
            "匹配度": f"{self.match_score:.1f}%",
            "各维度匹配": self.dimension_breakdown,
            "优势": self.strengths,
            "差距明细": [
                {
                    "技能": g.skill_name,
                    "当前": g.current_score,
                    "要求": g.required_score,
                    "差距": g.gap,
                    "优先级": g.priority,
                    "建议": g.suggestion,
                }
                for g in self.gaps
            ],
            "推荐理由": self.recommendation,
        }


# ============================================================
# 路径规划 (硬性指标: PDF/Word输出)
# ============================================================

@dataclass
class WeeklyTask:
    """周任务"""
    week: int
    title: str
    description: str
    modules: List[str] = field(default_factory=list)  # 关联学习模块ID
    tasks: List[str] = field(default_factory=list)    # 关联训练任务ID
    resource_links: List[str] = field(default_factory=list)  # 资源链接
    standard: str = ""                     # 达标标准
    estimated_hours: float = 5.0


@dataclass
class StageGoal:
    """阶段目标"""
    stage: int
    name: str
    description: str
    target_skills: List[str] = field(default_factory=list)  # 目标技能点
    target_score: float = 60.0             # 目标分数
    weekly_tasks: List[WeeklyTask] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)  # 达标标准


@dataclass
class PathPlan:
    """路径规划 - PDF/Word输出"""
    title: str = ""
    student_name: str = ""
    target_position: str = ""
    total_weeks: int = 16
    stages: List[StageGoal] = field(default_factory=list)
    summary: str = ""
    created_at: str = ""

    def to_json_dict(self) -> Dict:
        return {
            "标题": self.title,
            "学员": self.student_name,
            "目标岗位": self.target_position,
            "总周数": self.total_weeks,
            "阶段概览": [
                {
                    "阶段": s.stage,
                    "名称": s.name,
                    "周次": f"第{(s.stage-1)*4+1}-{s.stage*4}周",
                    "目标技能": s.target_skills,
                    "达标标准": s.acceptance_criteria,
                }
                for s in self.stages
            ],
            "详细计划": [
                {
                    "阶段": s.stage,
                    "名称": s.name,
                    "周任务": [
                        {
                            "周": w.week,
                            "标题": w.title,
                            "资源": w.resource_links,
                            "达标标准": w.standard,
                            "预估小时": w.estimated_hours,
                        }
                        for w in s.weekly_tasks
                    ],
                }
                for s in self.stages
            ],
        }


# ============================================================
# 实测案例 (硬性指标: 数据可追溯)
# ============================================================

@dataclass
class StudentCase:
    """学生案例"""
    case_id: str
    name: str
    raw_data: Dict[str, Any]              # 原始数据（成绩单、项目经历等）
    profile: CapabilityProfile            # 画像报告
    growth_path: PathPlan                 # 成长路径
    match_results: List[MatchResult]      # 匹配结果
    summary: str = ""
    created_at: str = ""

    def to_json_dict(self) -> Dict:
        return {
            "案例ID": self.case_id,
            "姓名": self.name,
            "原始数据": self.raw_data,
            "画像报告": self.profile.to_json_dict(),
            "成长路径": self.growth_path.to_json_dict(),
            "匹配结果": [m.to_json_dict() for m in self.match_results],
        }


@dataclass
class EnterpriseCase:
    """企业案例"""
    case_id: str
    company_name: str
    position_model: CapabilityFramework   # 岗位模型
    match_list: List[MatchResult]         # 匹配清单
    feedback: str = ""                    # 用人反馈
    summary: str = ""
    created_at: str = ""

    def to_json_dict(self) -> Dict:
        return {
            "案例ID": self.case_id,
            "企业": self.company_name,
            "岗位模型": self.position_model.position_name,
            "匹配清单": [m.to_json_dict() for m in self.match_list],
            "用人反馈": self.feedback,
        }


# ============================================================
# （仅保留方向二所需数据模型）
# 方向三(课程诊断)和方向四(企业招聘)模型已移除
# ============================================================
