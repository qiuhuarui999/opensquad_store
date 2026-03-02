"""
git_helper/tools.py

Git 工作流助手工具实现（只读）。
所有操作仅读取 Git 仓库信息，不执行任何写操作。
"""
import os
import subprocess
from typing import Optional


def _run_git(args: list[str], cwd: Optional[str] = None) -> tuple[str, str, int]:
    """执行 git 命令，返回 (stdout, stderr, returncode)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "", "git 未安装或不在 PATH 中", 1
    except subprocess.TimeoutExpired:
        return "", "git 命令超时", 1


def git_status(repo_path: Optional[str] = None) -> dict:
    """
    查看工作区和暂存区状态。

    Args:
        repo_path: Git 仓库根目录，默认当前目录

    Returns:
        {"branch": str, "staged": [...], "unstaged": [...], "untracked": [...], "raw": str}
    """
    stdout, stderr, code = _run_git(["status", "--porcelain", "-b"], cwd=repo_path)
    if code != 0:
        print(f"[GIT STATUS ERROR] {stderr}")
        return {"error": stderr}

    lines = stdout.splitlines()
    branch_line = lines[0] if lines else ""
    branch = branch_line.lstrip("## ").split("...")[0] if branch_line.startswith("##") else "unknown"

    staged, unstaged, untracked = [], [], []
    for line in lines[1:]:
        if len(line) < 2:
            continue
        index_status = line[0]
        work_status  = line[1]
        path         = line[3:].strip()

        if index_status == "?" and work_status == "?":
            untracked.append(path)
        else:
            if index_status not in (" ", "?"):
                staged.append(f"{index_status}  {path}")
            if work_status not in (" ", "?"):
                unstaged.append(f"{work_status}  {path}")

    full_out, _, _ = _run_git(["status"], cwd=repo_path)

    print(f"[GIT STATUS]")
    print(f"  分支: {branch}")
    if staged:
        print("  暂存区:")
        for s in staged:
            print(f"    {s}")
    if unstaged:
        print("  工作区（未暂存）:")
        for s in unstaged:
            print(f"    {s}")
    if untracked:
        print("  未跟踪:")
        for s in untracked[:10]:
            print(f"    {s}")
        if len(untracked) > 10:
            print(f"    ...（共 {len(untracked)} 个）")

    return {
        "branch": branch,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "raw": full_out,
    }


def git_diff(
    staged: bool = False,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    file: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> dict:
    """
    查看差异。

    Args:
        staged:    True 查看暂存区差异（等同 git diff --cached）
        from_ref:  起始 ref（如 HEAD~3、main），与 to_ref 配合使用
        to_ref:    结束 ref（如 HEAD、feat/xxx）
        file:      只查看指定文件的差异
        repo_path: Git 仓库根目录

    Returns:
        {"diff": str, "files_changed": int, "insertions": int, "deletions": int}
    """
    args = ["diff"]
    if staged:
        args.append("--cached")
    if from_ref and to_ref:
        args += [f"{from_ref}..{to_ref}"]
    elif from_ref:
        args.append(from_ref)
    if file:
        args += ["--", file]

    stdout, stderr, code = _run_git(args, cwd=repo_path)
    if code != 0:
        return {"error": stderr}

    # 统计变更
    stat_args = args.copy()
    stat_args.insert(1, "--stat")
    stat_out, _, _ = _run_git(stat_args, cwd=repo_path)

    # 解析 stat 最后一行
    files_changed = insertions = deletions = 0
    if stat_out:
        last_line = stat_out.splitlines()[-1]
        m_f = __import__("re").search(r"(\d+) file", last_line)
        m_i = __import__("re").search(r"(\d+) insertion", last_line)
        m_d = __import__("re").search(r"(\d+) deletion", last_line)
        if m_f: files_changed = int(m_f.group(1))
        if m_i: insertions    = int(m_i.group(1))
        if m_d: deletions     = int(m_d.group(1))

    label = "暂存区" if staged else ("提交间" if from_ref else "工作区")
    print(f"[GIT DIFF] {label}  {files_changed} 文件变更  +{insertions} -{deletions}")
    if stdout:
        # 只打印前 60 行避免过长
        diff_lines = stdout.splitlines()
        preview = "\n".join(diff_lines[:60])
        if len(diff_lines) > 60:
            preview += f"\n... （共 {len(diff_lines)} 行，已截断）"
        print(preview)

    return {
        "diff": stdout,
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def git_log(
    limit: int = 10,
    author: Optional[str] = None,
    file: Optional[str] = None,
    since: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> dict:
    """
    查看提交历史。

    Args:
        limit:     最多显示条数，默认 10
        author:    按作者名过滤（模糊匹配）
        file:      只显示涉及该文件的提交
        since:     时间过滤，如 "2 days ago"、"2025-01-01"
        repo_path: Git 仓库根目录

    Returns:
        {"commits": [{"hash": str, "subject": str, "author": str, "date": str}]}
    """
    args = [
        "log",
        f"--max-count={limit}",
        "--pretty=format:%H\x1f%s\x1f%an\x1f%ar",
    ]
    if author:
        args.append(f"--author={author}")
    if since:
        args.append(f"--since={since}")
    if file:
        args += ["--", file]

    stdout, stderr, code = _run_git(args, cwd=repo_path)
    if code != 0:
        return {"error": stderr}

    commits = []
    print(f"[GIT LOG] 最近 {limit} 条提交")
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 3)
        if len(parts) == 4:
            h, subject, author_name, date = parts
            commits.append({
                "hash": h[:7],
                "full_hash": h,
                "subject": subject,
                "author": author_name,
                "date": date,
            })
            print(f"  {h[:7]}  {subject[:50]:<50}  {author_name:<12}  {date}")

    return {"commits": commits}


def git_branches(include_remote: bool = False, repo_path: Optional[str] = None) -> dict:
    """
    列出分支信息。

    Args:
        include_remote: 是否包含远程分支
        repo_path:      Git 仓库根目录

    Returns:
        {"current": str, "local": [...], "remote": [...]}
    """
    args = ["branch", "-v"]
    if include_remote:
        args.append("-a")

    stdout, stderr, code = _run_git(args, cwd=repo_path)
    if code != 0:
        return {"error": stderr}

    current = ""
    local, remote = [], []
    for line in stdout.splitlines():
        is_current = line.startswith("*")
        name = line[2:].split()[0] if len(line) > 2 else ""
        if is_current:
            current = name
        if name.startswith("remotes/"):
            remote.append(name)
        else:
            local.append(name)

    print(f"[GIT BRANCHES]  当前: {current}")
    print(f"  本地分支 ({len(local)}): {', '.join(local[:10])}")
    if include_remote and remote:
        print(f"  远程分支 ({len(remote)}): {', '.join(remote[:10])}")

    return {"current": current, "local": local, "remote": remote}


def git_blame(file: str, lines: Optional[tuple] = None, repo_path: Optional[str] = None) -> dict:
    """
    查看文件每行的最后修改信息。

    Args:
        file:      文件路径
        lines:     行范围元组 (start, end)，如 (40, 60)
        repo_path: Git 仓库根目录

    Returns:
        {"blame": [{"line": int, "hash": str, "author": str, "date": str, "content": str}]}
    """
    args = ["blame", "--porcelain"]
    if lines:
        args += [f"-L{lines[0]},{lines[1]}"]
    args.append(file)

    stdout, stderr, code = _run_git(args, cwd=repo_path)
    if code != 0:
        return {"error": stderr}

    # 解析 porcelain 格式
    blame_entries = []
    lines_data: dict = {}
    current_hash = ""
    line_num = 0

    for line in stdout.splitlines():
        if not line:
            continue
        if re.match(r"^[0-9a-f]{40}", line):
            parts = line.split()
            current_hash = parts[0][:7]
            line_num = int(parts[2]) if len(parts) >= 3 else 0
            if current_hash not in lines_data:
                lines_data[current_hash] = {}
        elif line.startswith("author "):
            lines_data[current_hash]["author"] = line[7:]
        elif line.startswith("author-time "):
            import datetime
            ts = int(line[12:])
            lines_data[current_hash]["date"] = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        elif line.startswith("\t"):
            blame_entries.append({
                "line": line_num,
                "hash": current_hash,
                "author": lines_data.get(current_hash, {}).get("author", "?"),
                "date": lines_data.get(current_hash, {}).get("date", "?"),
                "content": line[1:],
            })

    print(f"[GIT BLAME] {file}" + (f" L{lines[0]}-{lines[1]}" if lines else ""))
    for entry in blame_entries[:20]:
        print(f"  L{entry['line']:4}  {entry['hash']}  {entry['author']:<12}  {entry['date']}  {entry['content'][:60]}")
    if len(blame_entries) > 20:
        print(f"  ... （共 {len(blame_entries)} 行）")

    return {"blame": blame_entries}


def git_show(ref: str, repo_path: Optional[str] = None) -> dict:
    """
    查看指定提交的详细内容。

    Args:
        ref:       提交 hash 或 ref（如 HEAD、v1.0.0）
        repo_path: Git 仓库根目录

    Returns:
        {"hash": str, "subject": str, "author": str, "date": str, "diff": str}
    """
    # 先获取提交元数据
    meta_out, _, code = _run_git(
        ["show", "--quiet", "--pretty=format:%H\x1f%s\x1f%an\x1f%ad", "--date=short", ref],
        cwd=repo_path,
    )
    if code != 0:
        return {"error": f"找不到提交: {ref}"}

    parts = meta_out.split("\x1f", 3)
    h, subject, author_name, date = (parts + [""] * 4)[:4]

    diff_out, _, _ = _run_git(["show", "--stat", ref], cwd=repo_path)

    print(f"[GIT SHOW] {h[:7]}  {subject}")
    print(f"  作者: {author_name}  日期: {date}")
    diff_lines = diff_out.splitlines()
    for line in diff_lines[-20:]:
        print(f"  {line}")

    return {
        "hash": h[:7],
        "full_hash": h,
        "subject": subject,
        "author": author_name,
        "date": date,
        "diff": diff_out,
    }


import re  # noqa: E402 (placed here to avoid shadowing built-in in function scope above)
