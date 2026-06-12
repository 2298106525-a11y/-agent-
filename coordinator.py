"""
学练测一体化能力提升系统 - 协调器模块（方向二专用）

4阶段核心流程：
1. 岗位需求分析 → 能力框架
2. 学习内容生成 → 模块化教材
3. 训练任务生成 → 实战训练
4. 测试考核生成 → 试卷 + 自动评分
5. 能力评估 → 评估报告
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List

if sys.stdout.encoding and sys.stdout.encoding.lower() in ('gbk', 'gb2312', 'gb18030'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config import config
from models import (
    SystemState, LearningPhase, LearnerProfile,
    CapabilityFramework, SkillLevel,
)
from agents import (
    RequirementAgent, LearningContentAgent,
    TrainingTaskAgent, TestGeneratorAgent, AssessmentAgent,
    ResumeEvaluatorAgent,
)
class SkillTrainerCoordinator:
    """方向二: 学练测一体化 — 4阶段流程"""

    def __init__(self, on_event=None):
        """
        Args:
            on_event: 可选回调函数 callback(event_type, data)
                      event_type: "progress" | "token" | "done" | "error"
        """
        print("🔄 初始化...")
        self.on_event = on_event
        self.requirement_agent = RequirementAgent()
        self.resume_agent = ResumeEvaluatorAgent()
        self.learning_agent = LearningContentAgent()
        self.training_agent = TrainingTaskAgent()
        self.test_agent = TestGeneratorAgent()
        self.assessment_agent = AssessmentAgent()
        # 给所有 agent 注册 token 回调
        if on_event:
            for agent in [self.requirement_agent, self.resume_agent, self.learning_agent,
                          self.training_agent, self.test_agent, self.assessment_agent]:
                agent.token_callback = lambda t, a=agent: on_event("token", {"agent": a.name, "text": t})
        self.output_dir = Path(config.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print("✅ 就绪: 岗位分析 → 学习内容 → 训练任务 → 测试考核 → 能力评估")
        print()

    def _checkpoint_path(self, name: str) -> Path:
        return self.output_dir / f"checkpoint_{name}.json"

    def _save_checkpoint(self, name: str, position: str, done: int):
        self._checkpoint_path(name).write_text(
            json.dumps({"name": name, "position": position, "done": done,
                        "time": datetime.now().isoformat()}, ensure_ascii=False),
            encoding="utf-8")

    def run_full(self, position: str, learner_name: str = "学员",
                 level: str = "初级", raw_data: dict = None, resume_text: str = None) -> SystemState:
        """完整学练测评流程"""
        state = SystemState(
            position=position,
            learner=LearnerProfile(name=learner_name, position=position,
                                   current_level=SkillLevel.BEGINNER),
        )

        # 根据是否有简历决定阶段数
        has_resume = bool(resume_text and resume_text.strip())
        total_stages = 6 if has_resume else 5

        if has_resume:
            phases = [
                ("📋 岗位需求分析", "01_岗位分析.md"),
                ("📄 简历评估", "01_5_简历评估.md"),
                ("📚 学习内容生成", "02_学习内容.md"),
                ("🏋️ 训练任务生成", "03_训练任务.md"),
                ("📝 测试考核生成", "04_测试试卷.md"),
                ("📊 能力评估", "05_评估报告.md"),
            ]
        else:
            phases = [
                ("📋 岗位需求分析", "01_岗位分析.md"),
                ("📚 学习内容生成", "02_学习内容.md"),
                ("🏋️ 训练任务生成", "03_训练任务.md"),
                ("📝 测试考核生成", "04_测试试卷.md"),
                ("📊 能力评估", "05_评估报告.md"),
            ]

        print(f"{'='*50}")
        print(f"学练测评: {position} | 学员: {learner_name}")
        if has_resume:
            print(f"简历分析: 已启用")
        print(f"{'='*50}\n")

        # 记录各阶段在 state 中的实际索引（用于简历评估的索引偏移）
        phase_idx = 0
        for label, filename in phases:
            self._phase(label)
            if self.on_event:
                self.on_event("progress", {"stage": phase_idx, "total": total_stages, "label": label})

            if phase_idx == 0:  # 岗位分析 — 关键阶段，失败则中止
                state.framework = self.requirement_agent.analyze(position, level)
                self._summary_framework(state.framework)
                self._save_output(f"01_岗位分析_{learner_name}",
                                  self._format_framework_md(state.framework))

            elif has_resume and phase_idx == 1:  # 简历评估（仅当有简历时）
                try:
                    state.resume_profile = self.resume_agent.evaluate(
                        resume_text, state.framework, position, learner_name)
                    # 将简历评估的初始评估合并到 state.assessment
                    if state.resume_profile.initial_assessment:
                        state.assessment = state.resume_profile.initial_assessment
                    print(f"  发现技能: {len(state.resume_profile.skills_found)}项")
                    self._save_output(f"01_5_简历评估_{learner_name}",
                                      self._format_resume_md(state.resume_profile))
                except Exception as e:
                    print(f"  ⚠️ {label}失败: {e}, 跳过")

            elif (has_resume and phase_idx == 2) or (not has_resume and phase_idx == 1):  # 学习内容
                try:
                    state.learning_content = self.learning_agent.generate(state.framework)
                    print(f"  {state.learning_content.total_modules}个模块, {state.learning_content.total_minutes}分钟")
                    self._save_output(f"02_学习内容_{learner_name}",
                                      self._format_learning_md(state.learning_content))
                except Exception as e:
                    print(f"  ⚠️ {label}失败: {e}, 跳过")

            elif (has_resume and phase_idx == 3) or (not has_resume and phase_idx == 2):  # 训练任务
                try:
                    state.training_plan = self.training_agent.generate(state.framework, state.learning_content)
                    print(f"  {state.training_plan.total_tasks}个任务")
                    self._save_output(f"03_训练任务_{learner_name}",
                                      self._format_training_md(state.training_plan))
                except Exception as e:
                    print(f"  ⚠️ {label}失败: {e}, 跳过")

            elif (has_resume and phase_idx == 4) or (not has_resume and phase_idx == 3):  # 测试考核
                try:
                    paper = self.test_agent.generate(state.framework, state.learning_content, num_questions=10)
                    state.test_papers.append(paper)
                    print(f"  {len(paper.questions)}题")
                    self._save_output(f"04_测试试卷_{learner_name}",
                                      self._format_test_md(paper))
                except Exception as e:
                    print(f"  ⚠️ {label}失败: {e}, 跳过")

            elif (has_resume and phase_idx == 5) or (not has_resume and phase_idx == 4):  # 能力评估
                try:
                    if raw_data:
                        state.learner.background = json.dumps(raw_data, ensure_ascii=False)
                    elif not state.learner.background:
                        state.learner.background = "学生基本信息未提供"
                    state.assessment = self.assessment_agent.evaluate(state)
                    print(f"  综合: {state.assessment.overall_score}/100")
                    self._save_output(f"05_评估报告_{learner_name}",
                                      self._format_assessment_md(state.assessment))
                except Exception as e:
                    print(f"  ⚠️ {label}失败: {e}, 跳过")

            self._save_checkpoint(learner_name, position, phase_idx)
            print(f"  💾 阶段{phase_idx+1}/{total_stages}完成，断点已保存")
            phase_idx += 1

        state.current_phase = LearningPhase.COMPLETED

        # 保存完整 JSON 数据供前端读取
        try:
            result_data = self._build_result_json(state)
            result_path = self.output_dir / f"result_{learner_name}.json"
            result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  💾 result_{learner_name}.json")

            # 自动生成导出文件
            self._export_profile_json(learner_name, result_data)
            self._export_profile_excel(learner_name, result_data)
            self._export_learning_pdf(learner_name, result_data)
            self._export_learning_word(learner_name, result_data)
        except Exception as e:
            print(f"  ⚠️ 保存/导出失败: {e}")

        print(f"\n✅ 完成！输出: {self.output_dir}")
        return state

    def _build_result_json(self, state):
        """构建与前端格式一致的完整 JSON 数据"""
        result = {"status": "ok"}

        if state.framework:
            fw = state.framework
            result["framework"] = {
                "position_name": fw.position_name,
                "position_description": fw.position_description,
                "summary": fw.summary,
                "skill_categories": fw.skill_categories,
                "skill_points": [
                    {"id": sp.id, "name": sp.name, "description": sp.description,
                     "category": sp.category, "required_level": sp.required_level.value,
                     "prerequisites": sp.prerequisites, "keywords": sp.keywords}
                    for sp in fw.skill_points
                ],
                "required_qualities": fw.required_qualities,
                "career_path": fw.career_path,
            }

        # 简历评估数据
        if state.resume_profile:
            rp = state.resume_profile
            result["resume_profile"] = {
                "name": rp.name,
                "education": rp.education,
                "experience_years": rp.experience_years,
                "skills_found": rp.skills_found,
                "projects": rp.projects,
                "work_experience": rp.work_experience,
                "strengths_from_resume": rp.strengths_from_resume,
            }
            # 初始评估数据也包含在内
            if rp.initial_assessment:
                ia = rp.initial_assessment
                result["resume_initial_assessment"] = {
                    "overall_score": ia.overall_score,
                    "overall_level": ia.overall_level.value,
                    "skill_assessments": [
                        {"skill_point_id": sa.skill_point_id, "skill_name": sa.skill_name,
                         "score": sa.score, "current_level": sa.current_level.value,
                         "strengths": sa.strengths}
                        for sa in ia.skill_assessments
                    ],
                    "summary": ia.conclusion,
                }

        if state.learning_content:
            lc = state.learning_content
            result["learning"] = {
                "total_modules": lc.total_modules,
                "total_minutes": lc.total_minutes,
                "contents": [
                    {
                        "skill_point": {"id": c.skill_point.id, "name": c.skill_point.name, "category": c.skill_point.category},
                        "summary": c.summary,
                        "key_concepts": c.key_concepts,
                        "learning_modules": [
                            {"id": m.id, "title": m.title, "description": m.description,
                             "estimated_minutes": m.estimated_minutes, "content": m.content}
                            for m in c.learning_modules
                        ]
                    }
                    for c in lc.contents
                ]
            }

        if state.training_plan:
            tp = state.training_plan
            result["training"] = {
                "title": tp.title, "description": tp.description,
                "total_tasks": tp.total_tasks, "total_estimated_hours": tp.total_estimated_hours,
                "tasks": [
                    {"id": t.id, "title": t.title, "description": t.description,
                     "type": t.type.value, "skill_point_id": t.skill_point_id,
                     "difficulty": t.difficulty.value, "requirements": t.requirements,
                     "hints": t.hints, "reference_solution": t.reference_solution,
                     "evaluation_criteria": t.evaluation_criteria, "estimated_minutes": t.estimated_minutes}
                    for t in tp.tasks
                ],
                "scenarios": [
                    {"id": s.id, "title": s.title, "description": s.description,
                     "context": s.context, "difficulty": s.difficulty.value,
                     "expected_outcome": s.expected_outcome}
                    for s in tp.scenarios
                ],
            }

        if state.test_papers:
            result["test_papers"] = [
                {
                    "id": p.id, "title": p.title, "description": p.description,
                    "time_limit_minutes": p.time_limit_minutes, "passing_score": p.passing_score,
                    "total_score": p.total_score,
                    "questions": [
                        {"id": q.id, "question_type": q.question_type.value, "question_text": q.question_text,
                         "skill_point_id": q.skill_point_id, "difficulty": q.difficulty.value,
                         "options": q.options, "correct_answer": q.correct_answer,
                         "explanation": q.explanation, "score": q.score, "tags": q.tags}
                        for q in p.questions
                    ]
                }
                for p in state.test_papers
            ]

        if state.assessment:
            a = state.assessment
            result["assessment"] = {
                "user_name": a.user_name, "position_name": a.position_name,
                "assessment_date": a.assessment_date, "period": a.period,
                "overall_score": a.overall_score, "overall_level": a.overall_level.value,
                "skill_assessments": [
                    {"skill_point_id": sa.skill_point_id, "skill_name": sa.skill_name,
                     "current_level": sa.current_level.value,
                     "previous_level": sa.previous_level.value if sa.previous_level else None,
                     "score": sa.score, "progress_percentage": sa.progress_percentage,
                     "strengths": sa.strengths, "weaknesses": sa.weaknesses,
                     "practice_recommendations": sa.practice_recommendations}
                    for sa in a.skill_assessments
                ],
                "overall_strengths": a.overall_strengths,
                "overall_weaknesses": a.overall_weaknesses,
                "growth_trend": a.growth_trend,
                "next_stage_plan": a.next_stage_plan,
                "conclusion": a.conclusion,
            }

        return result

    def run_train(self, position: str) -> None:
        """仅生成训练任务"""
        from demo_cases import get_demo_framework
        from models import LearningContentOutput, LearningContent, LearningModule

        framework = get_demo_framework(position)
        self._phase(f"🏋️ 训练任务: {position}")
        print(f"  技能: {[sp.name for sp in framework.skill_points]}")

        # 简易学习内容
        contents = [LearningContent(
            skill_point=sp,
            learning_modules=[LearningModule(id=f"M_{sp.id}", title=f"{sp.name}",
                                             description=sp.description,
                                             skill_point_id=sp.id,
                                             content=f"# {sp.name}\n{sp.description}")],
            key_concepts=[sp.name], summary=sp.description
        ) for sp in framework.skill_points]
        lc = LearningContentOutput(framework=framework, contents=contents,
                                    total_modules=len(contents),
                                    total_minutes=len(contents)*30)

        plan = self.training_agent.generate(framework, lc)
        print(f"\n  {plan.total_tasks}个任务, {len(plan.scenarios)}个场景, {plan.total_estimated_hours:.1f}h")
        for t in plan.tasks:
            print(f"\n  [{t.type.value}] {t.title} ({t.difficulty.value}, {t.estimated_minutes}min)")
            print(f"  {t.description[:80]}")
            if t.evaluation_criteria:
                print(f"  评价: {'; '.join(t.evaluation_criteria[:2])}")

    def run_test(self, position: str, student_name: str = "学员", count: int = 15) -> None:
        """仅生成测试试卷"""
        from demo_cases import get_demo_framework
        from models import LearningContentOutput, LearningContent, LearningModule

        framework = get_demo_framework(position)
        self._phase(f"📝 测试考核: {position}")

        contents = [LearningContent(
            skill_point=sp,
            learning_modules=[LearningModule(id=f"M_{sp.id}", title=f"{sp.name}",
                                             description=sp.description,
                                             skill_point_id=sp.id,
                                             content=f"# {sp.name}\n{sp.description}")],
            key_concepts=[sp.name], summary=sp.description
        ) for sp in framework.skill_points]
        lc = LearningContentOutput(framework=framework, contents=contents,
                                    total_modules=len(contents),
                                    total_minutes=len(contents)*30)

        paper = self.test_agent.generate(framework, lc, num_questions=count)
        self._save_output(f"04_测试试卷_{student_name}", self._format_test_md(paper))
        print(f"\n  {paper.title}")
        print(f"  {len(paper.questions)}题 | 总分{paper.total_score} | {paper.time_limit_minutes}分钟")
        for i, q in enumerate(paper.questions):
            print(f"\n  {i+1}. [{q.question_type.value}] {q.question_text[:60]}")
            if q.options:
                for o in q.options[:4]:
                    print(f"      {o}")
            print(f"      答案: {q.correct_answer[:40]} | {q.score}分")

    def _save_output(self, name: str, content: str):
        """保存阶段输出到 output 目录"""
        path = self.output_dir / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        print(f"  💾 {path.name}")

    @staticmethod
    def _phase(name: str):
        print(f"\n{'─'*40}\n  {name}\n{'─'*40}")

    @staticmethod
    def _summary_framework(fw):
        if fw:
            print(f"\n  岗位: {fw.position_name}")
            print(f"  分类({len(fw.skill_categories)}): {', '.join(fw.skill_categories)}")
            print(f"  技能点: {len(fw.skill_points)}个")

    # ---- 格式化输出 ----
    def _format_framework_md(self, fw) -> str:
        lines = [f"# {fw.position_name} 能力框架", "", f"**描述:** {fw.position_description}", f"**总结:** {fw.summary}"]
        for cat in fw.skill_categories:
            lines.append(f"\n## {cat}")
            for sp in [s for s in fw.skill_points if s.category == cat]:
                lines.append(f"- **{sp.name}** ({sp.required_level.value}): {sp.description}")
        return "\n".join(lines)

    def _format_learning_md(self, lc) -> str:
        lines = [f"# 学习内容", f"**模块数:** {lc.total_modules} | **预估时间:** {lc.total_minutes}分钟"]
        for c in lc.contents:
            lines.append(f"\n## {c.skill_point.name}")
            lines.append(f"**关键概念:** {', '.join(c.key_concepts[:5])}")
            for m in c.learning_modules:
                lines.append(f"\n### {m.title}")
                lines.append(m.content)
        return "\n".join(lines)

    def _format_training_md(self, plan) -> str:
        lines = [f"# 训练计划", f"**{plan.title}**", f"**{plan.description}**", f"**{plan.total_tasks}个任务, {plan.total_estimated_hours:.1f}小时"]
        for t in plan.tasks:
            lines.append(f"\n## {t.title}")
            lines.append(f"- 类型: {t.type.value} | 难度: {t.difficulty.value} | 预估: {t.estimated_minutes}分钟")
            lines.append(f"- 描述: {t.description}")
            if t.evaluation_criteria:
                lines.append(f"- 评价: {'; '.join(t.evaluation_criteria[:3])}")
        return "\n".join(lines)

    def _format_test_md(self, paper) -> str:
        lines = [f"# {paper.title}", f"**{len(paper.questions)}题 | 总分{paper.total_score} | {paper.time_limit_minutes}分钟**"]
        for i, q in enumerate(paper.questions):
            lines.append(f"\n## 第{i+1}题 ({q.score}分) [{q.question_type.value}]")
            lines.append(q.question_text)
            if q.options:
                for o in q.options:
                    lines.append(f"- {o}")
            lines.append(f"**答案:** {q.correct_answer}")
            lines.append(f"**解析:** {q.explanation}")
        return "\n".join(lines)

    def _format_assessment_md(self, report) -> str:
        lines = [f"# 能力评估报告", f"**学员:** {report.user_name}", f"**岗位:** {report.position_name}",
                 f"**综合评分:** {report.overall_score}/100 | **等级:** {report.overall_level.value}"]
        for sa in report.skill_assessments:
            lines.append(f"\n## {sa.skill_name}")
            lines.append(f"- 得分: {sa.score} | 等级: {sa.current_level.value}")
            if sa.strengths:
                lines.append(f"- 优势: {', '.join(sa.strengths[:3])}")
            if sa.weaknesses:
                lines.append(f"- 待提升: {', '.join(sa.weaknesses[:3])}")
        lines.append(f"\n## 综合评语\n{report.conclusion}")
        return "\n".join(lines)

    def _format_resume_md(self, profile) -> str:
        """格式化简历评估结果为Markdown"""
        lines = [f"# 简历评估报告", f"**姓名:** {profile.name}"]
        if profile.education:
            lines.append(f"**学历:** {profile.education}")
        if profile.experience_years:
            lines.append(f"**工作年限:** {profile.experience_years}年")
        if profile.skills_found:
            lines.append(f"\n## 发现的技能\n{', '.join(profile.skills_found)}")
        if profile.projects:
            lines.append(f"\n## 项目经历")
            for p in profile.projects:
                lines.append(f"- **{p.get('name', '')}**: {p.get('description', '')}")
        if profile.strengths_from_resume:
            lines.append(f"\n## 简历优势\n" + "\n".join([f"- {s}" for s in profile.strengths_from_resume]))
        if profile.initial_assessment:
            lines.append(f"\n## 初始评估\n综合评分: {profile.initial_assessment.overall_score}/100")
            for sa in profile.initial_assessment.skill_assessments:
                lines.append(f"- {sa.skill_name}: {sa.score}分")
        return "\n".join(lines)

    def regenerate(self, stage: str, result_path: str, extra_prompt: str = "",
                   completed_items: dict = None):
        """
        重新生成指定阶段并更新 result JSON

        Args:
            stage: "learning" | "training" | "test"
            result_path: result_*.json 文件路径
            extra_prompt: 用户需求描述（如"跳过Java基础，加深Spring"）
            completed_items: 前端传来的完成情况 {learning: {}, training: {}, testScore, ...}
        Returns:
            更新后的 result dict
        """
        import json as _json
        with open(result_path, 'r', encoding='utf-8') as f:
            result = _json.load(f)

        # 从现有 result 重建 framework 对象
        fw_data = result.get("framework", {})
        SkillPoint = __import__('models', fromlist=['SkillPoint']).SkillPoint
        framework = CapabilityFramework(
            position_name=fw_data.get("position_name", ""),
            position_description=fw_data.get("position_description", ""),
            summary=fw_data.get("summary", ""),
            skill_categories=fw_data.get("skill_categories", []),
            skill_points=[
                SkillPoint(
                    id=sp["id"], name=sp["name"], description=sp.get("description", ""),
                    category=sp.get("category", "通用"),
                    required_level=SkillLevel(sp.get("required_level", "junior")),
                    prerequisites=sp.get("prerequisites", []),
                    keywords=sp.get("keywords", []),
                )
                for sp in fw_data.get("skill_points", [])
            ],
        )

        # 构建上下文：用户需求 + 完成情况 + 薄弱环节
        context_parts = []
        if extra_prompt:
            context_parts.append(f"用户需求：{extra_prompt}")

        if completed_items:
            done_learn = list(completed_items.get("learning", {}).keys())
            done_train = list(completed_items.get("training", {}).keys())
            if done_learn:
                context_parts.append(f"学生已完成的学习模块ID：{', '.join(done_learn)}")
            if done_train:
                context_parts.append(f"学生已完成的训练任务ID：{', '.join(done_train)}")
            test_score = completed_items.get("testScore")
            if test_score is not None:
                context_parts.append(f"学生上次考核得分：{test_score}分")

        # 从评估数据提取薄弱环节
        asm = result.get("assessment", {})
        weak_skills = [sa.get("skill_name", "") for sa in asm.get("skill_assessments", [])
                       if sa.get("score", 100) < 60]
        if weak_skills:
            context_parts.append(f"学生薄弱技能点（分数<60）：{', '.join(weak_skills)}")

        extra_context = "\n".join(context_parts) if context_parts else ""

        if stage == "training":
            self._phase("🏋️ 重新生成训练任务")
            from models import LearningContentOutput, LearningContent, LearningModule
            contents = [LearningContent(
                skill_point=sp,
                learning_modules=[LearningModule(id=f"M_{sp.id}", title=sp.name,
                                                 description=sp.description, skill_point_id=sp.id,
                                                 content=f"# {sp.name}\n{sp.description}")],
                key_concepts=[sp.name], summary=sp.description,
            ) for sp in framework.skill_points]
            lc = LearningContentOutput(framework=framework, contents=contents,
                                        total_modules=len(contents), total_minutes=len(contents)*30)
            plan = self.training_agent.generate(framework, lc, extra_context=extra_context)
            result["training"] = {
                "title": plan.title, "description": plan.description,
                "total_tasks": plan.total_tasks, "total_estimated_hours": plan.total_estimated_hours,
                "tasks": [
                    {"id": t.id, "title": t.title, "description": t.description,
                     "type": t.type.value, "skill_point_id": t.skill_point_id,
                     "difficulty": t.difficulty.value, "requirements": t.requirements,
                     "hints": t.hints, "reference_solution": t.reference_solution,
                     "evaluation_criteria": t.evaluation_criteria, "estimated_minutes": t.estimated_minutes}
                    for t in plan.tasks
                ],
                "scenarios": [
                    {"id": s.id, "title": s.title, "description": s.description,
                     "context": s.context, "difficulty": s.difficulty.value,
                     "expected_outcome": s.expected_outcome}
                    for s in plan.scenarios
                ],
            }
            print(f"  ✅ 训练任务重新生成完成: {plan.total_tasks}个任务")

        elif stage == "test":
            self._phase("📝 重新生成测试试卷")
            from models import LearningContentOutput, LearningContent, LearningModule
            contents = [LearningContent(
                skill_point=sp,
                learning_modules=[LearningModule(id=f"M_{sp.id}", title=sp.name,
                                                 description=sp.description, skill_point_id=sp.id,
                                                 content=f"# {sp.name}\n{sp.description}")],
                key_concepts=[sp.name], summary=sp.description,
            ) for sp in framework.skill_points]
            lc = LearningContentOutput(framework=framework, contents=contents,
                                        total_modules=len(contents), total_minutes=len(contents)*30)
            paper = self.test_agent.generate(framework, lc, num_questions=10, extra_context=extra_context)
            result["test_papers"] = [{
                "id": paper.id, "title": paper.title, "description": paper.description,
                "time_limit_minutes": paper.time_limit_minutes, "passing_score": paper.passing_score,
                "total_score": paper.total_score,
                "questions": [
                    {"id": q.id, "question_type": q.question_type.value, "question_text": q.question_text,
                     "skill_point_id": q.skill_point_id, "difficulty": q.difficulty.value,
                     "options": q.options, "correct_answer": q.correct_answer,
                     "explanation": q.explanation, "score": q.score, "tags": q.tags}
                    for q in paper.questions
                ]
            }]
            print(f"  ✅ 试卷重新生成完成: {len(paper.questions)}题")

        elif stage == "learning":
            self._phase("📚 重新生成学习内容")
            from models import LearningContentOutput
            lc = self.learning_agent.generate(framework, extra_context=extra_context)
            result["learning"] = {
                "total_modules": lc.total_modules, "total_minutes": lc.total_minutes,
                "contents": [
                    {
                        "skill_point": {"id": c.skill_point.id, "name": c.skill_point.name, "category": c.skill_point.category},
                        "summary": c.summary, "key_concepts": c.key_concepts,
                        "learning_modules": [
                            {"id": m.id, "title": m.title, "description": m.description,
                             "estimated_minutes": m.estimated_minutes, "content": m.content}
                            for m in c.learning_modules
                        ]
                    }
                    for c in lc.contents
                ]
            }
            print(f"  ✅ 学习内容重新生成完成: {lc.total_modules}个模块")

        # 保存更新后的 result
        with open(result_path, 'w', encoding='utf-8') as f:
            _json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  💾 已更新 {result_path}")

        # 重新生成导出文件
        self._export_profile_json(os.path.basename(result_path).replace("result_", "").replace(".json", ""), result)
        self._export_profile_excel(os.path.basename(result_path).replace("result_", "").replace(".json", ""), result)
        self._export_learning_pdf(os.path.basename(result_path).replace("result_", "").replace(".json", ""), result)
        self._export_learning_word(os.path.basename(result_path).replace("result_", "").replace(".json", ""), result)

        return result

    # ============ 导出方法 ============

    def _export_profile_json(self, name, data):
        """导出能力画像 JSON"""
        fw = data.get("framework", {})
        asm = data.get("assessment", {})
        rp = data.get("resume_profile", {})
        profile = {
            "姓名": name,
            "目标岗位": fw.get("position_name", ""),
            "岗位描述": fw.get("position_description", ""),
            "综合评分": asm.get("overall_score", 0),
            "综合等级": asm.get("overall_level", ""),
            "评估日期": asm.get("assessment_date", ""),
            "优势": asm.get("overall_strengths", []),
            "待提升": asm.get("overall_weaknesses", []),
            "结论": asm.get("conclusion", ""),
            "技能评估": [],
            "雷达图数据": {"labels": [], "values": []},
        }
        for sa in asm.get("skill_assessments", []):
            profile["技能评估"].append({
                "技能名称": sa.get("skill_name", ""),
                "当前等级": sa.get("current_level", ""),
                "得分": sa.get("score", 0),
                "优势": sa.get("strengths", []),
                "不足": sa.get("weaknesses", []),
            })
            profile["雷达图数据"]["labels"].append(sa.get("skill_name", ""))
            profile["雷达图数据"]["values"].append(sa.get("score", 0))
        if rp:
            profile["简历信息"] = {
                "学历": rp.get("education", ""),
                "工作年限": rp.get("experience_years", 0),
                "发现技能": rp.get("skills_found", []),
            }
        out = self.output_dir / f"能力画像_{name}.json"
        out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  💾 {out.name}")

    def _export_profile_excel(self, name, data):
        """导出能力画像 Excel（含雷达图）"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            from openpyxl.chart import RadarChart, Reference
        except ImportError:
            print("  ⚠️ openpyxl 未安装，跳过 Excel 导出")
            return

        fw = data.get("framework", {})
        asm = data.get("assessment", {})
        wb = Workbook()

        # Sheet1: 基本信息
        ws1 = wb.active
        ws1.title = "基本信息"
        bold = Font(bold=True, size=11)
        rows = [
            ("姓名", name),
            ("目标岗位", fw.get("position_name", "")),
            ("综合评分", asm.get("overall_score", 0)),
            ("综合等级", asm.get("overall_level", "")),
            ("评估日期", asm.get("assessment_date", "")),
            ("优势", "、".join(asm.get("overall_strengths", []))),
            ("待提升", "、".join(asm.get("overall_weaknesses", []))),
            ("结论", asm.get("conclusion", "")),
        ]
        for i, (k, v) in enumerate(rows, 1):
            ws1.cell(i, 1, k).font = bold
            ws1.cell(i, 2, v)
        ws1.column_dimensions['A'].width = 15
        ws1.column_dimensions['B'].width = 60

        # Sheet2: 技能评估
        ws2 = wb.create_sheet("技能评估")
        headers = ["技能名称", "当前等级", "得分"]
        fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for j, h in enumerate(headers, 1):
            c = ws2.cell(1, j, h)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = fill
        for i, sa in enumerate(asm.get("skill_assessments", []), 2):
            ws2.cell(i, 1, sa.get("skill_name", ""))
            ws2.cell(i, 2, sa.get("current_level", ""))
            ws2.cell(i, 3, sa.get("score", 0))

        # Sheet3: 雷达图
        ws3 = wb.create_sheet("雷达图")
        skills = asm.get("skill_assessments", [])
        ws3.cell(1, 1, "技能").font = bold
        ws3.cell(1, 2, "得分").font = bold
        for i, sa in enumerate(skills, 2):
            ws3.cell(i, 1, sa.get("skill_name", ""))
            ws3.cell(i, 2, sa.get("score", 0))
        if len(skills) >= 3:
            chart = RadarChart()
            chart.title = f"{name} 能力雷达图"
            cats = Reference(ws3, 1, 2, 1, len(skills) + 1)
            vals = Reference(ws3, 2, 1, 2, len(skills) + 1)
            chart.add_data(vals, titles_from_data=True)
            chart.set_categories(cats)
            chart.width = 18
            chart.height = 14
            ws3.add_chart(chart, "D2")

        out = self.output_dir / f"能力画像_{name}.xlsx"
        wb.save(str(out))
        print(f"  💾 {out.name}")

    def _export_learning_pdf(self, name, data):
        """导出学习任务 PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            print("  ⚠️ reportlab 未安装，跳过 PDF 导出")
            return

        import os as _os
        font_paths = ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc",
                       "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
        cn = "Helvetica"
        for fp in font_paths:
            if _os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('CN', fp)); cn = 'CN'; break
                except: pass

        fw = data.get("framework", {})
        asm = data.get("assessment", {})
        learning = data.get("learning", {})
        training = data.get("training", {})

        out = self.output_dir / f"学习任务_{name}.pdf"
        doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        ts = ParagraphStyle('TS', parent=styles['Title'], fontName=cn, fontSize=18, spaceAfter=20)
        hs = ParagraphStyle('HS', parent=styles['Heading2'], fontName=cn, fontSize=14, spaceBefore=16, spaceAfter=10)
        bs = ParagraphStyle('BS', parent=styles['Normal'], fontName=cn, fontSize=10, leading=16)

        elems = []
        elems.append(Paragraph(f"学习任务计划 - {name}", ts))
        elems.append(Paragraph(f"目标岗位：{fw.get('position_name', '')}　综合评分：{asm.get('overall_score', 0)}分", bs))
        weak = asm.get("overall_weaknesses", [])
        if weak:
            elems.append(Paragraph(f"薄弱环节：{'、'.join(weak)}", bs))
        elems.append(Spacer(1, 20))

        # 学习模块
        elems.append(Paragraph("一、学习模块", hs))
        idx = 1
        for content in learning.get("contents", []):
            sp = content.get("skill_point", {})
            for m in content.get("learning_modules", []):
                elems.append(Paragraph(f"<b>{idx}. [{sp.get('name', '')}] {m.get('title', '')}</b>（{m.get('estimated_minutes', 30)}分钟）", bs))
                elems.append(Paragraph(f"　达标标准：完成模块内容学习并通过课后思考题", bs))
                idx += 1
        elems.append(Spacer(1, 15))

        # 训练任务
        elems.append(Paragraph("二、训练任务", hs))
        for i, t in enumerate(training.get("tasks", []), 1):
            elems.append(Paragraph(f"<b>{i}. {t.get('title', '')}</b>　{t.get('type', '')} / {t.get('difficulty', '')} / {t.get('estimated_minutes', 30)}分钟", bs))
            desc = t.get("description", "")
            if desc:
                elems.append(Paragraph(f"　{desc[:150]}", bs))
            ec = t.get("evaluation_criteria", [])
            if ec:
                elems.append(Paragraph(f"　达标标准：{'；'.join(ec[:3])}", bs))

        doc.build(elems)
        print(f"  💾 {out.name}")

    def _export_learning_word(self, name, data):
        """导出学习任务 Word"""
        try:
            from docx import Document
            from docx.shared import Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print("  ⚠️ python-docx 未安装，跳过 Word 导出")
            return

        fw = data.get("framework", {})
        asm = data.get("assessment", {})
        learning = data.get("learning", {})
        training = data.get("training", {})

        doc = Document()
        style = doc.styles['Normal']
        style.font.size = Pt(10.5)

        title = doc.add_heading(f'学习任务计划 - {name}', level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f'目标岗位：{fw.get("position_name", "")}')
        doc.add_paragraph(f'综合评分：{asm.get("overall_score", 0)}分')
        weak = asm.get("overall_weaknesses", [])
        if weak:
            doc.add_paragraph(f'薄弱环节：{"、".join(weak)}')
        doc.add_paragraph('')

        # 学习模块
        doc.add_heading('一、学习模块', level=1)
        idx = 1
        for content in learning.get("contents", []):
            sp = content.get("skill_point", {})
            for m in content.get("learning_modules", []):
                doc.add_heading(f'{idx}. [{sp.get("name", "")}] {m.get("title", "")}', level=2)
                doc.add_paragraph(f'时长：{m.get("estimated_minutes", 30)}分钟')
                doc.add_paragraph('达标标准：完成模块内容学习并通过课后思考题')
                idx += 1
        doc.add_paragraph('')

        # 训练任务
        doc.add_heading('二、训练任务', level=1)
        for i, t in enumerate(training.get("tasks", []), 1):
            doc.add_heading(f'{i}. {t.get("title", "")}', level=2)
            doc.add_paragraph(f'类型：{t.get("type", "")}　难度：{t.get("difficulty", "")}　时长：{t.get("estimated_minutes", 30)}分钟')
            desc = t.get("description", "")
            if desc:
                doc.add_paragraph(desc[:200])
            reqs = t.get("requirements", [])
            if reqs:
                doc.add_paragraph('任务要求：')
                for r in reqs:
                    doc.add_paragraph(f'• {r}', style='List Bullet')
            ec = t.get("evaluation_criteria", [])
            if ec:
                doc.add_paragraph('达标标准：')
                for c in ec:
                    doc.add_paragraph(f'• {c}', style='List Bullet')

        out = self.output_dir / f"学习任务_{name}.docx"
        doc.save(str(out))
        print(f"  💾 {out.name}")
