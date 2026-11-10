from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import CreatePaymentRequest, CreatePaymentResult, PaymentEvent, ProviderRef


class PaymentProviderAdapter(Protocol):
    provider: str

    def create_payment(self, req: CreatePaymentRequest) -> CreatePaymentResult: ...

    def verify_callback(
        self, *, headers: Mapping[str, str], raw_url: str, body: bytes | None = None
    ) -> bool | None: ...

    def normalize_callback(
        self, *, params: Mapping[str, str], headers: Mapping[str, str], raw_url: str
    ) -> PaymentEvent: ...

    def check_status(self, ref: ProviderRef) -> PaymentEvent | None: ...
