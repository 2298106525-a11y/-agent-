"""
学练测一体化能力提升系统 — 方向二

使用:
    python run.py                          # AI 对话模式（推荐）
    python run.py "Java后端" --name "张三"   # 命令行直接生成
"""

import sys, os, json, argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coordinator import SkillTrainerCoordinator
from config import config
from openai import OpenAI


def parse_args():
    p = argparse.ArgumentParser(description="学练测一体化 — 方向二")
    p.add_argument("position", nargs="?", default=None, help="目标岗位（指定则直接生成）")
    p.add_argument("--name", "-n", default="学员")
    p.add_argument("--level", "-l", default="初级")
    p.add_argument("--data", "-d", default=None, help="学生数据JSON")
    p.add_argument("--port", type=int, default=8000, help="API端口")
    p.add_argument("--no-frontend", action="store_true", help="不启动前端")
    return p.parse_args()


def start_api_server(port=8000):
    """启动API服务（后台线程）"""
    import subprocess
    import threading

    def run_api():
        subprocess.run([sys.executable, "api.py", "--port", str(port)],
                      cwd=os.path.dirname(os.path.abspath(__file__)))

    thread = threading.Thread(target=run_api, daemon=True)
    thread.start()
    print(f"🚀 API服务已启动: http://localhost:{port}")
    return thread


def start_frontend():
    """启动前端开发服务（后台线程）"""
    import subprocess
    import threading

    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

    def run_frontend():
        # 检查是否已安装依赖
        if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
            print("📦 安装前端依赖...")
            subprocess.run("npm install", shell=True, cwd=frontend_dir)

        subprocess.run("npm run dev", shell=True, cwd=frontend_dir)

    thread = threading.Thread(target=run_frontend, daemon=True)
    thread.start()
    print(f"🎨 前端服务已启动: http://localhost:5173")
    return thread


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def student_exists(name: str, output_dir: str = "LLMs/skill_trainer/output") -> bool:
    """检查这个学生是否已有任何输出"""
    name = name.replace(" ", "_")
    for f in os.listdir(output_dir):
        if name in f and not f.startswith("checkpoint"):
            return True
    return os.path.exists(os.path.join(output_dir, f"checkpoint_{name}.json"))


