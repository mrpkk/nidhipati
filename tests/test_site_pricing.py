"""Public spend-audit pages must all show the same price: $199 flat."""
from pathlib import Path


def test_spend_audit_price_is_199_everywhere():
    docs = Path(__file__).resolve().parent.parent / "docs"
    for name in ("pricing.html", "free-spend-audit.html", "verify-receipt.html", "index.html", "audit.html", "audit-sample.html", "agent-spend-audit.html"):
        text = (docs / name).read_text(encoding="utf-8")
        assert "$199" in text, name
        assert "First 3 paid audits" not in text, name
        assert "audit $1,250" not in text, name
        assert "audit $2,500" not in text, name
