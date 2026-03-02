"""
code_reviewer_lite/tools.py

代码审查助手工具实现。
检测 Python / TypeScript 代码中的常见坏味道、安全问题和 TODO 注释。
"""
import os
import re
import ast
from typing import Optional

# ── 坏味道规则 ────────────────────────────────────────────────────────────────

_PY_RULES = [
    # (pattern, level, message)
    (r"except\s*:", "error", "裸 except 语句，请指定异常类型"),
    (r"def\s+\w+\([^)]*=\s*\[\s*\]", "error", "可变默认参数（list），可能导致意外状态共享"),
    (r"def\s+\w+\([^)]*=\s*\{\s*\}", "error", "可变默认参数（dict），可能导致意外状态共享"),
    (r"password\s*=\s*['\"][^'\"]{4,}['\"]", "error", "疑似硬编码密码"),
    (r"secret\s*=\s*['\"][^'\"]{4,}['\"]", "error", "疑似硬编码 secret"),
    (r"api_key\s*=\s*['\"][^'\"]{4,}['\"]", "error", "疑似硬编码 API Key"),
    (r"print\(", "warning", "遗留 print 语句，生产代码建议改用 logger"),
    (r"TODO|FIXME|HACK|XXX", "info", "待办注释"),
]

_TS_RULES = [
    (r":\s*any\b", "warning", "使用了 any 类型，建议指定具体类型"),
    (r"console\.log\(", "warning", "遗留 console.log，建议移除或改用 logger"),
    (r"=\s*require\(", "warning", "使用了 CommonJS require，建议改用 ES import"),
    (r"\.then\(\s*\)\s*(?!\.catch)", "warning", "Promise .then() 缺少 .catch() 错误处理"),
    (r"password\s*=\s*['\"][^'\"]{4,}['\"]", "error", "疑似硬编码密码"),
    (r"TODO|FIXME|HACK|XXX", "info", "待办注释"),
]

_LEVEL_ICON = {"error": "🔴", "warning": "🟡", "info": "🟢"}


def review_file(path: str) -> dict:
    """
    审查单个文件，返回问题列表和复杂度信息。

    Args:
        path: 文件路径（支持 .py / .ts / .tsx）

    Returns:
        {
          "file": str,
          "issues": [{"line": int, "level": str, "message": str}],
          "complexity": int | None,
          "summary": str,
        }
    """
    if not os.path.isfile(path):
        return {"error": f"文件不存在: {path}"}

    ext = os.path.splitext(path)[1].lower()
    if ext not in (".py", ".ts", ".tsx"):
        return {"error": f"不支持的文件类型: {ext}（支持 .py / .ts / .tsx）"}

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    rules = _PY_RULES if ext == ".py" else _TS_RULES
    issues = []

    for i, line in enumerate(lines, start=1):
        for pattern, level, message in rules:
            if re.search(pattern, line):
                issues.append({"line": i, "level": level, "message": message})

    complexity = None
    if ext == ".py":
        complexity = _estimate_py_complexity(path)

    # 长函数检测（Python）
    if ext == ".py":
        func_issues = _check_long_functions(lines)
        issues.extend(func_issues)

    error_count   = sum(1 for i in issues if i["level"] == "error")
    warning_count = sum(1 for i in issues if i["level"] == "warning")
    info_count    = sum(1 for i in issues if i["level"] == "info")

    summary = f"{error_count} 个错误，{warning_count} 个警告，{info_count} 个提示"

    # 格式化输出
    output_lines = [f"[REVIEW] {path}"]
    for issue in issues:
        icon = _LEVEL_ICON.get(issue["level"], "ℹ️")
        output_lines.append(f"  {icon} L{issue['line']}  {issue['message']}")
    if complexity is not None:
        output_lines.append(f"  ℹ️  最高圈复杂度估算: {complexity}")
    output_lines.append(f"\n总计: {summary}")

    print("\n".join(output_lines))
    return {"file": path, "issues": issues, "complexity": complexity, "summary": summary}


