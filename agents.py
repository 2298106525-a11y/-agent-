"""
学练测一体化能力提升系统 - Agent模块

实现5个专业Agent：
1. RequirementAgent      - 岗位需求分析
2. LearningContentAgent  - 学习内容生成
3. TrainingTaskAgent     - 训练任务生成
4. TestGeneratorAgent    - 测试考核生成
5. AssessmentAgent       - 能力评估
"""

import json
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('gbk', 'gb2312', 'gb18030'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from openai import OpenAI

from config import config
from models import (
    CapabilityFramework, SkillPoint, SkillLevel,
    LearningContent, LearningModule, LearningContentOutput, LearningPath,
    TrainingPlan, TrainingTask, TrainingScenario, TrainingType,
    TestPaper, TestQuestion, QuestionType, TestResult,
    AssessmentReport, SkillAssessment,
    SystemState, LearnerProfile, ResumeProfile
)
from tools import json_parser
from promt import (
    REQUIREMENT_AGENT_PROMPT,
    LEARNING_CONTENT_AGENT_PROMPT,
    TRAINING_TASK_AGENT_PROMPT,
    TEST_GENERATOR_AGENT_PROMPT,
    ASSESSMENT_AGENT_PROMPT,
    RESUME_EVALUATOR_AGENT_PROMPT,
)


class BaseAgent:
    """Agent基类"""

    def __init__(self, name: str, system_prompt: str, model: str = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model or config.LLM_MODEL
        self.token_callback = None  # 可选回调: callback(token: str)
        self.client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=300.0,  # qwen-max 生成试卷需要2-3分钟
        )

    def chat(self, user_message: str, temperature: float = 0.7) -> str:
        """调用LLM"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=2048,
                extra_body={"enable_thinking": False},
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"❌ [{self.name}] LLM调用失败: {type(e).__name__}")
            return ""

    def chat_stream(self, user_message: str, temperature: float = 0.7) -> str:
        """流式调用LLM — 实时输出 + 回调 + 返回完整内容"""
        full = []
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=16384,
                stream=True,
                extra_body={"enable_thinking": False},
            )
            for chunk in stream:
                try:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full.append(delta.content)
                        print(delta.content, end="", flush=True)
                        if self.token_callback:
                            self.token_callback(delta.content)
                except (IndexError, AttributeError):
                    continue
            print()
            return "".join(full)
        except Exception as e:
            print(f"\n❌ [{self.name}] 流式调用失败: {type(e).__name__}")
            return "".join(full) if full else ""  # 至少有部分内容就返回

    def chat_with_context(self, messages: list, temperature: float = 0.7) -> str:
        """使用上下文消息列表调用LLM"""
        try:
            full_messages = [{"role": "system", "content": self.system_prompt}] + messages
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ [{self.name}] LLM调用失败: {e}")
            return ""


# ============================================================
# 1. 岗位需求分析Agent
# ============================================================

class RequirementAgent(BaseAgent):
    """岗位需求分析Agent - 分析岗位能力要求，构建能力框架"""

    def __init__(self):
        super().__init__(name="岗位分析", system_prompt=REQUIREMENT_AGENT_PROMPT)

    def analyze(self, position: str, level: str = "中级", context: str = "") -> CapabilityFramework:
        """
        分析岗位能力要求

        Args:
            position: 目标岗位名称
            level: 目标级别（初级/中级/高级）
            context: 额外上下文（可选）

        Returns:
            CapabilityFramework 能力框架
        """
        print(f"📋 [{self.name}] 正在分析岗位能力要求: {position} ({level})")

        user_msg = f"""请分析以下岗位的能力要求，构建完整的能力框架：

**目标岗位:** {position}
**目标级别:** {level}"""
        if context:
            user_msg += f"\n**补充说明:** {context}"

        user_msg += """

要求：
1. 技能点数量控制在6-10个（精简高效）
2. 只覆盖该岗位最核心的技术栈
3. 合理划分技能分类（2-4类）
4. 等级要求贴合岗位实际
5. 每个技能点描述简洁（一句话即可）"""

        print("  ⏳ 流式分析中: ", end="", flush=True)
        response = self.chat_stream(user_msg, temperature=0.5)

        data = json_parser.extract_json(response)
        if data:
            framework = CapabilityFramework(
                position_name=data.get("position_name", position),
                position_description=data.get("position_description", ""),
                summary=data.get("summary", ""),
                skill_categories=data.get("skill_categories", []),
                skill_points=[
                    SkillPoint(
                        id=sp.get("id", f"SKILL_{i:03d}"),
                        name=sp.get("name", ""),
                        description=sp.get("description", ""),
                        category=sp.get("category", "通用"),
                        required_level=SkillLevel(sp.get("required_level", "junior")),
                        prerequisites=sp.get("prerequisites", []),
                        keywords=sp.get("keywords", []),
                    )
                    for i, sp in enumerate(data.get("skill_points", []))
                ],
                required_qualities=data.get("required_qualities", []),
                career_path=data.get("career_path", []),
            )
            print(f"✅ [{self.name}] 分析完成！共 {len(framework.skill_points)} 个技能点，{len(framework.skill_categories)} 个分类")
            return framework

        # 解析失败，返回默认框架
        print(f"⚠️ [{self.name}] JSON解析失败，使用默认框架")
        return CapabilityFramework(
            position_name=position,
            position_description=f"{position}岗位能力要求",
            summary=f"针对{position}岗位的基础能力框架",
            skill_categories=["基础技能", "核心技能", "进阶技能"],
            skill_points=[
                SkillPoint(id="SKILL_001", name=f"{position}基础", description=f"{position}基础知识",
                           category="基础技能", required_level=SkillLevel.BEGINNER),
                SkillPoint(id="SKILL_002", name=f"{position}核心", description=f"{position}核心技能",
                           category="核心技能", required_level=SkillLevel.INTERMEDIATE),
                SkillPoint(id="SKILL_003", name=f"{position}进阶", description=f"{position}进阶知识",
                           category="进阶技能", required_level=SkillLevel.ADVANCED),
            ],
        )


# ============================================================
# 2. 学习内容生成Agent
# ============================================================

class LearningContentAgent(BaseAgent):
    """学习内容生成Agent - 根据能力框架生成学习内容"""

    def __init__(self):
        super().__init__(name="学习内容", system_prompt=LEARNING_CONTENT_AGENT_PROMPT)

    def generate(self, framework: CapabilityFramework, focus_skill: Optional[str] = None, extra_context: str = "") -> LearningContentOutput:
        """
        根据能力框架生成学习内容

        Args:
            framework: 能力框架
            focus_skill: 可选，只生成特定技能点的内容
            extra_context: 额外上下文（用户需求、已完成内容等）

        Returns:
            LearningContentOutput 学习内容输出
        """
        print(f"📚 [{self.name}] 正在批量生成 {len(framework.skill_points)} 个技能点的学习内容...")

        skill_points = framework.skill_points
        if focus_skill:
            skill_points = [sp for sp in skill_points if sp.id == focus_skill or sp.name == focus_skill]

        # 合并所有技能点到一次 LLM 调用
        skills_text = "\n".join([
            f"[{sp.id}] {sp.name}({sp.required_level.value}): {sp.description}"
            for sp in skill_points
        ])
        user_msg = f"""为 {framework.position_name} 岗位的 {len(skill_points)} 个技能点生成学习内容：

{skills_text}

每个技能点生成1-2个学习模块(含title/content)，输出JSON: {{"items": [{{"skill_point_id":"SKILL_001", "modules":[{{"title":"","content":""}}]}}]}}"""
        if extra_context:
            user_msg += f"\n\n【用户需求】{extra_context}"

        print("  ⏳ 流式生成中: ", end="", flush=True)
        response = self.chat_stream(user_msg, temperature=0.6)
        data = json_parser.extract_json(response)

        contents = []
        total_modules = 0
        total_minutes = 0

        if data:
            items = data.get("items", [data] if isinstance(data, dict) else [])
            if isinstance(items, dict):
                items = [items]

            for item in items:
                sid = item.get("skill_point_id", "")
                sp = next((s for s in skill_points if s.id == sid), None)
                if not sp and skill_points:
                    sp = skill_points[len(contents) % len(skill_points)]

                modules = []
                for md in item.get("modules", item.get("learning_modules", [])):
                    modules.append(LearningModule(
                        id=f"MOD_{total_modules + 1:03d}",
                        title=md.get("title", f"{sp.name}模块"),
                        description=md.get("description", ""),
                        skill_point_id=sp.id if sp else "",
                        difficulty=SkillLevel.BEGINNER,
                        estimated_minutes=md.get("estimated_minutes", 30),
                        order=len(modules) + 1,
                        content=md.get("content", ""),
                    ))
                    total_modules += 1
                    total_minutes += modules[-1].estimated_minutes

                if sp:
                    contents.append(LearningContent(
                        skill_point=sp, learning_modules=modules,
                        key_concepts=item.get("key_concepts", []),
                        summary=item.get("summary", sp.description),
                    ))

        # 补全未覆盖的技能点（降级）
        covered = {c.skill_point.id for c in contents}
        for sp in skill_points:
            if sp.id not in covered:
                m = LearningModule(id=f"MOD_{total_modules + 1:03d}",
                                   title=f"{sp.name}基础", description=sp.description,
                                   skill_point_id=sp.id, content=f"# {sp.name}\n{sp.description}")
                contents.append(LearningContent(skill_point=sp, learning_modules=[m],
                                                key_concepts=[sp.name], summary=sp.description))
                total_modules += 1
                total_minutes += 30

        # 构建学习路径
        learning_paths = self._build_learning_paths(framework, contents)

        output = LearningContentOutput(
            framework=framework,
            learning_paths=learning_paths,
            contents=contents,
            total_modules=total_modules,
            total_minutes=total_minutes,
        )

        print(f"✅ [{self.name}] 内容生成完成！共 {total_modules} 个模块，预估学习时间 {total_minutes} 分钟")
        return output

    def _build_learning_paths(self, framework: CapabilityFramework, contents: List[LearningContent]) -> List[LearningPath]:
        """构建学习路径（按技能分类组织）"""
        paths = []
        for category in framework.skill_categories:
            related_modules = []
            for content in contents:
                if content.skill_point.category == category:
                    related_modules.extend(content.learning_modules)

            if related_modules:
                # 按学习顺序排序
                related_modules.sort(key=lambda m: (m.order, m.difficulty.value))
                path = LearningPath(
                    title=f"{category}学习路径",
                    description=f"涵盖{category}相关技能的系统学习路径",
                    modules=related_modules,
                )
                paths.append(path)

        return paths


# ============================================================
# 3. 训练任务生成Agent
# ============================================================

class TrainingTaskAgent(BaseAgent):
    """训练任务生成Agent - 创建实践训练任务"""

    def __init__(self):
        super().__init__(name="训练任务", system_prompt=TRAINING_TASK_AGENT_PROMPT)

    def generate(self, framework: CapabilityFramework, learning_output: LearningContentOutput,
                 focus_skill: Optional[str] = None, extra_context: str = "") -> TrainingPlan:
        """
        生成训练计划

        Args:
            framework: 能力框架
            learning_output: 学习内容
            focus_skill: 可选，只生成特定技能点的训练
            extra_context: 额外上下文（用户需求、薄弱环节等）

        Returns:
            TrainingPlan 训练计划
        """
        print(f"🏋️ [{self.name}] 正在生成训练任务...")

        # 构建技能点列表
        skill_points_text = []
        for sp in framework.skill_points:
            if focus_skill and sp.id != focus_skill and sp.name != focus_skill:
                continue
            # 查找对应的学习内容
            content_summary = ""
            for lc in learning_output.contents:
                if lc.skill_point.id == sp.id:
                    content_summary = lc.summary[:200]
                    break
            skill_points_text.append(f"- {sp.name} ({sp.required_level.value}): {sp.description}\n  学习内容: {content_summary}")

        user_msg = f"""请根据以下信息生成训练任务：

**目标岗位：** {framework.position_name}
**岗位描述：** {framework.position_description}

**技能点列表：**
{chr(10).join(skill_points_text)}

**要求：**
1. 每个关键技能点至少1个训练任务
2. 包含至少1个综合场景模拟
3. 任务类型多样化（练习、案例分析、模拟、项目）
4. 难度递进合理
5. 提供清晰的评价标准"""
        if extra_context:
            user_msg += f"\n\n【用户需求】{extra_context}"

        data = None
        for attempt in range(3):
            print(f"  ⏳ 流式生成中(尝试{attempt+1}/3): ", end="", flush=True)
            response = self.chat_stream(user_msg, temperature=0.6 + attempt * 0.1)
            if not response:
                print(f"\n⚠️ [训练任务] LLM无响应")
                continue
            data = json_parser.extract_json(response)
            if not data:
                print(f"\n⚠️ [训练任务] JSON解析失败, 响应前200字: {response[:200]}")
                try:
                    import re
                    brace_match = re.search(r'\{[\s\S]*\}', response)
                    if brace_match:
                        import json as _json
                        raw = brace_match.group(0)
                        raw = re.sub(r',\s*([\]}])', r'\1', raw)
                        data = _json.loads(raw)
                        print(f"  ✅ 备用解析成功")
                except Exception as e2:
                    print(f"  ⚠️ 备用解析也失败: {e2}")
                    continue
            if data and data.get("tasks"):
                break  # 有任务数据，成功
            elif data:
                print(f"  ⚠️ tasks为空，重试...")
                data = None
                continue
        if not data or not data.get("tasks"):
            print(f"  ⚠️ 3次尝试均失败，使用降级方案自动生成任务")
            data = self._generate_fallback_tasks(framework)

        plan = TrainingPlan(
            title=data.get("title", f"{framework.position_name}训练计划"),
            description=data.get("description", ""),
        )

        # 解析训练任务
        tasks_data = data.get("tasks", [])
        for td in tasks_data:
            task = TrainingTask(
                id=td.get("id", f"TASK_{len(plan.tasks) + 1:03d}"),
                title=td.get("title", ""),
                description=td.get("description", ""),
                type=TrainingType(td.get("type", "exercise")),
                skill_point_id=td.get("skill_point_id", ""),
                difficulty=SkillLevel(td.get("difficulty", "beginner")),
                requirements=td.get("requirements", []),
                hints=td.get("hints", []),
                reference_solution=td.get("reference_solution", ""),
                evaluation_criteria=td.get("evaluation_criteria", []),
                estimated_minutes=td.get("estimated_minutes", 30),
            )
            plan.tasks.append(task)

        # 解析训练场景
        scenarios_data = data.get("scenarios", [])
        for sd in scenarios_data:
            scenario = TrainingScenario(
                id=sd.get("id", f"SCENE_{len(plan.scenarios) + 1:03d}"),
                title=sd.get("title", ""),
                description=sd.get("description", ""),
                context=sd.get("context", ""),
                difficulty=SkillLevel(sd.get("difficulty", "intermediate")),
                expected_outcome=sd.get("expected_outcome", ""),
                tasks=[],  # task id 字符串，不关联 TrainingTask 对象
            )
            scenario.tasks = sd.get("tasks", [])
            plan.scenarios.append(scenario)

        plan.total_tasks = len(plan.tasks)
        plan.total_estimated_hours = sum(t.estimated_minutes for t in plan.tasks) / 60.0

        print(f"✅ [{self.name}] 训练计划生成完成！共 {plan.total_tasks} 个任务，{len(plan.scenarios)} 个场景")
        return plan

    def _generate_fallback_tasks(self, framework: CapabilityFramework) -> dict:
        """LLM 失败时根据框架自动生成基础训练任务"""
        tasks = []
        for i, sp in enumerate(framework.skill_points):
            tasks.append({
                "id": f"TASK_{i+1:03d}",
                "title": f"{sp.name}实战练习",
                "description": f"针对{sp.name}({sp.required_level.value})的专项训练任务。{sp.description}",
                "type": "exercise",
                "skill_point_id": sp.id,
                "difficulty": sp.required_level.value,
                "requirements": [f"掌握{sp.name}的核心概念", f"完成{sp.name}相关的实践练习"],
                "hints": [f"参考{sp.name}的学习材料"],
                "reference_solution": f"根据{sp.name}的学习内容完成练习",
                "evaluation_criteria": [f"正确运用{sp.name}的知识点", "代码规范，逻辑清晰"],
                "estimated_minutes": 30,
            })
        return {
            "title": f"{framework.position_name}训练计划",
            "description": f"针对{framework.position_name}岗位的自动化训练计划",
            "tasks": tasks,
            "scenarios": [],
        }


# ============================================================
# 4. 测试考核生成Agent
# ============================================================

class TestGeneratorAgent(BaseAgent):
    """测试考核生成Agent - 生成测试题目和试卷"""

    def __init__(self):
        super().__init__(name="测试考核", system_prompt=TEST_GENERATOR_AGENT_PROMPT)

    def generate(self, framework: CapabilityFramework, learning_output: LearningContentOutput,
                 difficulty: str = "mixed", num_questions: int = 20, extra_context: str = "") -> TestPaper:
        """
        生成测试试卷

        Args:
            framework: 能力框架
            learning_output: 学习内容
            difficulty: 难度（beginner/junior/intermediate/advanced/mixed）
            num_questions: 题目数量
            extra_context: 额外上下文（用户需求、薄弱环节等）

        Returns:
            TestPaper 试卷
        """
        print(f"📝 [{self.name}] 正在生成测试试卷...")

        # 构建技能点描述
        skill_info = []
        for sp in framework.skill_points:
            content_summary = ""
            for lc in learning_output.contents:
                if lc.skill_point.id == sp.id:
                    key_concepts = ", ".join(lc.key_concepts[:5])
                    content_summary = f"核心概念: {key_concepts}"
                    break
            skill_info.append(f"- {sp.name} ({sp.required_level.value}): {sp.description}\n  {content_summary}")

        user_msg = f"""请根据以下能力框架和学习内容，生成一套测试试卷：

**目标岗位：** {framework.position_name}

**技能点信息：**
{chr(10).join(skill_info)}

**出题要求：**
- 难度等级：{difficulty}
- 题目数量：约{num_questions}题
- 题型多样化，包含选择题、判断题、简答题等
- 覆盖所有关键技能点
- 难度分布：基础40%，进阶40%，挑战20%

请确保题目质量高、区分度好、无歧义。"""
        if extra_context:
            user_msg += f"\n\n【用户需求】{extra_context}"

        data = None
        for attempt in range(3):
            print(f"  ⏳ 流式出题中(尝试{attempt+1}/3): ", end="", flush=True)
            response = self.chat_stream(user_msg, temperature=0.5 + attempt * 0.1)
            if not response:
                continue
            data = json_parser.extract_json(response)
            if data and data.get("questions"):
                break
            elif data:
                print(f"  ⚠️ questions为空，重试...")
                data = None
            else:
                print(f"  ⚠️ JSON解析失败，重试...")
        if not data or not data.get("questions"):
            print(f"\n  ⚠️ 3次尝试均失败，使用降级方案")
            data = self._generate_fallback_questions(framework)

        valid_levels = {e.value for e in SkillLevel}
        def safe_lv(val, default="beginner"):
            if not val or val not in valid_levels:
                return SkillLevel(default)
            return SkillLevel(val)

        questions = []
        for qd in data.get("questions", []):
            question = TestQuestion(
                id=qd.get("id", f"Q_{len(questions) + 1:03d}"),
                question_type=QuestionType(qd.get("question_type", "single_choice")),
                question_text=qd.get("question_text", ""),
                skill_point_id=qd.get("skill_point_id", ""),
                difficulty=safe_lv(qd.get("difficulty"), "beginner"),
                options=qd.get("options", []),
                correct_answer=qd.get("correct_answer", ""),
                explanation=qd.get("explanation", ""),
                score=qd.get("score", 5),
                tags=qd.get("tags", []),
            )
            questions.append(question)

        paper = TestPaper(
            id=f"PAPER_{framework.position_name[:3].upper()}_001",
            title=data.get("title", f"{framework.position_name}能力测试"),
            description=data.get("description", ""),
            questions=questions,
            time_limit_minutes=data.get("time_limit_minutes", 60),
            passing_score=data.get("passing_score", 60),
            skill_points_covered=data.get("skill_points_covered", [sp.id for sp in framework.skill_points]),
        )

        print(f"✅ [{self.name}] 试卷生成完成！共 {len(paper.questions)} 道题，时限 {paper.time_limit_minutes} 分钟")
        return paper

    def _generate_fallback_questions(self, framework: CapabilityFramework) -> dict:
        """LLM 失败时根据框架自动生成基础题目"""
        questions = []
        for i, sp in enumerate(framework.skill_points):
            # 每个技能点生成1道单选题
            questions.append({
                "id": f"Q_{i*2+1:03d}",
                "question_type": "single_choice",
                "question_text": f"关于{sp.name}，以下哪项描述是正确的？",
                "skill_point_id": sp.id,
                "difficulty": "beginner",
                "options": [
                    f"A. {sp.name}是{sp.description}",
                    f"B. {sp.name}不需要掌握",
                    f"C. {sp.name}仅用于高级开发",
                    f"D. {sp.name}与本岗位无关"
                ],
                "correct_answer": "A",
                "explanation": f"{sp.name}是{sp.required_level.value}级别的核心技能点。",
                "score": 5,
                "tags": [sp.category],
            })
            # 每个技能点生成1道判断题
            questions.append({
                "id": f"Q_{i*2+2:03d}",
                "question_type": "true_false",
                "question_text": f"{sp.name}是{framework.position_name}岗位的必备技能。",
                "skill_point_id": sp.id,
                "difficulty": "beginner",
                "options": ["A. 正确", "B. 错误"],
                "correct_answer": "A",
                "explanation": f"根据岗位分析，{sp.name}属于{sp.category}分类的核心技能。",
                "score": 5,
                "tags": [sp.category],
            })
        return {
            "title": f"{framework.position_name}能力测试",
            "description": f"针对{framework.position_name}岗位的基础能力测试",
            "questions": questions,
            "time_limit_minutes": 60,
            "passing_score": 60,
        }


# ============================================================
# 5. 能力评估Agent
# ============================================================

class AssessmentAgent(BaseAgent):
    """能力评估Agent - 评估学员能力并生成评估报告"""

    def __init__(self):
        super().__init__(name="能力评估", system_prompt=ASSESSMENT_AGENT_PROMPT)

    def evaluate(self, state: SystemState) -> AssessmentReport:
        """
        综合评估学员能力

        Args:
            state: 系统状态（包含学员画像、学习进度、测试结果等）

        Returns:
            AssessmentReport 评估报告
        """
        print(f"📊 [{self.name}] 正在生成能力评估报告...")

        learner = state.learner
        framework = state.framework

        # 构建评估上下文
        completion_info = f"已完成模块: {len(learner.completed_modules)}个"
        if state.learning_content:
            completion_info += f" / 总计: {state.learning_content.total_modules}个"

        task_info = f"已完成任务: {len(learner.completed_tasks)}个"
        if state.training_plan:
            task_info += f" / 总计: {state.training_plan.total_tasks}个"

        test_info = "测试记录: "
        if learner.test_results:
            avg_score = sum(r.percentage for r in learner.test_results) / len(learner.test_results)
            test_info += f"共{len(learner.test_results)}次，平均得分{avg_score:.1f}%"
        else:
            test_info += "暂无测试记录"

        framework_info = ""
        if framework:
            sp_list = "\n".join([f"  - {sp.name} (目标: {sp.required_level.value})" for sp in framework.skill_points])
            framework_info = f"**技能框架：**\n{sp_list}"

        # 简历评估信息
        resume_info = ""
        if state.resume_profile:
            rp = state.resume_profile
            resume_info = f"""
**简历分析结果：**
- 学历：{rp.education or '未提供'}
- 工作年限：{rp.experience_years}年
- 发现的技能：{', '.join(rp.skills_found[:10]) if rp.skills_found else '无'}
- 项目经历：{len(rp.projects)}个
- 简历优势：{', '.join(rp.strengths_from_resume[:5]) if rp.strengths_from_resume else '无'}
"""
            if rp.initial_assessment and rp.initial_assessment.skill_assessments:
                resume_info += "\n**简历初始评分：**\n"
                for sa in rp.initial_assessment.skill_assessments:
                    resume_info += f"  - {sa.skill_name}: {sa.score}分\n"

        user_msg = f"""请根据以下信息进行综合能力评估：

**学员信息：**
- 姓名：{learner.name}
- 目标岗位：{learner.position or state.position}
- 当前等级：{learner.current_level.value}
- 背景：{learner.background or '未提供'}

**学习进度：**
- {completion_info}
- {task_info}
- {test_info}

**{framework_info}**
{resume_info}
请对每个技能点进行评估，并生成综合评估报告。
{"注意：该学员提供了简历，请结合简历分析结果给出更精准的评估。" if state.resume_profile else ""}"""

        print("  ⏳ 评估中: ", end="", flush=True)
        response = self.chat_stream(user_msg, temperature=0.5)
        if not response:
            response = self.chat(user_msg, temperature=0.5)
        data = json_parser.extract_json(response) if response else None

        if data:
            valid_levels = {e.value for e in SkillLevel}
            def safe_level(val, default="beginner"):
                if not val or val not in valid_levels:
                    return SkillLevel(default)
                return SkillLevel(val)

            assessments = []
            for ad in data.get("skill_assessments", []):
                assessment = SkillAssessment(
                    skill_point_id=ad.get("skill_point_id", ""),
                    skill_name=ad.get("skill_name", ""),
                    current_level=safe_level(ad.get("current_level"), "beginner"),
                    previous_level=safe_level(ad.get("previous_level")) if ad.get("previous_level") else None,
                    score=ad.get("score", 0),
                    progress_percentage=ad.get("progress_percentage", 0),
                    strengths=ad.get("strengths", []),
                    weaknesses=ad.get("weaknesses", []),
                    practice_recommendations=ad.get("practice_recommendations", []),
                )
                assessments.append(assessment)

            import datetime
            report = AssessmentReport(
                user_name=data.get("user_name", learner.name),
                position_name=data.get("position_name", state.position),
                assessment_date=data.get("assessment_date", datetime.datetime.now().strftime("%Y-%m-%d")),
                period=data.get("period", "当前阶段"),
                overall_score=data.get("overall_score", 0),
                overall_level=safe_level(data.get("overall_level"), "beginner"),
                skill_assessments=assessments,
                overall_strengths=data.get("overall_strengths", []),
                overall_weaknesses=data.get("overall_weaknesses", []),
                growth_trend=data.get("growth_trend", ""),
                next_stage_plan=data.get("next_stage_plan", ""),
                conclusion=data.get("conclusion", ""),
            )
        else:
            # 降级方案
            report = AssessmentReport(
                user_name=learner.name,
                position_name=state.position,
                assessment_date="评估日期",
                period="当前阶段",
                overall_score=50,
                overall_level=learner.current_level,
                conclusion="评估生成失败，请检查LLM连接后重试。",
            )

        print(f"✅ [{self.name}] 评估完成！综合评分: {report.overall_score}/100，等级: {report.overall_level.value}")
        return report


# ============================================================
# 6. 简历评估Agent
# ============================================================

class ResumeEvaluatorAgent(BaseAgent):
    """简历评估Agent - 分析简历内容，生成初始能力画像"""

    def __init__(self):
        super().__init__(name="简历评估", system_prompt=RESUME_EVALUATOR_AGENT_PROMPT)

    def evaluate(self, resume_text: str, framework: CapabilityFramework,
                 position: str, name: str) -> ResumeProfile:
        """
        分析简历内容，生成初始能力画像

        Args:
            resume_text: 简历的纯文本内容
            framework: 岗位能力框架（技能点列表）
            position: 目标岗位
            name: 求职者姓名

        Returns:
            ResumeProfile 简历分析结果
        """
        print(f"📋 [{self.name}] 正在分析简历: {name} -> {position}")

        # 构建技能点列表
        skills_text = "\n".join([
            f"- {sp.name} ({sp.required_level.value}): {sp.description}"
            for sp in framework.skill_points
        ])

        user_msg = f"""请分析以下简历内容，评估求职者对目标岗位的技能掌握程度。

**求职者姓名:** {name}
**目标岗位:** {position}

**岗位要求的技能点:**
{skills_text}

**简历内容:**
{resume_text[:4000]}

请根据简历中的实际经历（项目、工作经验、技能描述等），对每个技能点给出初始评分（0-100），并提取简历中的关键信息。"""

        print("  ⏳ 流式分析中: ", end="", flush=True)
        response = self.chat_stream(user_msg, temperature=0.5)
        if not response:
            response = self.chat(user_msg, temperature=0.5)
        data = json_parser.extract_json(response) if response else None

        valid_levels = {e.value for e in SkillLevel}
        def safe_level(val, default="beginner"):
            if not val or val not in valid_levels:
                return SkillLevel(default)
            return SkillLevel(val)

        if data:
            profile = ResumeProfile(
                name=name,
                education=data.get("education", ""),
                experience_years=data.get("experience_years", 0),
                skills_found=data.get("skills_found", []),
                projects=data.get("projects", []),
                work_experience=data.get("work_experience", []),
                strengths_from_resume=data.get("strengths_from_resume", []),
                raw_text=resume_text[:2000],
            )

            # 构建初始评估报告
            skill_assessments = []
            for sa_data in data.get("skill_assessments", []):
                skill_assessments.append(SkillAssessment(
                    skill_point_id=sa_data.get("skill_point_id", ""),
                    skill_name=sa_data.get("skill_name", ""),
                    current_level=safe_level(sa_data.get("current_level"), "beginner"),
                    score=sa_data.get("score", 0),
                    progress_percentage=0,
                    strengths=[sa_data.get("evidence", "")],
                    weaknesses=[],
                    practice_recommendations=[],
                ))

            profile.initial_assessment = AssessmentReport(
                user_name=name,
                position_name=position,
                assessment_date=datetime.now().strftime("%Y-%m-%d"),
                period="简历评估",
                overall_score=data.get("overall_score", 50),
                overall_level=safe_level(data.get("overall_level"), "beginner"),
                skill_assessments=skill_assessments,
                overall_strengths=data.get("strengths_from_resume", []),
                overall_weaknesses=[],
                growth_trend="基于简历的初始评估",
                next_stage_plan="根据岗位要求制定学习计划",
                conclusion=data.get("summary", f"基于{name}的简历分析，已完成初始能力评估。"),
            )

            print(f"✅ [{self.name}] 简历分析完成！发现 {len(profile.skills_found)} 项技能，综合评分: {profile.initial_assessment.overall_score}/100")
            return profile

        # 降级方案
        print(f"⚠️ [{self.name}] 简历分析失败，使用默认评估")
        return ResumeProfile(
            name=name,
            raw_text=resume_text[:2000],
            initial_assessment=AssessmentReport(
                user_name=name,
                position_name=position,
                assessment_date=datetime.now().strftime("%Y-%m-%d"),
                period="简历评估",
                overall_score=50,
                overall_level=SkillLevel.BEGINNER,
                conclusion="简历分析失败，请检查LLM连接后重试。",
            ),
        )


# ============================================================
# 7. 伴学助手 Agent（带记忆系统）
# ============================================================

class TutorAgent(BaseAgent):
    """伴学助手Agent - 带三层记忆系统的个性化辅导"""

    def __init__(self):
        from promt import TUTOR_AGENT_PROMPT, SUMMARY_PROMPT, MEMORY_EXTRACT_PROMPT
        super().__init__(name="伴学助手", system_prompt=TUTOR_AGENT_PROMPT)
        self.summary_prompt = SUMMARY_PROMPT
        self.memory_prompt = MEMORY_EXTRACT_PROMPT

    def build_messages(self, name: str, position: str, context: str,
                       summary: str, memory: dict, recent_history: list,
                       user_message: str) -> list:
        """拼接包含所有记忆层的 messages 列表"""
        # 构建记忆上下文
        memory_parts = []
        if summary:
            memory_parts.append(f"【对话摘要】\n{summary}")

        mem_items = []
        if memory.get("preferences"):
            prefs = "; ".join(f"{k}:{v}" for k, v in memory["preferences"].items() if v)
            if prefs:
                mem_items.append(f"偏好：{prefs}")
        if memory.get("weak_points"):
            mem_items.append(f"薄弱点：{', '.join(memory['weak_points'])}")
        if memory.get("topics"):
            mem_items.append(f"常问话题：{', '.join(memory['topics'][-5:])}")
        if mem_items:
            memory_parts.append("【关键记忆】\n" + "\n".join(mem_items))

        memory_context = "\n\n".join(memory_parts)

        # 构建 system prompt
        system = self.system_prompt.format(name=name)
        if memory_context:
            system += f"\n\n{memory_context}"

        # 拼接 messages
        messages = [{"role": "system", "content": system}]
        for h in recent_history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": f"学生档案：{context}\n\n问题：{user_message}"})
        return messages

    def compress_summary(self, old_summary: str, recent_messages: list) -> str:
        """用 LLM 将对话压缩为摘要"""
        msg_text = "\n".join(
            f"{'学生' if m['role'] == 'user' else '助手'}：{m['content'][:200]}"
            for m in recent_messages[-20:]
        )
        prompt = self.summary_prompt.format(
            old_summary=old_summary or "（无历史摘要）",
            messages=msg_text
        )
        response = self.chat(prompt, temperature=0.3)
        return response.strip() if response else old_summary

    def extract_memory(self, messages: list, current_memory: dict) -> dict:
        """从对话中提取关键信息更新结构化记忆"""
        msg_text = "\n".join(
            f"{'学生' if m['role'] == 'user' else '助手'}：{m['content'][:300]}"
            for m in messages[-10:]
        )
        prompt = self.memory_prompt.format(
            preferences=json.dumps(current_memory.get("preferences", {}), ensure_ascii=False),
            weak_points=json.dumps(current_memory.get("weak_points", []), ensure_ascii=False),
            topics=json.dumps(current_memory.get("topics", []), ensure_ascii=False),
            messages=msg_text
        )
        response = self.chat(prompt, temperature=0.2)
        if not response:
            return current_memory

        # 提取 JSON
        data = json_parser.extract_json(response)
        if data:
            # 合并：旧 + 新
            merged = {
                "preferences": {**current_memory.get("preferences", {}), **data.get("preferences", {})},
                "weak_points": list(set(current_memory.get("weak_points", []) + data.get("weak_points", [])))[:10],
                "topics": list(dict.fromkeys(current_memory.get("topics", []) + data.get("topics", [])))[-10:],
            }
            return merged
        return current_memory
