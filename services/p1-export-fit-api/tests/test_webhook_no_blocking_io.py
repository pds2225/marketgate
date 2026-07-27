"""웹훅 핸들러는 이벤트 루프를 막지 않아야 한다 (구조적 가드).

Toss는 10초 안에 2xx를 받지 못하면 실패로 간주하고 재전송한다. 핸들러가
`async def`인 채로 동기 파일 I/O를 호출하면 이벤트 루프 전체가 멈춰
/health 까지 함께 지연된다 — 그래서 저장소 접근은 전부 run_in_threadpool로
넘겨야 한다.

타이밍 단언은 불안정하므로 구조(AST)만 검사한다:
  1. 엔드포인트는 async def를 유지한다
  2. webhook 자체 스코프에서 저장소를 건드리는 호출은 모두 run_in_threadpool 경유
     (콜백으로 넘긴 클로저 내부는 호출자 컨텍스트를 상속하므로 제외)
  3. run_in_threadpool에 넘기는 함수는 반드시 동기 함수
     — async 함수를 넘기면 await되지 않은 코루틴이 반환되어 핸들러가
       아무 일도 하지 않고 200을 돌려주며 결제를 전부 유실한다
"""
from __future__ import annotations

import ast
import pathlib

import app.routers.payment as payment_router

# 디스크를 건드리는 함수들 (직접·간접)
BLOCKING = {
    "fulfill_payment_once", "charge", "change_plan", "get_payment_history",
    "record_payment", "find_user_by_id", "find_user_by_email",
    "get_balance", "get_subscription", "deduct", "open",
}


def _tree():
    src = pathlib.Path(payment_router.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent
    return tree


def _callee(node: ast.Call):
    f = node.func
    return getattr(f, "id", None) or getattr(f, "attr", None)


def _funcs(tree):
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _tainted(tree):
    """저장소를 전이적으로 건드리는 함수 이름 집합."""
    funcs, tainted = _funcs(tree), set(BLOCKING)
    for _ in range(6):
        for name, node in funcs.items():
            if name in tainted:
                continue
            if any(_callee(c) in tainted
                   for c in ast.walk(node) if isinstance(c, ast.Call)):
                tainted.add(name)
    return tainted


def _own_scope_calls(fn):
    """중첩 함수 본문을 제외한, fn 자체 스코프의 호출."""
    out, stack = [], list(fn.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(n, ast.Call):
            out.append(n)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _under_threadpool(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, ast.Call) and _callee(cur) == "run_in_threadpool":
            return True
        cur = getattr(cur, "parent", None)
    return False


def test_webhook_endpoint_stays_async():
    fn = _funcs(_tree())["webhook"]
    assert isinstance(fn, ast.AsyncFunctionDef), (
        "webhook must stay `async def`; a sync def would be run in Starlette's "
        "threadpool and silently change the concurrency model"
    )


def test_no_blocking_store_call_on_the_event_loop():
    tree = _tree()
    fn = _funcs(tree)["webhook"]
    tainted = _tainted(tree)
    unwrapped = sorted(
        (_callee(c), c.lineno)
        for c in _own_scope_calls(fn)
        if _callee(c) in tainted and not _under_threadpool(c)
    )
    assert unwrapped == [], (
        f"blocking store access on the event loop: {unwrapped}. "
        "Wrap it: await run_in_threadpool(fn, ...)"
    )


def test_functions_sent_to_threadpool_are_sync():
    tree = _tree()
    funcs = _funcs(tree)
    offenders = []
    for call in ast.walk(funcs["webhook"]):
        if isinstance(call, ast.Call) and _callee(call) == "run_in_threadpool":
            for arg in call.args:
                name = getattr(arg, "id", None) or getattr(arg, "attr", None)
                node = funcs.get(name)
                if isinstance(node, ast.AsyncFunctionDef):
                    offenders.append((name, call.lineno))
    assert offenders == [], (
        f"async function handed to run_in_threadpool: {offenders}. "
        "It returns an un-awaited coroutine — the handler would do nothing, "
        "return 200, and drop every payment."
    )
