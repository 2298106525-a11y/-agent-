"""
学练测一体化能力提升系统 - 数据库模块

使用 SQLite 存储学生数据，替代前端 localStorage
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import config

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "skill_trainer.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        -- 学生表
        CREATE TABLE IF NOT EXISTS students (
            name TEXT PRIMARY KEY,
            position TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT '初级',
            current_step INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- 学生结果数据（LLM 生成的完整数据）
        CREATE TABLE IF NOT EXISTS student_results (
            name TEXT PRIMARY KEY REFERENCES students(name) ON DELETE CASCADE,
            result_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- 学生进度（已完成的学习模块和训练任务）
        CREATE TABLE IF NOT EXISTS student_progress (
            name TEXT NOT NULL REFERENCES students(name) ON DELETE CASCADE,
            item_type TEXT NOT NULL,  -- 'learning' 或 'training'
            item_id TEXT NOT NULL,
            completed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (name, item_type, item_id)
        );

        -- 学生考核成绩
        CREATE TABLE IF NOT EXISTS student_test_scores (
            name TEXT PRIMARY KEY REFERENCES students(name) ON DELETE CASCADE,
            score INTEGER NOT NULL DEFAULT 0,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        -- 对话历史（伴学助手持久化）
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_chat_messages_name ON chat_messages(name, id);

        -- 对话摘要（长期记忆）
        CREATE TABLE IF NOT EXISTS chat_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            summary TEXT NOT NULL,
            msg_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_chat_summaries_name ON chat_summaries(name, id);

        -- 学生结构化记忆
        CREATE TABLE IF NOT EXISTS student_memory (
            name TEXT PRIMARY KEY,
            preferences TEXT NOT NULL DEFAULT '{}',
            weak_points TEXT NOT NULL DEFAULT '[]',
            topics TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.commit()
    conn.close()


# ============ 学生操作 ============

def get_student(name: str) -> Optional[Dict[str, Any]]:
    """获取学生基本信息"""
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_or_update_student(name: str, position: str = "", level: str = "初级", current_step: int = 0):
    """创建或更新学生"""
    conn = get_db()
    conn.execute("""
        INSERT INTO students (name, position, level, current_step, updated_at)
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET
            position = COALESCE(NULLIF(excluded.position, ''), students.position),
            level = excluded.level,
            current_step = excluded.current_step,
            updated_at = datetime('now', 'localtime')
    """, (name, position, level, current_step))
    conn.commit()
    conn.close()


def list_students() -> List[Dict[str, Any]]:
    """列出所有学生"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM students ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_student(name: str):
    """删除学生及其所有数据"""
    conn = get_db()
    conn.execute("DELETE FROM students WHERE name = ?", (name,))
    conn.commit()
    conn.close()


# ============ 结果数据操作 ============

