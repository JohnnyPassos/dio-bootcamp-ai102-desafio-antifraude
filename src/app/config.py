from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


dataclass
class Config:
    endpoint: str
    key: str
    min_confidence: float = 0.6
    require_sum_match: bool = False
    sum_tolerance: float = 0.01
    vendors_allowlist: Optional[List[str]] = None

    @staticmethod
    def from_env() -> "Config":
        load_dotenv(override=False)

        endpoint = os.getenv("AZURE_DOCUMENTINTELLIGENCE_ENDPOINT", "").strip()
        key = os.getenv("AZURE_DOCUMENTINTELLIGENCE_KEY", "").strip()

        if not endpoint or not key:
            raise ValueError(
                "Defina AZURE_DOCUMENTINTELLIGENCE_ENDPOINT e AZURE_DOCUMENTINTELLIGENCE_KEY no ambiente."
            )

        min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.6"))
        require_sum_match = os.getenv("REQUIRE_SUM_MATCH", "false").lower() in ("1", "true", "yes", "y")
        sum_tolerance = float(os.getenv("SUM_TOLERANCE", "0.01"))

        vendors_raw = os.getenv("VENDORS_ALLOWLIST", "").strip()
        vendors_allowlist = [v.strip() for v in vendors_raw.split(",") if v.strip()] if vendors_raw else None

        return Config(
            endpoint=endpoint,
            key=key,
            min_confidence=min_confidence,
            require_sum_match=require_sum_match,
            sum_tolerance=sum_tolerance,
            vendors_allowlist=vendors_allowlist,
        )