def ai_new_student(name: str):
    """新学生：采集信息 → 完整生成"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    print(f"\n👋 {name} 你好！我是你的 AI 学练测评助手")
    pos = input("🎯 你想学习什么岗位？(例: Java后端开发工程师): ").strip()
    if not pos:
        print("需要指定岗位，重新开始")
        return

    level = input("📊 目标级别 [入门/初级/中级/高级] (回车=初级): ").strip() or "初级"
    data_file = input("📁 你的数据文件 (GPA/课程成绩等, 回车跳过): ").strip() or None

    raw = load_json(data_file) if data_file else None
    if raw:
        print(f"  📋 已加载: {data_file}")

    c = SkillTrainerCoordinator()
    c.output_dir = Path(output_dir)
    c.run_full(pos, name, level, raw)

    print(f"\n✅ 你的学习计划已生成！下次输入 {name} 即可进入伴学模式")


def ai_tutor(name: str):
    """老学生：AI 伴学模式"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    # 加载学生已有的内容
    files = {}
    for f in sorted(os.listdir(output_dir)):
        if name in f and f.endswith(".md"):
            phase = f.split("_")[0] if "_" in f else "unknown"
            files[phase] = os.path.join(output_dir, f)

    ck_path = os.path.join(output_dir, f"checkpoint_{name}.json")
    ck = load_json(ck_path) or {}

    print(f"\n👋 欢迎回来, {name}！")
    print(f"   岗位: {ck.get('position', '未知')}")
    print(f"   已完成: {ck.get('done', -1)+1}/5 阶段")
    if files:
        print(f"   已有文件: {', '.join(files.keys())}")
    print()
    print("我可以帮你:")
    print("   · 继续未完成的生成任务")
    print("   · 重新生成某个阶段的题目")
    print("   · 出几道练习题测试一下")
    print("   · 解答学习中的疑问")
    print("   · 修改学习计划")
    print("   (输入 q 退出)")

    client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, timeout=30)
    c = SkillTrainerCoordinator()
    c.output_dir = Path(output_dir)
    position = ck.get("position", "")

    while True:
        try:
            cmd = input(f"\n{name}> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not cmd or cmd in ('q', 'quit', 'exit'):
            break

        # LLM 解析意图
        try:
            resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": f"""解析学生学习指令:
学生: {name}, 岗位: {position}, 已完成阶段: {ck.get('done',-1)+1}/5
指令: {cmd}

返回JSON: {{"action":"continue/retrain/retest/quiz/chat", "phase":"content/training/testing/assessment", "detail":"具体做什么"}}
- continue: 继续上次断点
- retrain: 重新生成训练任务
- retest: 重新生成测试试卷
- quiz: 出几道练习题
- chat: 聊天解答问题
只输出JSON。"""}],
                max_tokens=200, temperature=0,
            )
            intent = json.loads(resp.choices[0].message.content.strip().strip("```json").strip("```").strip())
        except Exception:
            intent = {"action": "chat", "detail": cmd}

        action = intent.get("action", "chat")

        try:
            if action == "continue":
                c.run_full(position, name, ck.get("level", "初级"))
            elif action == "retrain":
                c.run_train(position, name)
            elif action == "retest":
                c.run_test(position, name)
            elif action == "quiz":
                # 随机出几道题
                from demo_cases import get_demo_framework
                from models import LearningContentOutput, LearningContent, LearningModule
                fw = get_demo_framework(position)
                contents = [LearningContent(skill_point=sp, learning_modules=[
                    LearningModule(id=f"M_{sp.id}", title=sp.name, description=sp.description,
                                   skill_point_id=sp.id, content=f"# {sp.name}")
                ], key_concepts=[sp.name]) for sp in fw.skill_points[:3]]
                lc = LearningContentOutput(framework=fw, contents=contents,
                                           total_modules=3, total_minutes=90)
                paper = SkillTrainerCoordinator().test_agent.generate(fw, lc, num_questions=5)
                print(f"\n📝 小测验 ({len(paper.questions)}题):")
                for i, q in enumerate(paper.questions):
                    print(f"\n{i+1}. {q.question_text}")
                    if q.options:
                        for o in q.options:
                            print(f"   {o}")
                    input("   你的答案(回车看答案): ")
                    print(f"   答案: {q.correct_answer}")
                    if q.explanation:
                        print(f"   解析: {q.explanation[:100]}")
            else:
                # chat 模式
                # 加载相关文件内容作为上下文
                ctx = ""
                for phase, path in sorted(files.items()):
                    try:
                        content = open(path, 'r', encoding='utf-8').read()[:2000]
                        ctx += f"\n--- {phase} ---\n{content}\n"
                    except:
                        pass

                resp = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": f"你是{name}的AI学习助手。岗位:{position}。根据学生的已有学习材料回答问题。简洁、有针对性。"},
                        {"role": "user", "content": f"学生已有的学习材料:\n{ctx[:3000]}\n\n学生问: {cmd}"},
                    ],
                    max_tokens=1000, temperature=0.7,
                )
                print(f"\n🤖 {resp.choices[0].message.content}")
        except Exception as e:
            print(f"  ⚠️ {e}")


def main():
    args = parse_args()
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    # 如果指定了岗位，直接生成（不启动服务）
    if args.position:
        raw = load_json(args.data) if args.data else None
        c = SkillTrainerCoordinator()
        c.output_dir = Path(output_dir)
        c.run_full(args.position, args.name, args.level, raw)
        return

    # 默认启动 API + 前端服务
    print("\n" + "=" * 50)
    print("🎓 学练测一体化能力提升系统 v2.0")
    print("=" * 50)

    # 启动API服务
    start_api_server(args.port)

    # 启动前端（除非指定 --no-frontend）
    if not args.no_frontend:
        start_frontend()

    print("\n" + "=" * 50)
    print("🌐 系统已启动:")
    print(f"   后端API: http://localhost:{args.port}")
    if not args.no_frontend:
        print(f"   前端界面: http://localhost:5173")
    print(f"   API文档: http://localhost:{args.port}/docs")
    print("=" * 50)
    print("\n按 Ctrl+C 停止所有服务\n")

    # 保持主线程运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")


if __name__ == "__main__":
    main()
