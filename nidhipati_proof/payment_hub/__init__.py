"""Payment Hub module (draft).

Provider-agnostic checkout/callback/fulfillment primitives for existing
products. First target adapter: PayGate.to (card -> USDC Polygon).
Jurisdiction/policy checks are configurable; operators must verify provider
terms and compliance requirements separately.
"""

from .models import (
    CreatePaymentRequest,
    CreatePaymentResult,
    PaymentEvent,
    PaymentPolicy,
    PaymentStatus,
    ProviderRef,
)
from .policy import evaluate_policy
from .idempotency import InMemoryIdempotencyStore
from .paygate import PayGateCardAdapter, verify_paygate_signature

__all__ = [
    "CreatePaymentRequest",
    "CreatePaymentResult",
    "PaymentEvent",
    "PaymentPolicy",
    "PaymentStatus",
    "ProviderRef",
    "evaluate_policy",
    "InMemoryIdempotencyStore",
    "PayGateCardAdapter",
    "verify_paygate_signature",
]