def get_result(name: str) -> Optional[Dict[str, Any]]:
    """获取学生的 LLM 生成结果"""
    conn = get_db()
    row = conn.execute("SELECT result_json FROM student_results WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["result_json"])
        except json.JSONDecodeError:
            return None
    return None


def save_result(name: str, result: Dict[str, Any]):
    """保存学生的 LLM 生成结果"""
    conn = get_db()
    # 确保学生存在
    conn.execute("""
        INSERT INTO students (name, updated_at) VALUES (?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET updated_at = datetime('now', 'localtime')
    """, (name,))
    conn.execute("""
        INSERT INTO student_results (name, result_json, updated_at)
        VALUES (?, ?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET
            result_json = excluded.result_json,
            updated_at = datetime('now', 'localtime')
    """, (name, json.dumps(result, ensure_ascii=False)))
    conn.commit()
    conn.close()


# ============ 进度操作 ============

def get_progress(name: str) -> Dict[str, Any]:
    """获取学生的完成进度"""
    conn = get_db()
    rows = conn.execute(
        "SELECT item_type, item_id FROM student_progress WHERE name = ?", (name,)
    ).fetchall()
    conn.close()
    result = {"learning": {}, "training": {}}
    for row in rows:
        result[row["item_type"]][row["item_id"]] = True
    return result


def toggle_progress(name: str, item_type: str, item_id: str):
    """切换学习模块或训练任务的完成状态"""
    conn = get_db()
    # 确保学生存在
    conn.execute("""
        INSERT INTO students (name, updated_at) VALUES (?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET updated_at = datetime('now', 'localtime')
    """, (name,))
    existing = conn.execute(
        "SELECT 1 FROM student_progress WHERE name = ? AND item_type = ? AND item_id = ?",
        (name, item_type, item_id)
    ).fetchone()
    if existing:
        conn.execute(
            "DELETE FROM student_progress WHERE name = ? AND item_type = ? AND item_id = ?",
            (name, item_type, item_id)
        )
    else:
        conn.execute(
            "INSERT INTO student_progress (name, item_type, item_id) VALUES (?, ?, ?)",
            (name, item_type, item_id)
        )
    conn.commit()
    conn.close()


# ============ 考核成绩操作 ============

def get_test_score(name: str) -> Optional[Dict[str, Any]]:
    """获取学生的考核成绩"""
    conn = get_db()
    row = conn.execute("SELECT * FROM student_test_scores WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_test_score(name: str, score: int, correct: int, total: int):
    """保存学生的考核成绩"""
    conn = get_db()
    # 确保学生存在
    conn.execute("""
        INSERT INTO students (name, updated_at) VALUES (?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET updated_at = datetime('now', 'localtime')
    """, (name,))
    conn.execute("""
        INSERT INTO student_test_scores (name, score, correct, total, updated_at)
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET
            score = excluded.score,
            correct = excluded.correct,
            total = excluded.total,
            updated_at = datetime('now', 'localtime')
    """, (name, score, correct, total))
    conn.commit()
    conn.close()


# ============ 对话记忆操作 ============

def save_chat_message(name: str, role: str, content: str):
    """保存一条对话消息"""
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_messages (name, role, content) VALUES (?, ?, ?)",
        (name, role, content)
    )
    conn.commit()
    conn.close()


def get_recent_messages(name: str, limit: int = 20) -> List[Dict[str, str]]:
    """获取最近 N 条对话消息"""
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE name = ? ORDER BY id DESC LIMIT ?",
        (name, limit)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_chat_message_count(name: str) -> int:
    """获取对话消息总数"""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM chat_messages WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def save_chat_summary(name: str, summary: str, msg_count: int):
    """保存对话摘要"""
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_summaries (name, summary, msg_count) VALUES (?, ?, ?)",
        (name, summary, msg_count)
    )
    conn.commit()
    conn.close()


def get_latest_summary(name: str) -> Optional[Dict[str, Any]]:
    """获取最新的对话摘要"""
    conn = get_db()
    row = conn.execute(
        "SELECT summary, msg_count FROM chat_summaries WHERE name = ? ORDER BY id DESC LIMIT 1",
        (name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_memory(name: str) -> Dict[str, Any]:
    """获取学生结构化记忆"""
    conn = get_db()
    row = conn.execute("SELECT * FROM student_memory WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row:
        return {
            "preferences": json.loads(row["preferences"]),
            "weak_points": json.loads(row["weak_points"]),
            "topics": json.loads(row["topics"]),
        }
    return {"preferences": {}, "weak_points": [], "topics": []}


def update_student_memory(name: str, memory: Dict[str, Any]):
    """更新学生结构化记忆"""
    conn = get_db()
    conn.execute("""
        INSERT INTO student_memory (name, preferences, weak_points, topics, updated_at)
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(name) DO UPDATE SET
            preferences = excluded.preferences,
            weak_points = excluded.weak_points,
            topics = excluded.topics,
            updated_at = datetime('now', 'localtime')
    """, (
        name,
        json.dumps(memory.get("preferences", {}), ensure_ascii=False),
        json.dumps(memory.get("weak_points", []), ensure_ascii=False),
        json.dumps(memory.get("topics", []), ensure_ascii=False),
    ))
    conn.commit()
    conn.close()


def clear_chat_history(name: str):
    """清空学生的对话历史和摘要"""
    conn = get_db()
    conn.execute("DELETE FROM chat_messages WHERE name = ?", (name,))
    conn.execute("DELETE FROM chat_summaries WHERE name = ?", (name,))
    conn.commit()
    conn.close()


# ============ 完整数据加载 ============

def load_student_full(name: str) -> Dict[str, Any]:
    """加载学生的完整数据（用于前端一次性加载）"""
    student = get_student(name)
    result = get_result(name)
    progress = get_progress(name)
    test_score = get_test_score(name)

    return {
        "student": student,
        "result": result,
        "currentStep": student["current_step"] if student else 0,
        "completedItems": {
            "learning": progress.get("learning", {}),
            "training": progress.get("training", {}),
            "testScore": test_score["score"] if test_score else None,
            "testCorrect": test_score["correct"] if test_score else None,
            "testTotal": test_score["total"] if test_score else None,
        }
    }


# 初始化
init_db()
