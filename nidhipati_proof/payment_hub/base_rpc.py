"""Прямое чтение сети Base через публичный JSON-RPC.

Зачем. Провайдерская карта (PayGate.to) требует регистрации магазина, KYC и
callback'а — это «я пройду» для владельца. Прямой путь (покупатель сам шлёт
USDC в сеть и присылает хеш транзакции) сверяется публичной нодой: без
аккаунта, без комиссии провайдера, без третьей стороны между нами и
плательщиком. Комиссия — только сеть.

Два разных отказа, и путать их нельзя:
  * `TransferRejected` — перевод не подтверждает оплату (не тот получатель,
    мало, транзакция упала, ещё не подтверждена). Это «не оплачено».
  * `ChainUnavailable` — сеть не ответила. Это «не смогли проверить»: клиенту
    нельзя говорить «не оплачено», когда мы просто не достучались до ноды.

Публичные ноды ограничивают частоту, поэтому список нод и повтор. mainnet.base.org
отвечает 403 без браузерного User-Agent — проверено 18.10.2026 и 12.11.2026.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable

#: ERC-20 Transfer(address,address,uint256) — значение из спецификации.
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

#: USDC в сети Base (mainnet). Контрольная сумма EIP-55 сходится.
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
#: USDC в Base Sepolia — другой контракт, в сети другой адрес.
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

BASE_RPC_URLS = ("https://mainnet.base.org", "https://base-rpc.publicnode.com")
SEPOLIA_RPC_URLS = ("https://sepolia.base.org", "https://base-sepolia.publicnode.com")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)

#: fetch(url, method, params) -> dict — точка подмены в тестах.
Fetcher = Callable[[str, str, list], dict]


class ChainUnavailable(Exception):
    """Сеть не ответила. Это не «не оплачено»."""


class TransferRejected(Exception):
    """Перевод не подтверждает оплату. Причина всегда названа."""


def _default_fetch(url: str, method: str, params: list) -> dict:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 — явный список нод
        return json.loads(resp.read().decode("utf-8"))


def rpc(
    urls: Iterable[str],
    method: str,
    params: list,
    *,
    timeout: float = 20.0,
    fetch: Fetcher | None = None,
) -> Any:
    """Вызов JSON-RPC с перебором нод. Ошибка сети — ChainUnavailable."""
    call = fetch or _default_fetch
    last: Exception | None = None
    for url in urls:
        try:
            body = call(url, method, params)
        except Exception as exc:  # noqa: BLE001 — сеть может лечь на любом узле
            last = exc
            continue
        if isinstance(body, dict) and body.get("error"):
            last = RuntimeError(str(body["error"].get("message") or "rpc error"))
            continue
        if not isinstance(body, dict):
            last = RuntimeError("rpc returned a non-object body")
            continue
        return body.get("result")
    raise ChainUnavailable(f"no node answered {method}: {type(last).__name__ if last else 'no attempt'}")


def _is_tx_hash(value: str) -> bool:
    if not (value.startswith("0x") and len(value) == 66):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value[2:])


def confirm_usdc_transfer(
    tx_hash: str,
    *,
    pay_to: str,
    min_atoms: int,
    asset: str = USDC_BASE,
    rpc_urls: Iterable[str] = BASE_RPC_URLS,
    confirmations: int = 2,
    timeout: float = 20.0,
    fetch: Fetcher | None = None,
) -> dict[str, Any]:
    """Подтвердить перевод USDC на `pay_to` не меньше `min_atoms`.

    Возвращает факты из цепи: плательщик, сумма, блок, число подтверждений.
    Ничего из тела запроса не берётся — только из receipt'а транзакции.
    """
    wanted = (tx_hash or "").strip().lower()
    if not _is_tx_hash(wanted):
        raise TransferRejected("tx hash must look like 0x followed by 64 hex characters")

    receipt = rpc(rpc_urls, "eth_getTransactionReceipt", [wanted], timeout=timeout, fetch=fetch)
    if not receipt:
        raise TransferRejected("transaction not found on Base yet")
    if int(receipt.get("status") or "0x0", 16) != 1:
        raise TransferRejected("transaction failed on-chain (status 0)")

    block = int(receipt.get("blockNumber") or "0x0", 16)
    head = int(rpc(rpc_urls, "eth_blockNumber", [], timeout=timeout, fetch=fetch) or "0x0", 16)
    done = head - block + 1
    if done < confirmations:
        raise TransferRejected(f"waiting for confirmations: {done}/{confirmations}")

    want_to = (pay_to or "").lower()
    want_asset = (asset or "").lower()
    total = 0
    payer = ""
    for log in receipt.get("logs") or []:
        if (log.get("address") or "").lower() != want_asset:
            continue
        topics = log.get("topics") or []
        if len(topics) != 3 or (topics[0] or "").lower() != TRANSFER_TOPIC:
            continue
        if "0x" + str(topics[2])[-40:].lower() != want_to:
            continue
        total += int(log.get("data") or "0x0", 16)
        if not payer:
            payer = "0x" + str(topics[1])[-40:].lower()

    if total == 0:
        raise TransferRejected("no USDC transfer to the project wallet in this transaction")
    if total < min_atoms:
        raise TransferRejected(
            f"paid {total / 1_000_000:.6f} USDC, required {min_atoms / 1_000_000:.6f} USDC"
        )
    return {
        "tx_hash": wanted,
        "payer": payer,
        "amount_atoms": total,
        "amount_usdc": f"{total / 1_000_000:.6f}",
        "block": block,
        "confirmations": done,
        "asset": asset,
        "pay_to": pay_to,
    }