def review_directory(path: str, extensions: Optional[list] = None) -> dict:
    """
    批量审查目录下所有支持的文件。

    Args:
        path: 目录路径
        extensions: 文件扩展名列表，默认 ['.py', '.ts', '.tsx']

    Returns:
        {"files_reviewed": int, "total_issues": int, "results": [...]}
    """
    if extensions is None:
        extensions = [".py", ".ts", ".tsx"]

    if not os.path.isdir(path):
        return {"error": f"目录不存在: {path}"}

    results = []
    for root, _, files in os.walk(path):
        # 跳过常见无关目录
        if any(skip in root for skip in ["node_modules", ".git", "__pycache__", ".venv", "dist", "build"]):
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in extensions:
                fpath = os.path.join(root, fname)
                result = review_file(fpath)
                if "error" not in result:
                    results.append(result)

    total_issues = sum(len(r["issues"]) for r in results)
    print(f"\n[REVIEW SUMMARY] 共审查 {len(results)} 个文件，发现 {total_issues} 个问题")
    return {"files_reviewed": len(results), "total_issues": total_issues, "results": results}


def find_todos(path: str) -> dict:
    """
    提取文件或目录中所有 TODO / FIXME / HACK / XXX 注释。

    Args:
        path: 文件路径或目录路径

    Returns:
        {"total": int, "items": [{"file": str, "line": int, "text": str}]}
    """
    pattern = re.compile(r"(TODO|FIXME|HACK|XXX)[:\s]*(.*)", re.IGNORECASE)
    items = []

    files = []
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        for root, _, fnames in os.walk(path):
            if any(s in root for s in ["node_modules", ".git", "__pycache__"]):
                continue
            for fname in fnames:
                if os.path.splitext(fname)[1].lower() in (".py", ".ts", ".tsx", ".js"):
                    files.append(os.path.join(root, fname))

    for fpath in files:
        with open(fpath, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                m = pattern.search(line)
                if m:
                    items.append({
                        "file": fpath,
                        "line": i,
                        "tag": m.group(1).upper(),
                        "text": m.group(2).strip(),
                    })

    print(f"[TODO SCAN] 共发现 {len(items)} 条待办注释")
    for item in items:
        print(f"  {item['tag']}  {item['file']}:{item['line']}  {item['text']}")
    return {"total": len(items), "items": items}


def estimate_complexity(path: str) -> dict:
    """
    估算 Python 文件中各函数的圈复杂度。

    Args:
        path: .py 文件路径

    Returns:
        {"functions": [{"name": str, "complexity": int, "line": int}]}
    """
    if not os.path.isfile(path) or not path.endswith(".py"):
        return {"error": "请提供有效的 .py 文件路径"}

    with open(path, encoding="utf-8", errors="replace") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"语法错误，无法解析: {e}"}

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = _calc_complexity(node)
            level = "低" if cc <= 5 else ("中等" if cc <= 10 else "高（建议重构）")
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": cc,
                "level": level,
            })

    functions.sort(key=lambda x: x["complexity"], reverse=True)
    print(f"[COMPLEXITY] {path}")
    for fn in functions:
        print(f"  {fn['name']}() L{fn['line']}  CC={fn['complexity']} ({fn['level']})")
    return {"functions": functions}


# ── 内部辅助 ──────────────────────────────────────────────────────────────────

def _estimate_py_complexity(path: str) -> Optional[int]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source)
        max_cc = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                max_cc = max(max_cc, _calc_complexity(node))
        return max_cc if max_cc > 0 else None
    except Exception:
        return None


def _calc_complexity(func_node) -> int:
    """简化版圈复杂度：1 + 分支数"""
    cc = 1
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                             ast.With, ast.Assert, ast.comprehension)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += len(node.values) - 1
    return cc


def _check_long_functions(lines: list) -> list:
    """检测超过 50 行的函数（Python 简单启发式）"""
    issues = []
    func_start = None
    func_name = ""
    indent_level = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            m = re.match(r"\s*(async\s+)?def\s+(\w+)", line)
            if m:
                if func_start is not None and (i - func_start) > 50:
                    issues.append({
                        "line": func_start,
                        "level": "warning",
                        "message": f"函数 {func_name} 共 {i - func_start} 行，建议拆分（阈值 50）",
                    })
                func_start = i
                func_name = m.group(2)
                indent_level = len(line) - len(line.lstrip())

    return issues
