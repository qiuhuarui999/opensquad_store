"""
api_tester/tools.py

API 接口测试工具实现。
支持单个请求发送、响应断言、批量测试套件执行和模板变量替换。
"""
import json
import re
import time
from typing import Any, Optional
try:
    import httpx
    _HTTP_CLIENT = "httpx"
except ImportError:
    import urllib.request
    import urllib.error
    _HTTP_CLIENT = "urllib"

# 全局模板变量存储
_variables: dict[str, Any] = {}

# 最近一次响应（供 assert_response 使用）
_last_response: Optional[dict] = None


def send_request(
    method: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    body: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """
    发送 HTTP 请求。

    Args:
        method:     HTTP 方法（GET / POST / PUT / DELETE / PATCH）
        url:        请求地址，支持 {{variable}} 模板变量
        headers:    请求头字典，值支持 {{variable}}
        params:     URL 查询参数
        json_body:  JSON 请求体（dict），与 body 二选一
        body:       原始字符串请求体
        timeout:    超时秒数，默认 30

    Returns:
        {"status": int, "headers": dict, "body": str, "json": dict|None, "elapsed_ms": int}
    """
    global _last_response

    url     = _render(url)
    headers = {k: _render(str(v)) for k, v in (headers or {}).items()}

    start = time.time()
    try:
        if _HTTP_CLIENT == "httpx":
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.request(
                    method.upper(), url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    content=body.encode() if body else None,
                )
            elapsed_ms = int((time.time() - start) * 1000)
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = None

            result = {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
                "json": resp_json,
                "elapsed_ms": elapsed_ms,
            }
        else:
            # fallback: urllib
            import urllib.request as _ur
            req_headers = headers or {}
            if json_body is not None:
                data = json.dumps(json_body).encode()
                req_headers.setdefault("Content-Type", "application/json")
            elif body is not None:
                data = body.encode()
            else:
                data = None

            req = _ur.Request(url, data=data, headers=req_headers, method=method.upper())
            with _ur.urlopen(req, timeout=timeout) as resp:
                elapsed_ms = int((time.time() - start) * 1000)
                resp_body = resp.read().decode("utf-8", errors="replace")
                try:
                    resp_json = json.loads(resp_body)
                except Exception:
                    resp_json = None
                result = {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": resp_body,
                    "json": resp_json,
                    "elapsed_ms": elapsed_ms,
                }

        _last_response = result
        print(f"[REQUEST] {method.upper()} {url}")
        print(f"  状态: {result['status']}  耗时: {result['elapsed_ms']}ms")
        return result

    except Exception as e:
        print(f"[REQUEST ERROR] {method.upper()} {url}: {e}")
        return {"error": str(e)}


def assert_response(
    status: Optional[int] = None,
    json_path: Optional[str] = None,
    not_empty: bool = False,
    equals: Any = None,
    contains: Optional[str] = None,
    max_ms: Optional[int] = None,
    response: Optional[dict] = None,
) -> dict:
    """
    对最近一次请求（或指定 response）进行断言。

    Args:
        status:    期望状态码
        json_path: JSON 路径（简化版，如 $.token 或 $.data.id）
        not_empty: json_path 对应的值不为空
        equals:    json_path 对应的值等于此值
        contains:  响应体包含此字符串
        max_ms:    响应时间不超过此毫秒数
        response:  指定响应字典（默认使用最近一次请求结果）

    Returns:
        {"passed": bool, "assertions": [{"name": str, "passed": bool, "detail": str}]}
    """
    resp = response or _last_response
    if resp is None:
        return {"error": "没有可断言的响应，请先调用 send_request()"}

    assertions = []

    if status is not None:
        ok = resp.get("status") == status
        assertions.append({
            "name": f"状态码 == {status}",
            "passed": ok,
            "detail": f"实际: {resp.get('status')}",
        })

    if json_path is not None:
        value = _get_json_path(resp.get("json"), json_path)
        if not_empty:
            ok = value is not None and value != "" and value != [] and value != {}
            assertions.append({
                "name": f"{json_path} 不为空",
                "passed": ok,
                "detail": f"实际值: {value}",
            })
        if equals is not None:
            ok = value == equals
            assertions.append({
                "name": f"{json_path} == {equals}",
                "passed": ok,
                "detail": f"实际值: {value}",
            })

    if contains is not None:
        ok = contains in (resp.get("body") or "")
        assertions.append({
            "name": f"响应体包含 '{contains}'",
            "passed": ok,
            "detail": "" if ok else "未找到",
        })

    if max_ms is not None:
        elapsed = resp.get("elapsed_ms", 0)
        ok = elapsed <= max_ms
        assertions.append({
            "name": f"响应时间 <= {max_ms}ms",
            "passed": ok,
            "detail": f"实际: {elapsed}ms",
        })

    all_passed = all(a["passed"] for a in assertions)
    for a in assertions:
        icon = "✅" if a["passed"] else "❌"
        print(f"  {icon} {a['name']}  {a['detail']}")

    return {"passed": all_passed, "assertions": assertions}


def set_variable(name: str, value: Any) -> None:
    """
    设置模板变量，后续请求中用 {{name}} 引用。

    Args:
        name:  变量名
        value: 变量值
    """
    _variables[name] = value
    print(f"[VAR] {name} = {value}")


def run_test_suite(suite_path: str) -> dict:
    """
    加载 JSON 测试套件文件，批量执行所有测试用例。

    Args:
        suite_path: JSON 测试套件文件路径

    Returns:
        {"total": int, "passed": int, "failed": int, "results": [...]}
    """
    try:
        with open(suite_path, encoding="utf-8") as f:
            suite = json.load(f)
    except Exception as e:
        return {"error": f"加载测试套件失败: {e}"}

    suite_name = suite.get("name", suite_path)
    base_url   = suite.get("base_url", "")
    variables  = suite.get("variables", {})
    cases      = suite.get("cases", [])

    # 注入套件级变量
    for k, v in variables.items():
        set_variable(k, v)

    print(f"\n[TEST SUITE] {suite_name} ({len(cases)} cases)")

    results = []
    for case in cases:
        case_id   = case.get("id", "?")
        case_name = case.get("name", "")
        url       = base_url + case.get("path", "")
        method    = case.get("method", "GET")
        headers   = case.get("headers", {})
        json_body = case.get("body")
        asserts   = case.get("asserts", [])

        resp = send_request(method, url, headers=headers, json_body=json_body)

        case_assertions = []
        all_ok = True
        for a in asserts:
            atype = a.get("type")
            if atype == "status":
                ok = resp.get("status") == a.get("expect")
            elif atype == "json_path":
                value = _get_json_path(resp.get("json"), a.get("path", ""))
                if a.get("not_empty"):
                    ok = value is not None and value != ""
                elif "equals" in a:
                    ok = value == a["equals"]
                else:
                    ok = value is not None
            elif atype == "response_time_ms":
                ok = resp.get("elapsed_ms", 0) <= a.get("max", 5000)
            else:
                ok = True

            case_assertions.append({"type": atype, "passed": ok})
            if not ok:
                all_ok = False

        icon = "✅" if all_ok else "❌"
        elapsed = resp.get("elapsed_ms", "?")
        status  = resp.get("status", "?")
        print(f"  {icon} {case_id}  {case_name:<24} {status}  {elapsed}ms")

        results.append({
            "id": case_id,
            "name": case_name,
            "passed": all_ok,
            "status": status,
            "elapsed_ms": elapsed,
            "assertions": case_assertions,
        })

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    print(f"\n结果: {passed}/{len(results)} 通过  失败: {failed}")

    return {"total": len(results), "passed": passed, "failed": failed, "results": results}


# ── 内部辅助 ──────────────────────────────────────────────────────────────────

def _render(text: str) -> str:
    """将 {{variable}} 替换为实际值"""
    def replace(m):
        key = m.group(1).strip()
        return str(_variables.get(key, m.group(0)))
    return re.sub(r"\{\{(\w+)\}\}", replace, text)


def _get_json_path(data: Any, path: str) -> Any:
    """简化版 JSON Path（支持 $.a.b.c 格式）"""
    if data is None:
        return None
    path = path.lstrip("$").lstrip(".")
    parts = path.split(".") if path else []
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current
