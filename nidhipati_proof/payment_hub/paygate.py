from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .models import (
    CreatePaymentRequest,
    CreatePaymentResult,
    PaymentEvent,
    PaymentPolicy,
    PaymentStatus,
    ProviderRef,
)
from .policy import evaluate_policy

HttpGet = Callable[[str, Mapping[str, str] | None, float], tuple[int, bytes, Mapping[str, str]]]


def _default_http_get(url: str, headers: Mapping[str, str] | None = None, timeout: float = 20.0):
    req = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - target is explicit provider API
        return r.status, r.read(), dict(r.headers)


def verify_paygate_signature(
    *,
    registered_callback_base: str,
    raw_query_string: str,
    signature_b64: str,
    public_key_pem: bytes | str,
) -> bool:
    """Verify PayGate.to callback signature.

    PayGate.to signs the exact full callback URL: registered callback base + raw query string.
    Do not rebuild/normalize the query string. Key: RSA 2048, SHA-256, PKCS1v15.
    Docs: https://paygate.to/docs/payment-gateway-api/ and crypto-payment-api/ callback sections.
    """
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("utf-8")
    signed = registered_callback_base if not raw_query_string else f"{registered_callback_base}?{raw_query_string}"
    try:
        pub = serialization.load_pem_public_key(public_key_pem)
        sig = base64.b64decode(signature_b64)
        pub.verify(sig, signed.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


class PayGateCardAdapter:
    """PayGate.to card gateway adapter (USDC Polygon payout). Draft: verify live docs/ToS before production."""

    provider = "paygate.to"

    def __init__(
        self,
        *,
        api_base: str = "https://api.paygate.to",
        checkout_base: str = "https://checkout.paygate.to",
        http_get: HttpGet | None = None,
        policy: PaymentPolicy | None = None,
        callback_public_key_pem: bytes | str | None = None,
        registered_callback_base: str | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.checkout_base = checkout_base.rstrip("/")
        self.http_get = http_get or _default_http_get
        self.policy = policy or PaymentPolicy()
        self.callback_public_key_pem = callback_public_key_pem
        self.registered_callback_base = registered_callback_base

    def create_payment(self, req: CreatePaymentRequest) -> CreatePaymentResult:
        blocked = evaluate_policy(req, self.policy)
        if blocked:
            return blocked
        if req.settlement_asset.upper() != "USDC" or req.settlement_network.lower() != "polygon":
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="paygate_v0_supports_usdc_polygon_only")
        if not req.payout_address:
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="payout_address_required")
        # PayGate.to wallet.php requires unique GET param in callback; ensure order_id is present.
        cb = req.callback_url
        if "order_id=" not in cb and "invoice" not in cb and "number=" not in cb:
            sep = "&" if "?" in cb else "?"
            cb = f"{cb}{sep}order_id={urllib.parse.quote(req.order_id)}"
        wallet_url = (
            f"{self.api_base}/control/wallet.php?address={urllib.parse.quote(req.payout_address)}"
            f"&callback={urllib.parse.quote(cb, safe='')}"
        )
        status, body, _ = self.http_get(wallet_url, {}, 20.0)
        if status >= 400:
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason=f"wallet_http_{status}")
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="wallet_invalid_json")
        address_in = data.get("address_in")
        if not address_in:
            return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="wallet_missing_address_in")
        params = {
            "address": address_in,
            "amount": str(req.amount_fiat),
            "currency": req.currency,
            "email": req.customer_email or "buyer@example.invalid",
        }
        if req.provider_name:
            params["provider"] = req.provider_name
            checkout = f"{self.checkout_base}/process-payment.php?{urllib.parse.urlencode(params)}"
        else:
            checkout = f"{self.checkout_base}/pay.php?{urllib.parse.urlencode(params)}"
        return CreatePaymentResult(
            True,
            req.order_id,
            PaymentStatus.PENDING,
            provider_ref=ProviderRef(
                provider=self.provider,
                address_in=address_in,
                polygon_address_in=data.get("polygon_address_in"),
                ipn_token=data.get("ipn_token"),
                checkout_url=checkout,
                raw=data if isinstance(data, dict) else {},
            ),
        )

    def verify_callback(
        self, *, headers: Mapping[str, str], raw_url: str, body: bytes | None = None
    ) -> bool | None:
        sig = headers.get("X-PayGate-Signature") or headers.get("x-paygate-signature")
        if not sig or not self.callback_public_key_pem or not self.registered_callback_base:
            return None
        parsed = urllib.parse.urlsplit(raw_url)
        raw_qs = parsed.query
        return verify_paygate_signature(
            registered_callback_base=self.registered_callback_base,
            raw_query_string=raw_qs,
            signature_b64=sig,
            public_key_pem=self.callback_public_key_pem,
        )

    def normalize_callback(
        self, *, params: Mapping[str, str], headers: Mapping[str, str], raw_url: str
    ) -> PaymentEvent:
        verified = self.verify_callback(headers=headers, raw_url=raw_url)
        order_id = params.get("order_id") or params.get("invoice") or params.get("number")
        # Card callback fields per docs: value_coin, coin, txid_in, txid_out, address_in, value_forwarded_coin.
        has_paid = bool(params.get("txid_in") or params.get("txid_out") or params.get("value_coin"))
        status = PaymentStatus.PAID if has_paid else PaymentStatus.PENDING
        if params.get("status") == "unpaid":
            status = PaymentStatus.PENDING
        return PaymentEvent(
            provider=self.provider,
            order_id=order_id,
            status=status,
            provider_ref=params.get("address_in"),
            amount=params.get("value_coin"),
            currency_or_asset=params.get("coin") or "polygon_usdc",
            network="polygon",
            txid_in=params.get("txid_in"),
            txid_out=params.get("txid_out"),
            value_forwarded=params.get("value_forwarded_coin"),
            signature_verified=verified,
            raw=dict(params),
        )

    def check_status(self, ref: ProviderRef) -> PaymentEvent | None:
        if not ref.ipn_token:
            return None
        url = f"{self.api_base}/control/payment-status.php?ipn_token={urllib.parse.quote(ref.ipn_token)}"
        status, body, _ = self.http_get(url, {}, 20.0)
        if status >= 400:
            return None
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            return None
        paid = str(data.get("status", "")).lower() == "paid"
        return PaymentEvent(
            provider=self.provider,
            order_id=None,
            status=PaymentStatus.PAID if paid else PaymentStatus.PENDING,
            amount=data.get("value_coin"),
            currency_or_asset=data.get("coin"),
            network="polygon",
            txid_out=data.get("txid_out"),
            signature_verified=None,
            raw=data if isinstance(data, dict) else {},
        )
