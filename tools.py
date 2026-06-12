"""
学练测一体化能力提升系统 - 工具模块

提供JSON解析、文件操作等通用工具函数
"""

import json
import re
from typing import Optional, Dict, Any


class JSONParser:
    """JSON解析工具 - 从LLM输出中提取JSON"""

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取JSON对象

        Args:
            text: 包含JSON的文本

        Returns:
            解析后的字典，失败返回None
        """
        if not text or not text.strip():
            return None

        # 先去掉 <think>...</think> 标签（qwen3 模型输出）
        original_len = len(text)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = text.strip()

        if not text:
            print(f"  ⚠️ 去掉<think>标签后为空，原始长度{original_len}")
            return None

        # 尝试多种方式提取 JSON
        candidates = []

        # 1. 查找 ```json ... ``` 代码块
        for m in re.finditer(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL):
            candidates.append(m.group(1).strip())

        # 2. 查找所有 { ... } 块（按长度从长到短）
        brace_matches = list(re.finditer(r'\{[\s\S]*\}', text))
        for m in sorted(brace_matches, key=lambda x: len(x.group(0)), reverse=True):
            candidates.append(m.group(0))

        # 3. 整个文本作为候选
        if text.startswith('{'):
            candidates.append(text)

        # 逐个尝试解析
        for i, raw in enumerate(candidates):
            if not raw:
                continue
            result = _try_parse_json(raw)
            if result is not None:
                return result

        # 所有候选都失败，打印调试信息
        if candidates:
            c0 = candidates[0]
            print(f"  ⚠️ JSON解析失败，第1个候选长度{len(c0)}:")
            print(f"    前150字: {c0[:150]}")
            print(f"    后50字: {c0[-50:]}")
        else:
            print(f"  ⚠️ JSON解析失败，无候选，原始文本前200字: {text[:200]}")
        return None


def _try_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """尝试解析 JSON 字符串，包含多种修复策略"""
    # 清理
    raw = raw.strip()
    if not raw:
        return None

    # 去掉可能的 BOM 和零宽字符
    raw = raw.replace('﻿', '').replace('​', '').replace('‌', '').replace('‍', '')

    # 策略1: 直接解析
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError as e:
        pass

    # 策略2: 去掉注释 + 尾逗号
    try:
        cleaned = _strip_json_comments(raw)
        cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 策略3: 修复常见 LLM 输出问题
    try:
        fixed = _fix_common_json_issues(raw)
        result = json.loads(fixed)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 策略4: 尝试提取第一个完整的 JSON 对象
    try:
        depth = 0
        start = -1
        for i, ch in enumerate(raw):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    candidate = raw[start:i+1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        # 尝试修复后解析
                        try:
                            fixed = _fix_common_json_issues(candidate)
                            result = json.loads(fixed)
                            if isinstance(result, dict):
                                return result
                        except json.JSONDecodeError:
                            pass
                    start = -1
    except Exception:
        pass

    # 策略5: 修复被截断的 JSON（LLM 输出超长被截断）
    try:
        repaired = _repair_truncated_json(raw)
        if repaired:
            result = json.loads(repaired)
            if isinstance(result, dict):
                print(f"  ✅ 截断JSON修复成功")
                return result
    except (json.JSONDecodeError, Exception):
        pass

    # 策略6: 正则直接提取 tasks 数组（绕过 JSON 解析错误）
    try:
        result = _extract_tasks_by_regex(raw)
        if result and result.get("tasks"):
            print(f"  ✅ 正则提取成功: {len(result['tasks'])}个任务")
            return result
    except Exception:
        pass

    return None


def _strip_json_comments(text: str) -> str:
    """去掉 JSON 中的注释，但不影响字符串内的 // 和 /*"""
    result = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and not escape:
            in_string = not in_string
            result.append(ch)
        elif in_string:
            result.append(ch)
            escape = ch == '\\' and not escape
        elif ch == '/' and i+1 < len(text) and text[i+1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        elif ch == '/' and i+1 < len(text) and text[i+1] == '*':
            i += 2
            while i < len(text) and not (text[i] == '*' and i+1 < len(text) and text[i+1] == '/'):
                i += 1
            i += 2
            continue
        else:
            result.append(ch)
            escape = False
        i += 1
    return ''.join(result)


def _fix_common_json_issues(text: str) -> str:
    """修复 LLM 输出的常见 JSON 问题"""
    # 去掉注释
    text = _strip_json_comments(text)
    # 去掉尾逗号
    text = re.sub(r',\s*([\]}])', r'\1', text)
    # 修复单引号为双引号（但不影响字符串内的单引号）
    # 只处理键值对的单引号
    text = re.sub(r"'([^']*?)'(\s*:)", r'"\1"\2', text)
    text = re.sub(r":\s*'([^']*?)'", r': "\1"', text)
    # 修复 Python 风格的 True/False/None
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    text = re.sub(r'\bNone\b', 'null', text)
    return text


def _extract_tasks_by_regex(text: str) -> Optional[Dict[str, Any]]:
    """用正则从 LLM 输出中直接提取 tasks/questions 数组，绕过 JSON 语法错误"""
    # 提取 title
    title_m = re.search(r'"title"\s*:\s*"([^"]*)"', text)
    title = title_m.group(1) if title_m else ""

    desc_m = re.search(r'"description"\s*:\s*"([^"]*)"', text)
    description = desc_m.group(1) if desc_m else ""

    # 通用函数：提取指定 id 前缀的对象列表
    def extract_objects(id_pattern, field_map):
        items = []
        starts = [m.start() for m in re.finditer(rf'\{{\s*"id"\s*:\s*"{id_pattern}', text)]
        for start_idx in starts:
            depth = 0
            end_idx = -1
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx < 0:
                continue
            chunk = text[start_idx:end_idx + 1]
            # 尝试直接解析
            try:
                obj = json.loads(chunk)
                items.append(obj)
                continue
            except json.JSONDecodeError:
                pass
            # 正则提取各字段
            def extract_str(key):
                m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', chunk)
                return m.group(1) if m else ""
            def extract_num(key, default=0):
                m = re.search(rf'"{key}"\s*:\s*(\d+)', chunk)
                return int(m.group(1)) if m else default
            def extract_list(key):
                m = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', chunk, re.DOTALL)
                if not m:
                    return []
                return re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
            obj = {}
            for key, typ in field_map.items():
                if typ == "str":
                    obj[key] = extract_str(key)
                elif typ == "num":
                    obj[key] = extract_num(key)
                elif typ == "list":
                    obj[key] = extract_list(key)
            items.append(obj)
        return items

    # 尝试提取训练任务
    task_fields = {"id": "str", "title": "str", "description": "str", "type": "str",
                   "skill_point_id": "str", "difficulty": "str", "requirements": "list",
                   "hints": "list", "reference_solution": "str", "evaluation_criteria": "list",
                   "estimated_minutes": "num"}
    tasks = extract_objects("TASK_", task_fields)
    if tasks:
        print(f"  ✅ 正则提取成功: {len(tasks)}个任务")
        return {"title": title, "description": description, "tasks": tasks, "scenarios": []}

    # 尝试提取测试题目
    question_fields = {"id": "str", "question_type": "str", "question_text": "str",
                       "skill_point_id": "str", "difficulty": "str", "options": "list",
                       "correct_answer": "str", "explanation": "str", "score": "num", "tags": "list"}
    questions = extract_objects("Q_", question_fields)
    if questions:
        print(f"  ✅ 正则提取成功: {len(questions)}道题")
        return {"title": title, "description": description, "questions": questions}

    return None


def _repair_truncated_json(text: str) -> Optional[str]:
    """尝试修复被 LLM 截断的 JSON"""
    text = text.strip()
    if not text.startswith('{'):
        return None

    # 去掉尾部不完整的字符串值
    # 找到最后一个完整的引号对
    in_string = False
    escape = False
    last_complete_quote = -1
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            if not in_string:
                last_complete_quote = i

    # 如果字符串未闭合，截断到最后一个完整引号后
    if in_string and last_complete_quote >= 0:
        text = text[:last_complete_quote + 1]

    # 去掉尾部的逗号、冒号、不完整的值
    text = re.sub(r'[,\s:]+$', '', text)

    # 计算需要补多少个 } 和 ]
    open_braces = 0
    open_brackets = 0
    in_str = False
    esc = False
    for ch in text:
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{':
            open_braces += 1
        elif ch == '}':
            open_braces -= 1
        elif ch == '[':
            open_brackets += 1
        elif ch == ']':
            open_brackets -= 1

    # 补齐闭合符号
    if open_brackets > 0:
        text += ']' * open_brackets
    if open_braces > 0:
        text += '}' * open_braces

    # 最后再清理一下尾逗号
    text = re.sub(r',\s*([\]}])', r'\1', text)

    return text if text.startswith('{') and text.endswith('}') else None


class FileHelper:
    """文件操作工具"""

    @staticmethod
    def save_markdown(content: str, filepath: str) -> str:
        """
        从文本中提取Markdown内容

        Args:
            content: 包含Markdown的文本
            filepath: 保存路径

        Returns:
            实际保存的文件路径
        """
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    @staticmethod
    def read_file(filepath: str) -> str:
        """读取文件内容"""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()



# 全局实例
json_parser = JSONParser()
file_helper = FileHelper()
