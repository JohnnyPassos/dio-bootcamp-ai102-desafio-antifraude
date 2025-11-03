from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest


@dataclass
class InvoiceItem:
    description: Optional[str]
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]
    confidence: float


@dataclass
class InvoiceData:
    invoice_id: Optional[str]
    vendor_name: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    currency: Optional[str]
    subtotal: Optional[float]
    total_tax: Optional[float]
    invoice_total: Optional[float]
    items: List[InvoiceItem]
    field_confidence: Dict[str, float]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["items"] = [asdict(i) for i in self.items]
        return d


def _get_value(field) -> Any:
    if field is None:
        return None
    v = getattr(field, "value", None)
    if v is not None:
        return v
    return getattr(field, "content", None)


def _get_conf(field) -> float:
    if field is None:
        return 0.0
    return float(getattr(field, "confidence", 0.0))


def analyze_invoice(file_path: str, endpoint: str, key: str) -> InvoiceData:
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-invoice",
            analyze_request=AnalyzeDocumentRequest(bytes_source=f.read()),
        )
    result = poller.result()

    if not result.documents:
        raise RuntimeError("Nenhum documento foi detectado pela análise.")

    doc = result.documents[0]
    fields = doc.fields or {}

    def f(name: str):
        return fields.get(name)

    # Itens
    items: List[InvoiceItem] = []
    items_field = f("Items")
    if items_field and getattr(items_field, "value", None):
        for it in items_field.value:
            props = getattr(it, "properties", {}) or {}

            def pf(n: str):
                return props.get(n)

            amount_field = pf("Amount")
            item = InvoiceItem(
                description=_get_value(pf("Description")),
                quantity=_get_value(pf("Quantity")),
                unit_price=_get_value(pf("UnitPrice")),
                amount=_get_value(amount_field),
                confidence=_get_conf(amount_field) if amount_field is not None else 0.0,
            )
            items.append(item)

    data = InvoiceData(
        invoice_id=_get_value(f("InvoiceId")),
        vendor_name=_get_value(f("VendorName")),
        invoice_date=str(_get_value(f("InvoiceDate"))) if _get_value(f("InvoiceDate")) is not None else None,
        due_date=str(_get_value(f("DueDate"))) if _get_value(f("DueDate")) is not None else None,
        currency=_get_value(f("Currency")) or _get_value(f("CurrencySymbol")),
        subtotal=_get_value(f("SubTotal")),
        total_tax=_get_value(f("TotalTax")),
        invoice_total=_get_value(f("InvoiceTotal")),
        items=items,
        field_confidence={
            "InvoiceId": _get_conf(f("InvoiceId")),
            "VendorName": _get_conf(f("VendorName")),
            "InvoiceDate": _get_conf(f("InvoiceDate")),
            "DueDate": _get_conf(f("DueDate")),
            "Currency": _get_conf(f("Currency")),
            "SubTotal": _get_conf(f("SubTotal")),
            "TotalTax": _get_conf(f("TotalTax")),
            "InvoiceTotal": _get_conf(f("InvoiceTotal")),
        },
        raw=result.to_dict() if hasattr(result, "to_dict") else {},
    )
    return data