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
from .store import PaymentStore, OrderRecord
from .handler import handle_callback, HandleResult
from .fulfillment import FulfillmentHook, ManualFulfillment, maybe_fulfill
from .receipt import build_payment_evidence, canonical_hash
from .paygate import PayGateCardAdapter, verify_paygate_signature
from .direct import (
    ChainUnavailable,
    DirectBaseAdapter,
    TransferRejected,
    adapter_from_env,
)
from .base_rpc import confirm_usdc_transfer

__all__ = [
    "CreatePaymentRequest",
    "CreatePaymentResult",
    "PaymentEvent",
    "PaymentPolicy",
    "PaymentStatus",
    "ProviderRef",
    "evaluate_policy",
    "InMemoryIdempotencyStore",
    "PaymentStore",
    "OrderRecord",
    "handle_callback",
    "HandleResult",
    "ManualFulfillment",
    "maybe_fulfill",
    "FulfillmentHook",
    "build_payment_evidence",
    "canonical_hash",
    "PayGateCardAdapter",
    "verify_paygate_signature",
    "DirectBaseAdapter",
    "ChainUnavailable",
    "TransferRejected",
    "adapter_from_env",
    "confirm_usdc_transfer",
]
