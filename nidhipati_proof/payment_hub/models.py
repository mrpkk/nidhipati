from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class PaymentStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    SETTLED = "settled"
    FULFILLED = "fulfilled"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"
    REFUNDED = "refunded"


@dataclass(slots=True)
class PaymentPolicy:
    # Technical policy hints; provider ToS/compliance must be checked separately.
    blocked_country_codes: tuple[str, ...] = ()
    allowed_settlement_assets: tuple[str, ...] = ("USDC", "USDT")
    allowed_networks: tuple[str, ...] = ("polygon", "tron", "ethereum", "base", "arbitrum")

    def country_blocked(self, code: str | None) -> bool:
        if not code:
            return False
        return code.strip().upper() in {c.upper() for c in self.blocked_country_codes}


@dataclass(slots=True)
class CreatePaymentRequest:
    order_id: str
    amount_fiat: str
    currency: str
    product_id: str
    callback_url: str
    payout_address: str
    description: str = ""
    customer_email: str | None = None
    settlement_asset: str = "USDC"
    settlement_network: str = "polygon"
    provider_name: str | None = None  # e.g. PayGate.to provider id
    payer_country: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderRef:
    provider: str
    address_in: str | None = None
    polygon_address_in: str | None = None
    ipn_token: str | None = None
    checkout_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CreatePaymentResult:
    ok: bool
    order_id: str
    status: PaymentStatus
    provider_ref: ProviderRef | None = None
    reason: str | None = None


@dataclass(slots=True)
class PaymentEvent:
    provider: str
    order_id: str | None
    status: PaymentStatus
    provider_ref: str | None = None
    amount: str | None = None
    currency_or_asset: str | None = None
    network: str | None = None
    txid_in: str | None = None
    txid_out: str | None = None
    value_forwarded: str | None = None
    signature_verified: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)
