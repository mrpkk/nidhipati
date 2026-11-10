from __future__ import annotations

from .models import CreatePaymentRequest, CreatePaymentResult, PaymentPolicy, PaymentStatus


def evaluate_policy(req: CreatePaymentRequest, policy: PaymentPolicy | None = None) -> CreatePaymentResult | None:
    policy = policy or PaymentPolicy()
    if not req.order_id or not req.order_id.strip():
        return CreatePaymentResult(False, req.order_id or "", PaymentStatus.FAILED, reason="order_id_required")
    if policy.country_blocked(req.payer_country):
        return CreatePaymentResult(
            False,
            req.order_id,
            PaymentStatus.FAILED,
            reason=f"payer_country_blocked:{(req.payer_country or '').upper()}",
        )
    if req.settlement_asset.upper() not in {a.upper() for a in policy.allowed_settlement_assets}:
        return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="settlement_asset_not_allowed")
    if req.settlement_network.lower() not in {n.lower() for n in policy.allowed_networks}:
        return CreatePaymentResult(False, req.order_id, PaymentStatus.FAILED, reason="settlement_network_not_allowed")
    if "callback=" not in req.callback_url and "order_id" not in req.callback_url and "invoice" not in req.callback_url:
        # Heuristic only: PayGate.to requires a unique GET param in callback URL.
        # We don't hard-fail here to avoid false positives; adapter may enforce.
        pass
    return None
