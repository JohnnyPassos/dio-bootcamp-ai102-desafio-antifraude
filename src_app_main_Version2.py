from __future__ import annotations

import argparse
import json
import sys

from .config import Config
from .azure_di import analyze_invoice
from .validation import validate_invoice


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validador de faturas usando Azure AI Document Intelligence (prebuilt-invoice)."
    )
    p.add_argument("--file", required=True, help="Caminho do arquivo da fatura (PDF, PNG, JPG, etc.)")
    p.add_argument("--min-confidence", type=float, default=None, help="Confiança mínima exigida nos campos chave.")
    p.add_argument("--sum-tolerance", type=float, default=None, help="Tolerância para checagem de soma.")
    p.add_argument(
        "--require-sum-match",
        action="store_true",
        help="Requer que a soma dos itens/valores bata com InvoiceTotal dentro da tolerância.",
    )
    p.add_argument(
        "--vendors-allowlist",
        type=str,
        default=None,
        help='Lista de fornecedores permitidos, separados por vírgula. Ex.: "Fornecedor A,Fornecedor B"',
    )
    return p


def override_cfg_with_args(cfg: Config, args: argparse.Namespace) -> Config:
    if args.min_confidence is not None:
        cfg.min_confidence = args.min_confidence
    if args.sum_tolerance is not None:
        cfg.sum_tolerance = args.sum_tolerance
    if args.require_sum_match:
        cfg.require_sum_match = True
    if args.vendors_allowlist:
        cfg.vendors_allowlist = [v.strip() for v in args.vendors_allowlist.split(",") if v.strip()]
    return cfg


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        cfg = Config.from_env()
        cfg = override_cfg_with_args(cfg, args)

        data = analyze_invoice(file_path=args.file, endpoint=cfg.endpoint, key=cfg.key)
        result = validate_invoice(data, cfg)

        output = {
            "approved": result.approved,
            "reasons": result.reasons,
            "extracted": {
                "InvoiceId": data.invoice_id,
                "VendorName": data.vendor_name,
                "InvoiceDate": data.invoice_date,
                "DueDate": data.due_date,
                "Currency": data.currency,
                "SubTotal": data.subtotal,
                "TotalTax": data.total_tax,
                "InvoiceTotal": data.invoice_total,
            },
            "confidences": data.field_confidence,
            "items": [i.__dict__ for i in data.items],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

        # Exit codes: 0 aprovado, 2 reprovado
        return 0 if result.approved else 2

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())