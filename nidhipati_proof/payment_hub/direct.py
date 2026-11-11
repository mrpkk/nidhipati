"""Прямой рельс: USDC в сети Base, без провайдера и без KYC.

Зачем. Карточная карта (PayGate.to) требует регистрации магазина, KYC и
callback'а — это «я пройду» для владельца, и до её закрытия денег не принять.
Прямой рельс не требует ничего: покупатель сам переводит USDC в Base на адрес
проекта и присылает хеш транзакции, сервер сверяет перевод в сети. Это тот же
путь, что уже работает в `attest` (`/pay`) и в AILegal (`/api/v2/pay`) —
здесь он оформлен как адаптер хаба, чтобы рельсы не расходились.

Доказательство оплаты — цепочка, а не слово провайдера:
  * сумма и получатель читаются из receipt'а транзакции, не из тела запроса;
  * подпись провайдера тут не нужна и не притворяется: `verify_callback`
    возвращает None, а решение принимает `confirm` по данным сети;
  * транзакция, уже использованная для заказа, повторно оплатой не считается
    (идемпотентность живёт в сторе хаба).

Границы: публичные ноды могут лечь — это `ChainUnavailable` («не смогли
проверить»), а не «не оплачено». Цена в заказе — в долларах, актив USDC
считается один к одному; это допущение записано в `PAYMENT_HUB_ASSET` и
`PAYMENT_HUB_NETWORK` по умолчанию.
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

from .base_rpc import (
    BASE_RPC_URLS,
    SEPOLIA_RPC_URLS,
    USDC_BASE,
    USDC_BASE_SEPOLIA,
    ChainUnavailable,
    TransferRejected,
    confirm_usdc_transfer,
)
from .models import (
    CreatePaymentRequest,
    CreatePaymentResult,
    PaymentEvent,
    PaymentPolicy,
    PaymentStatus,
    ProviderRef,
)
from .policy import evaluate_policy

#: Сеть и актив по умолчанию — Base mainnet. Для тестовой сети переменные
#: окружения переопределяют и сеть, и контракт токена.
DEFAULT_NETWORK = "base"
DEFAULT_ASSET = "USDC"


def _network_of(name: str) -> str:
    return (name or "").strip().lower()


def _is_sepolia(network: str) -> bool:
    return "sepolia" in network


def default_rpc_urls(network: str) -> tuple[str, ...]:
    return SEPOLIA_RPC_URLS if _is_sepolia(network) else BASE_RPC_URLS


def default_asset_contract(network: str, asset: str) -> str:
    if (asset or "").upper() != "USDC":
        return ""
    return USDC_BASE_SEPOLIA if _is_sepolia(network) else USDC_BASE


class DirectBaseAdapter:
    """Рельс «покупатель платит сам»: USDC в Base, сверка по хешу в сети."""

    provider = "direct.base"

    def __init__(
        self,
        *,
        payout_address: str,
        network: str = DEFAULT_NETWORK,
        asset: str = DEFAULT_ASSET,
        rpc_urls: Iterable[str] | None = None,
        confirmations: int = 2,
        policy: PaymentPolicy | None = None,
        fetch: Any = None,
    ) -> None:
        self.payout_address = (payout_address or "").strip()
        self.network = _network_of(network) or DEFAULT_NETWORK
        self.asset = (asset or DEFAULT_ASSET).upper()
        self.rpc_urls = tuple(rpc_urls) if rpc_urls else default_rpc_urls(self.network)
        self.confirmations = confirmations
        self.policy = policy or PaymentPolicy()
        self.fetch = fetch

    # -- адаптер -----------------------------------------------------------
    def create_payment(self, req: CreatePaymentRequest) -> CreatePaymentResult:
        blocked = evaluate_policy(req, self.policy)
        if blocked:
            return blocked
        if req.settlement_asset.upper() != self.asset:
            return CreatePaymentResult(
                False, req.order_id, PaymentStatus.FAILED,
                reason=f"direct_rail_serves_{self.asset}_only",
            )
        if _network_of(req.settlement_network) != self.network:
            return CreatePaymentResult(
                False, req.order_id, PaymentStatus.FAILED,
                reason=f"direct_rail_serves_{self.network}_only",
            )
        if not self.payout_address:
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED,
                                      reason="payout_address_required")
        return CreatePaymentResult(
            True,
            req.order_id,
            PaymentStatus.PENDING,
            provider_ref=ProviderRef(
                provider=self.provider,
                address_in=self.payout_address,
                checkout_url=None,  # витрины у прямого рельса нет: платёж идёт на адрес
                raw={
                    "asset": self.asset,
                    "network": self.network,
                    "payout_address": self.payout_address,
                    "amount_fiat": req.amount_fiat,
                    "currency": req.currency,
                },
            ),
        )

    def verify_callback(self, *, headers: Mapping[str, str], raw_url: str,
                        body: bytes | None = None) -> bool | None:
        # Подписи провайдера у прямого рельса нет и быть не может: доказательство
        # оплаты — запись в сети. None означает «проверки подписью нет».
        return None

    def normalize_callback(self, *, params: Mapping[str, str], headers: Mapping[str, str],
                           raw_url: str) -> PaymentEvent:
        raise NotImplementedError("direct rail has no callback; use confirm()")

    def check_status(self, ref: ProviderRef) -> PaymentEvent | None:
        return None

    # -- прямая сверка -----------------------------------------------------
    def confirm(self, tx_hash: str, *, order_id: str | None = None,
                min_atoms: int = 1) -> PaymentEvent:
        """Сверить перевод в сети и вернуть событие оплаты.

        `TransferRejected` — не оплачено (причина названа).
        `ChainUnavailable` — не смогли проверить; сеть важнее, чем отказ.
        """
        facts = confirm_usdc_transfer(
            tx_hash,
            pay_to=self.payout_address,
            min_atoms=min_atoms,
            asset=default_asset_contract(self.network, self.asset),
            rpc_urls=self.rpc_urls,
            confirmations=self.confirmations,
            fetch=self.fetch,
        )
        return PaymentEvent(
            provider=self.provider,
            order_id=order_id,
            status=PaymentStatus.PAID,
            provider_ref=self.payout_address,
            amount=facts["amount_usdc"],
            currency_or_asset=self.asset,
            network=self.network,
            txid_in=facts["tx_hash"],
            txid_out=None,
            value_forwarded=facts["amount_usdc"],
            signature_verified=None,  # подписи нет: доказательство — цепочка
            raw=facts,
        )


def adapter_from_env() -> DirectBaseAdapter:
    """Собрать адаптер из окружения сервиса."""
    return DirectBaseAdapter(
        payout_address=os.environ.get("NIDHIPATI_PAYOUT_ADDRESS", ""),
        network=os.environ.get("PAYMENT_HUB_NETWORK", DEFAULT_NETWORK),
        asset=os.environ.get("PAYMENT_HUB_ASSET", DEFAULT_ASSET),
        confirmations=int(os.environ.get("PAYMENT_HUB_CONFIRMATIONS", "2")),
    )


__all__ = [
    "DirectBaseAdapter",
    "ChainUnavailable",
    "TransferRejected",
    "DEFAULT_ASSET",
    "DEFAULT_NETWORK",
    "adapter_from_env",
    "default_rpc_urls",
    "default_asset_contract",
]
