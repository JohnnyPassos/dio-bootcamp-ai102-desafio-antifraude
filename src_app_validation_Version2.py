from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .azure_di import InvoiceData, InvoiceItem
from .config import Config


@dataclass
class ValidationResult:
    approved: bool
    reasons: List[str]


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s[: len(fmt)], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _float_or_none(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _sum_items(items: List[InvoiceItem]) -> Optional[float]:
    if not items:
        return None
    total = 0.0
    at_least_one = False
    for it in items:
        if it.amount is not None:
            total += float(it.amount)
            at_least_one = True
        else:
            qty = _float_or_none(it.quantity)
            unit = _float_or_none(it.unit_price)
            if qty is not None and unit is not None:
                total += qty * unit
                at_least_one = True
    return total if at_least_one else None


def validate_invoice(data: InvoiceData, cfg: Config) -> ValidationResult:
    reasons: List[str] = []

    # 1) Campos obrigatórios
    required_fields = {
        "InvoiceId": data.invoice_id,
        "VendorName": data.vendor_name,
        "InvoiceTotal": data.invoice_total,
        "InvoiceDate": data.invoice_date,
    }
    for name, val in required_fields.items():
        if val in (None, "", []):
            reasons.append(f"Campo obrigatório ausente: {name}")

    # 2) Confiança mínima em campos chave
    for key_field in ("InvoiceId", "VendorName", "InvoiceDate", "InvoiceTotal"):
        conf = float(data.field_confidence.get(key_field, 0.0))
        if conf < cfg.min_confidence:
            reasons.append(f"Confiança baixa em {key_field}: {conf:.2f} (mínimo {cfg.min_confidence:.2f})")

    # 3) Lista de fornecedores permitidos (se definida)
    if cfg.vendors_allowlist and data.vendor_name:
        allow = {v.lower() for v in cfg.vendors_allowlist}
        if data.vendor_name.lower() not in allow:
            reasons.append(f"Fornecedor '{data.vendor_name}' não está na lista permitida.")

    # 4) Verificações de soma
    invoice_total = _float_or_none(data.invoice_total)
    subtotal = _float_or_none(data.subtotal)
    total_tax = _float_or_none(data.total_tax)
    items_sum = _sum_items(data.items)

    def close_enough(a: float, b: float, tol: float) -> bool:
        return abs(a - b) <= tol

    if invoice_total is not None:
        if cfg.require_sum_match:
            if items_sum is not None:
                if not close_enough(invoice_total, items_sum, cfg.sum_tolerance):
                    reasons.append(
                        f"Soma dos itens ({items_sum:.2f}) difere do InvoiceTotal ({invoice_total:.2f}) "
                        f"acima da tolerância ({cfg.sum_tolerance})."
                    )
            elif subtotal is not None and total_tax is not None:
                if not close_enough(invoice_total, subtotal + total_tax, cfg.sum_tolerance):
                    reasons.append(
                        f"SubTotal+TotalTax ({(subtotal + total_tax):.2f}) difere do InvoiceTotal ({invoice_total:.2f}) "
                        f"acima da tolerância ({cfg.sum_tolerance})."
                    )
            else:
                reasons.append(
                    "Não foi possível verificar a soma (itens ou SubTotal/TotalTax ausentes) com require_sum_match habilitado."
                )
        else:
            # Modo suave: se houver dados suficientes e diferença for grande, apenas avisa
            if items_sum is not None and not close_enough(invoice_total, items_sum, cfg.sum_tolerance * 5):
                reasons.append(
                    f"Aviso: Soma dos itens ({items_sum:.2f}) difere do InvoiceTotal ({invoice_total:.2f})."
                )

    # 5) Datas coerentes: DueDate >= InvoiceDate (quando existirem)
    inv_dt = _parse_date(data.invoice_date)
    due_dt = _parse_date(data.due_date)
    if inv_dt and due_dt and due_dt < inv_dt:
        reasons.append("DueDate é anterior a InvoiceDate.")

    approved = len([r for r in reasons if not r.lower().startswith("aviso")]) == 0
    return ValidationResult(approved=approved, reasons=reasons)