import hashlib
import hmac
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PAYMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "payments.json")
# RLock: fulfill_payment_once가 잠금을 쥔 채 apply_fn을 호출하므로 재진입 가능해야 한다.
_lock = threading.RLock()

CREDIT_PACKAGES = {
    "small":  {"credits": 10,  "price": 20000,  "name": "소형"},
    "medium": {"credits": 30,  "price": 54000,  "name": "중형"},
    "large":  {"credits": 100, "price": 160000, "name": "대형"},
}

PLAN_PRICES = {
    "Pro":      29000,
    "Advanced": 79000,
}


def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    # fail-closed: 시크릿 미설정 시 어떤 웹훅도 신뢰하지 않는다
    secret = os.environ.get("TOSS_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _load() -> list:
    """원장 읽기. 파일 없음은 부트스트랩, 손상은 실패 처리한다.

    손상된 원장을 빈 목록으로 취급하면 이미 이행된 order_id가 전부 재이행
    가능해진다 (docs/LESSONS.md L016). 예외를 그대로 올려 웹훅이 5xx가 되면
    Toss가 재전송하므로, 운영자가 파일을 복구한 뒤 정상 처리된다.
    """
    try:
        with open(PAYMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    if not isinstance(data, list):
        raise ValueError(f"payments ledger is not a list: {type(data).__name__}")
    return data


def _save(data: list) -> None:
    # 원자적 + 내구성 있는 교체: 임시 파일에 쓰고 fsync한 뒤 os.replace.
    directory = os.path.dirname(PAYMENTS_PATH)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".payments-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, PAYMENTS_PATH)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def fulfill_payment_once(
    *,
    order_id: str,
    user_id: str,
    product_type: str,
    package: str | None,
    plan: str | None,
    amount: int,
    status: str = "DONE",
    apply_fn,
) -> dict:
    """Apply credit/plan side effect at most once per order_id.

    Holds the payments lock across check → apply → record so concurrent
    Toss webhook retries cannot double-charge.

    DONE 행은 종결이다 — 재전송은 duplicate로 흡수한다. NEEDS_REVIEW 행은
    종결이 아니다: 검증을 통과한 재전송(status="DONE")이 오면 그때 이행하고
    같은 행을 DONE으로 승격한다. 그러지 않으면 값이 틀렸다가 정정된 정상
    결제가 영원히 미이행 상태로 남는다.
    """
    if not order_id:
        raise ValueError("order_id_required")
    with _lock:
        data = _load()
        existing = next((r for r in data if r.get("order_id") == order_id), None)
        if existing is not None:
            existing_status = existing.get("status")
            if existing_status != "NEEDS_REVIEW":
                return {"status": "ok", "duplicate": True}
            if status != "DONE":
                logger.warning(
                    f"[payment] NEEDS_REVIEW replay blocked order_id={order_id!r} "
                    f"— 검토 대기 중인 주문이라 이행하지 않는다"
                )
                return {
                    "status": "ok",
                    "duplicate": True,
                    "blocked_by": "NEEDS_REVIEW",
                }
            # 검증을 통과한 재전송 — 이제 이행하고 기존 행을 승격한다.
            apply_fn()
            existing.update(
                {
                    "user_id": user_id,
                    "product_type": product_type,
                    "package": package,
                    "plan": plan,
                    "amount": amount,
                    "status": "DONE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            _save(data)
            logger.warning(
                f"[payment] NEEDS_REVIEW recovered → DONE order_id={order_id!r}"
            )
            return {"status": "ok", "duplicate": False, "recovered": True}
        apply_fn()
        data.append(
            {
                "user_id": user_id,
                "product_type": product_type,
                "package": package,
                "plan": plan,
                "amount": amount,
                "status": status,
                "order_id": order_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        _save(data)
        return {"status": "ok", "duplicate": False}


def get_payment_history(user_id: str | None = None) -> list:
    with _lock:
        data = _load()
    if user_id is None:
        return data
    return [r for r in data if r.get("user_id") == user_id]
