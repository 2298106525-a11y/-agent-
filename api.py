"""
学练测一体化 API — 方向二专用

启动: python api.py --port 8000

端点:
  GET  /api/health        — 健康检查
  POST /api/full           — 完整学练测评（岗位分析→学习内容→训练→测试→评估）
  POST /api/train          — 仅训练任务
  POST /api/test           — 仅测试试卷
"""

import sys, os, json
from datetime import datetime
from typing import List, Optional, Dict, Any

if sys.stdout.encoding and sys.stdout.encoding.lower() in ('gbk', 'gb2312', 'gb18030'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from coordinator import SkillTrainerCoordinator
import database as db

app = FastAPI(title="学练测一体化", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    """API根路径 - 返回API信息"""
    return {
        "name": "学练测一体化能力提升系统",
        "version": "2.0.0",
        "description": "打通学习、训练与测评全过程，实现学生能力成长的可量化、可验证与可追踪",
        "endpoints": {
            "health": "GET /api/health",
            "check": "GET /api/check/{name} - 检查学生是否存在",
            "demo": "GET /api/demo?position=岗位名称",
            "full": "POST /api/full",
            "train": "POST /api/train",
            "test": "POST /api/test"
        },
        "frontend": "http://localhost:5173",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/api/check/{name}")
async def check_student(name: str):
    """检查学生是否已有学习数据"""
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    if not os.path.exists(output_dir):
        return {"exists": False, "name": name, "files": []}

    # 查找该学生的文件
    student_files = []
    for f in os.listdir(output_dir):
        if name in f and not f.startswith("checkpoint"):
            student_files.append(f)

    # 检查checkpoint
    checkpoint_path = os.path.join(output_dir, f"checkpoint_{name}.json")
    checkpoint = None
    if os.path.exists(checkpoint_path):
        import json
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

    exists = len(student_files) > 0 or checkpoint is not None

    return {
        "exists": exists,
        "name": name,
        "files": student_files,
        "checkpoint": checkpoint
    }

_coordinator = None

def get_coordinator():
    global _coordinator
    if _coordinator is None:
        _coordinator = SkillTrainerCoordinator()
    return _coordinator


class FullRequest(BaseModel):
    position: str
    name: str = "学员"
    level: str = "初级"
    student_data: Optional[Dict[str, Any]] = None
    resume_text: Optional[str] = None  # 简历纯文本内容

class TrainRequest(BaseModel):
    position: str

class TestRequest(BaseModel):
    position: str
    count: int = 15


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ============ 学生数据 API ============

@app.get("/api/students")
async def list_students():
    """列出所有学生"""
    students = db.list_students()
    return {"status": "ok", "students": students}


@app.get("/api/students/{name}/full")
async def get_student_full(name: str):
    """获取学生的完整数据（结果 + 进度 + 考核成绩）"""
    data = db.load_student_full(name)
    return {"status": "ok", "data": data}


class ProgressRequest(BaseModel):
    item_type: str  # 'learning' 或 'training'
    item_id: str


@app.post("/api/students/{name}/progress")
async def toggle_student_progress(name: str, req: ProgressRequest):
    """切换学习模块或训练任务的完成状态"""
    db.toggle_progress(name, req.item_type, req.item_id)
    progress = db.get_progress(name)
    return {"status": "ok", "progress": progress}


class TestScoreRequest(BaseModel):
    score: int
    correct: int
    total: int


@app.post("/api/students/{name}/test-score")
async def save_student_test_score(name: str, req: TestScoreRequest):
    """保存学生的考核成绩"""
    db.save_test_score(name, req.score, req.correct, req.total)
    return {"status": "ok"}


class StudentResultRequest(BaseModel):
    result: Dict[str, Any]
    position: str = ""
    level: str = "初级"
    current_step: int = 0


@app.post("/api/students/{name}/result")
async def save_student_result(name: str, req: StudentResultRequest):
    """保存学生的 LLM 生成结果"""
    db.create_or_update_student(name, req.position, req.level, req.current_step)
    db.save_result(name, req.result)
    return {"status": "ok"}


class CurrentStepRequest(BaseModel):
    current_step: int


@app.post("/api/students/{name}/step")
async def save_student_step(name: str, req: CurrentStepRequest):
    """保存学生的当前步骤"""
    db.create_or_update_student(name, current_step=req.current_step)
    return {"status": "ok"}


@app.delete("/api/students/{name}")
async def delete_student(name: str):
    """删除学生及其所有数据"""
    db.delete_student(name)
    return {"status": "ok"}


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """上传简历PDF，返回解析后的纯文本"""

    try:
        import io
        from PyPDF2 import PdfReader

        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if not text.strip():
            raise HTTPException(status_code=400, detail="无法从PDF中提取文本，请确认文件包含可选择的文字")

        return {
            "status": "ok",
            "text": text.strip(),
            "pages": len(reader.pages),
            "chars": len(text.strip())
        }
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="服务器未安装PyPDF2，请运行: pip install PyPDF2")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF解析失败: {str(e)}")


@app.get("/api/test/stream")
async def test_stream():
    """测试 SSE 连接 — 不调用 LLM，立即返回事件"""
    from fastapi.responses import StreamingResponse
    import asyncio

    async def gen():
        for i in range(5):
            yield f"event: progress\ndata: {{\"stage\": {i}, \"total\": 5, \"label\": \"测试阶段 {i+1}\"}}\n\n"
            await asyncio.sleep(0.3)
        yield f"event: token\ndata: {{\"agent\": \"test\", \"text\": \"Hello from SSE!\"}}\n\n"
        yield f"event: done\ndata: {{\"status\": \"ok\", \"message\": \"测试完成\"}}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/demo")
async def demo(position: str = "Java后端开发工程师"):
    """获取演示数据（不调用LLM）"""
    from demo_cases import get_demo_framework
    import random

    framework = get_demo_framework(position)

    # 模拟学生成绩
    skill_scores = {}
    for sp in framework.skill_points:
        skill_scores[sp.id] = random.randint(55, 95)
    overall_score = round(sum(skill_scores.values()) / len(skill_scores), 1) if skill_scores else 70

    # 模拟评估报告
    from models import AssessmentReport, SkillAssessment, SkillLevel
    assessment = AssessmentReport(
        user_name="演示学生",
        position_name=position,
        assessment_date="2025-05-28",
        period="当前阶段",
        overall_score=overall_score,
        overall_level=SkillLevel.INTERMEDIATE,
        skill_assessments=[
            SkillAssessment(
                skill_point_id=sp.id,
                skill_name=sp.name,
                current_level=SkillLevel.JUNIOR,
                score=skill_scores.get(sp.id, 70),
                progress_percentage=random.randint(5, 25),
                strengths=["基础扎实"],
                weaknesses=["需深入学习"],
                practice_recommendations=[f"多练习{sp.name}相关题目"]
            )
            for sp in framework.skill_points
        ],
        overall_strengths=["基础扎实", "学习积极", "有项目经验"],
        overall_weaknesses=["高级特性待深入", "实战经验不足"],
        growth_trend="稳步上升",
        next_stage_plan="继续深入学习核心技能",
        conclusion=f"该学生在{position}方向有较好的基础，建议继续深入学习。"
    )

    return {
        "status": "ok",
        "framework": {
            "position_name": framework.position_name,
            "position_description": framework.position_description,
            "summary": framework.summary,
            "skill_categories": framework.skill_categories,
            "skill_points": [
                {
                    "id": sp.id,
                    "name": sp.name,
                    "description": sp.description,
                    "category": sp.category,
                    "required_level": sp.required_level.value,
                    "prerequisites": sp.prerequisites,
                    "keywords": sp.keywords
                }
                for sp in framework.skill_points
            ],
            "required_qualities": framework.required_qualities,
            "career_path": framework.career_path
        },
        "learning": {
            "total_modules": len(framework.skill_points) * 2,
            "total_minutes": len(framework.skill_points) * 60,
            "contents": [
                {
                    "skill_point": {
                        "id": sp.id,
                        "name": sp.name,
                        "category": sp.category
                    },
                    "summary": sp.description,
                    "key_concepts": sp.keywords[:3],
                    "learning_modules": [
                        {
                            "id": f"MOD_{i*2+1:03d}",
                            "title": f"{sp.name}基础",
                            "description": f"学习{sp.name}的核心概念",
                            "estimated_minutes": 30,
                            "content": f"# {sp.name}基础\n\n## 学习目标\n- 理解{sp.name}的核心概念\n- 掌握基本使用方法\n\n## 内容\n{sp.description}"
                        },
                        {
                            "id": f"MOD_{i*2+2:03d}",
                            "title": f"{sp.name}进阶",
                            "description": f"深入学习{sp.name}的高级特性",
                            "estimated_minutes": 45,
                            "content": f"# {sp.name}进阶\n\n## 学习目标\n- 掌握{sp.name}的高级用法\n- 能够解决实际问题\n\n## 内容\n{sp.description}"
                        }
                    ]
                }
                for i, sp in enumerate(framework.skill_points)
            ]
        },
        "training": {
            "title": f"{position}训练计划",
            "description": f"针对{position}岗位的系统训练",
            "total_tasks": len(framework.skill_points),
            "total_estimated_hours": len(framework.skill_points) * 1.5,
            "tasks": [
                {
                    "id": f"TASK_{i+1:03d}",
                    "title": f"{sp.name}专项训练",
                    "description": f"通过实践练习掌握{sp.name}的核心技能",
                    "type": "exercise" if i % 3 != 0 else "case_study",
                    "skill_point_id": sp.id,
                    "difficulty": sp.required_level.value,
                    "requirements": [f"完成{sp.name}相关练习", "提交代码"],
                    "hints": [f"参考{sp.name}官方文档"],
                    "evaluation_criteria": ["代码质量", "功能完整性"],
                    "estimated_minutes": 60
                }
                for i, sp in enumerate(framework.skill_points)
            ],
            "scenarios": [
                {
                    "id": "SCENE_001",
                    "title": f"{position}综合实战",
                    "description": "模拟真实工作场景完成综合任务",
                    "context": "你是一名初级工程师，需要完成一个实际项目",
                    "difficulty": "intermediate",
                    "expected_outcome": "完成项目并输出文档"
                }
            ]
        },
        "test_papers": [
            {
                "id": "PAPER_001",
                "title": f"{position}能力测试",
                "description": "测试岗位核心技能掌握程度",
                "time_limit_minutes": 60,
                "passing_score": 60,
                "total_score": len(framework.skill_points) * 10,
                "questions": [
                    {
                        "id": f"Q_{i+1:03d}",
                        "question_type": "single_choice" if i % 3 == 0 else ("short_answer" if i % 3 == 1 else "true_false"),
                        "question_text": f"关于{sp.name}，以下说法正确的是？",
                        "skill_point_id": sp.id,
                        "difficulty": sp.required_level.value,
                        "options": [f"A. {sp.name}的核心概念", f"B. {sp.name}的使用场景", f"C. {sp.name}的优缺点", f"D. 以上都是"] if i % 3 == 0 else [],
                        "correct_answer": "D" if i % 3 == 0 else f"{sp.name}的核心要点",
                        "explanation": f"考察对{sp.name}的理解程度",
                        "score": 10,
                        "tags": [sp.category]
                    }
                    for i, sp in enumerate(framework.skill_points)
                ]
            }
        ],
        "assessment": {
            "user_name": "演示学生",
            "position_name": position,
            "assessment_date": "2025-05-28",
            "period": "当前阶段",
            "overall_score": overall_score,
            "overall_level": "intermediate",
            "skill_assessments": [
                {
                    "skill_point_id": sp.id,
                    "skill_name": sp.name,
                    "current_level": "junior",
                    "score": skill_scores.get(sp.id, 70),
                    "progress_percentage": random.randint(5, 25),
                    "strengths": ["基础扎实"],
                    "weaknesses": ["需深入学习"],
                    "practice_recommendations": [f"多练习{sp.name}相关题目"]
                }
                for sp in framework.skill_points
            ],
            "overall_strengths": ["基础扎实", "学习积极", "有项目经验"],
            "overall_weaknesses": ["高级特性待深入", "实战经验不足"],
            "growth_trend": "稳步上升",
            "next_stage_plan": "继续深入学习核心技能",
            "conclusion": f"该学生在{position}方向有较好的基础，建议继续深入学习。"
        }
    }


@app.post("/api/full")
async def full(req: FullRequest):
    """完整学练测评流程 — 返回完整数据（与 demo 格式一致）"""
    from fastapi import HTTPException
    coord = get_coordinator()
    state = coord.run_full(req.position, req.name, req.level, resume_text=req.resume_text)

    if not state.framework:
        raise HTTPException(status_code=500, detail="岗位需求分析失败，请检查 LLM 配置后重试")

    # 构建与 demo 格式一致的完整返回数据
    result = {"status": "ok"}

    # framework
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

    # learning
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

    # training
    if state.training_plan:
        tp = state.training_plan
        result["training"] = {
            "title": tp.title,
            "description": tp.description,
            "total_tasks": tp.total_tasks,
            "total_estimated_hours": tp.total_estimated_hours,
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

    # test_papers
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

    # assessment
    if state.assessment:
        a = state.assessment
        result["assessment"] = {
            "user_name": a.user_name,
            "position_name": a.position_name,
            "assessment_date": a.assessment_date,
            "period": a.period,
            "overall_score": a.overall_score,
            "overall_level": a.overall_level.value,
            "skill_assessments": [
                {"skill_point_id": sa.skill_point_id, "skill_name": sa.skill_name,
                 "current_level": sa.current_level.value, "previous_level": sa.previous_level.value if sa.previous_level else None,
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


@app.get("/api/full/stream")
async def full_stream(position: str, name: str = "学员", level: str = "初级", resume_text: str = None):
    """完整学练测评流程 — SSE 流式返回，实时推送 LLM 输出和进度"""
    import threading, queue
    from fastapi.responses import StreamingResponse

    q = queue.Queue()

    def on_event(event_type, data):
        q.put((event_type, data))

    def run():
        try:
            coord = SkillTrainerCoordinator(on_event=on_event)
            state = coord.run_full(position, name, level, resume_text=resume_text)

            if not state.framework:
                q.put(("error", {"message": "岗位需求分析失败"}))
            else:
                result = _build_api_result(state)
                q.put(("done", result))
        except Exception as e:
            q.put(("error", {"message": str(e)}))
        finally:
            q.put(("__end__", None))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def event_stream():
        while True:
            try:
                event_type, data = q.get(timeout=600)
            except queue.Empty:
                yield f"event: error\ndata: {json.dumps({'message': '请求超时'}, ensure_ascii=False)}\n\n"
                break
            if event_type == "__end__":
                break
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_api_result(state):
    """从 SystemState 构建与 /api/full 格式一致的 JSON 结果"""
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


@app.post("/api/train")
async def train(req: TrainRequest):
    """仅训练任务生成"""
    coord = get_coordinator()
    coord.run_train(req.position)
    return {"status": "ok", "position": req.position}


@app.post("/api/test")
async def test(req: TestRequest):
    """仅测试试卷生成"""
    coord = get_coordinator()
    coord.run_test(req.position, req.count)
    return {"status": "ok", "position": req.position, "count": req.count}


class RegenerateRequest(BaseModel):
    name: str
    stage: str  # "learning" | "training" | "test"
    extra_prompt: str = ""  # 用户需求描述
    completed_items: Optional[Dict[str, Any]] = None  # 前端完成情况


@app.post("/api/regenerate")
async def regenerate(req: RegenerateRequest):
    """重新生成指定阶段（训练/考核/学习内容），根据用户需求定制"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    result_path = os.path.join(output_dir, f"result_{req.name}.json")

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail=f"未找到 {req.name} 的数据，请先生成学习计划")

    if req.stage not in ("learning", "training", "test"):
        raise HTTPException(status_code=400, detail="stage 必须是 learning、training 或 test")

    try:
        coord = get_coordinator()
        result = coord.regenerate(req.stage, result_path,
                                   extra_prompt=req.extra_prompt,
                                   completed_items=req.completed_items)
        return result
    except Exception as e:
        print(f"❌ 重新生成失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")


class TutorRequest(BaseModel):
    name: str
    message: str
    history: Optional[List[Dict[str, str]]] = None  # 兼容旧接口，不再使用


@app.get("/api/tutor/history/{name}")
async def get_tutor_history(name: str):
    """获取学生的对话历史"""
    messages = db.get_recent_messages(name, limit=200)
    return {"status": "ok", "messages": messages}


@app.delete("/api/tutor/history/{name}")
async def clear_tutor_history(name: str):
    """清空学生的对话历史"""
    db.clear_chat_history(name)
    return {"status": "ok"}


@app.get("/api/result/{name}")
async def get_result(name: str):
    """获取学生已生成的完整 JSON 数据（无需重新调用 LLM）"""
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    result_path = os.path.join(output_dir, f"result_{name}.json")

    if os.path.exists(result_path):
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            return {"status": "error", "message": f"读取失败: {str(e)}"}

    return {"status": "not_found", "message": f"未找到 {name} 的结果数据"}


@app.get("/api/materials/{name}")
async def get_materials(name: str):
    """获取学生的学习材料"""
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    materials = {}
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir)):
            if name in f and f.endswith(".md") and not f.startswith("checkpoint"):
                try:
                    with open(os.path.join(output_dir, f), 'r', encoding='utf-8') as file:
                        content = file.read()
                        # 根据文件名判断类型
                        if "01_岗位分析" in f:
                            materials["framework"] = {"filename": f, "content": content}
                        elif "02_学习内容" in f:
                            materials["learning"] = {"filename": f, "content": content}
                        elif "03_训练任务" in f:
                            materials["training"] = {"filename": f, "content": content}
                        elif "04_测试试卷" in f:
                            materials["test"] = {"filename": f, "content": content}
                        elif "05_评估报告" in f:
                            materials["assessment"] = {"filename": f, "content": content}
                except:
                    pass

    return {"status": "ok", "name": name, "materials": materials}


@app.post("/api/tutor")
async def tutor(req: TutorRequest):
    """伴学模式 - AI对话（带三层记忆系统，流式SSE返回）"""
    from fastapi.responses import StreamingResponse
    from agents import TutorAgent

    # 1. 保存用户消息到 DB
    db.save_chat_message(req.name, "user", req.message)

    # 2. 加载记忆层
    summary_data = db.get_latest_summary(req.name)
    summary = summary_data["summary"] if summary_data else ""
    memory = db.get_student_memory(req.name)
    recent_messages = db.get_recent_messages(req.name, limit=20)

    # 3. 构建学生档案上下文
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    checkpoint_path = os.path.join(output_dir, f"checkpoint_{req.name}.json")
    checkpoint = None
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
    position = checkpoint.get("position", "未知岗位") if checkpoint else "未知岗位"

    context_parts = []
    result_path = os.path.join(output_dir, f"result_{req.name}.json")
    if os.path.exists(result_path):
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                r = json.load(f)
            fw = r.get("framework", {})
            skills = [sp.get("name", "") for sp in fw.get("skill_points", [])]
            context_parts.append(f"岗位: {fw.get('position_name', '?')}，技能点: {', '.join(skills[:8])}")
            asm = r.get("assessment", {})
            if asm:
                context_parts.append(f"综合评分: {asm.get('overall_score', '?')}分，等级: {asm.get('overall_level', '?')}")
                if asm.get("overall_strengths"): context_parts.append(f"优势: {', '.join(asm['overall_strengths'][:3])}")
                if asm.get("overall_weaknesses"): context_parts.append(f"待提升: {', '.join(asm['overall_weaknesses'][:3])}")
            tr = r.get("training", {})
            if tr: context_parts.append(f"训练任务: {tr.get('total_tasks', 0)}个")
        except: pass
    context = "；".join(context_parts) if context_parts else "暂无学习数据"

    # 4. 用 TutorAgent 构建 messages
    tutor_agent = TutorAgent()
    messages = tutor_agent.build_messages(
        name=req.name, position=position, context=context,
        summary=summary, memory=memory,
        recent_history=recent_messages[:-1],  # 排除刚保存的用户消息（已在 user_message 中）
        user_message=req.message
    )

    # 5. 流式调用 LLM
    from config import config as cfg

    full_reply = []

    def generate():
        try:
            stream = tutor_agent.client.chat.completions.create(
                model=cfg.LLM_MODEL,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_reply.append(text)
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"❌ Tutor流式调用失败: {type(e).__name__}: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        # 6. 响应结束后：保存助手消息 + 异步处理记忆
        try:
            reply_text = "".join(full_reply)
            db.save_chat_message(req.name, "assistant", reply_text)

            # 检查是否需要压缩摘要（每 20 条消息触发一次）
            msg_count = db.get_chat_message_count(req.name)
            if msg_count > 0 and msg_count % 20 == 0:
                recent = db.get_recent_messages(req.name, limit=20)
                old_summary = summary
                new_summary = tutor_agent.compress_summary(old_summary, recent)
                if new_summary:
                    db.save_chat_summary(req.name, new_summary, msg_count)
                    print(f"  💾 对话摘要已更新: {req.name}")

            # 每 10 条消息更新一次结构化记忆
            if msg_count > 0 and msg_count % 10 == 0:
                recent = db.get_recent_messages(req.name, limit=10)
                updated_memory = tutor_agent.extract_memory(recent, memory)
                if updated_memory != memory:
                    db.update_student_memory(req.name, updated_memory)
                    print(f"  💾 结构化记忆已更新: {req.name}")
        except Exception as e:
            print(f"  ⚠️ 记忆处理失败: {e}")

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import argparse, uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"学练测一体化 API: http://localhost:{args.port}")
    uvicorn.run("api:app", host="0.0.0.0", port=args.port)
