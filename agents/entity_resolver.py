from agents.base_agent import BaseAgent
from tools.schemas import ResolvedEntity
from typing import Optional, Dict, Any
import json
import re


CURATED_RESOLVED_ENTITIES: Dict[str, Dict[str, Any]] = {
    "jazz": {
        "canonical_name": "Jazz (JazzWorld Pakistan Limited / PMCL)",
        "trade_name": "Jazz",
        "legal_entity_name": "Pakistan Mobile Communications Limited (PMCL)",
        "entity_type": "SUBSIDIARY",
        "ticker": None,
        "parent_company": "VEON Ltd. (NASDAQ: VEON)",
        "parent_ticker": "VEON",
        "ownership_pct": "100% wholly-owned subsidiary of VEON Ltd. (NASDAQ: VEON)",
        "local_currency": "PKR",
        "sector": "Telecommunications & Digital Services",
        "headquarters": "Islamabad, Pakistan",
        "wikipedia_title": "Jazz_(mobile_network_operator)",
        "required_search_anchors": ["Jazz Pakistan", "VEON Jazz", "JazzCash", "PMCL", "JazzWorld", "telecom"],
        "negative_keywords": [
            "Jazz Pharmaceuticals", "Utah Jazz", "NBA", "basketball", "music",
            "jazz festival", "concert", "album", "saxophone", "band", "singer"
        ],
        "subsidiary_kpis": {
            "reporting_basis": "Consolidated under VEON Ltd. (NASDAQ: VEON) Integrated Annual Report & PACRA Ratings",
            "annual_revenue": "PKR 456.6B (FY2025, VEON Integrated Annual Report / PACRA)",
            "ebitda": "PKR 200.3B (FY2025, ~43.9% EBITDA margin)",
            "subscribers": "~76M+ cellular subscribers (~37%+ market share; Pakistan's largest mobile operator)",
            "digital_ecosystem": "JazzCash (~19M+ monthly active fintech users), Tamasha OTT, Simosa digital super-app, Garaj Cloud",
            "credit_rating": "AA+ (Long-Term) / A1+ (Short-Term) — PACRA"
        }
    },
    "zong": {
        "canonical_name": "Zong 4G (China Mobile Pakistan / CMPak)",
        "trade_name": "Zong 4G",
        "legal_entity_name": "China Mobile Pakistan Limited (CMPak)",
        "entity_type": "SUBSIDIARY",
        "ticker": None,
        "parent_company": "China Mobile Limited (SEHK: 0941.HK)",
        "parent_ticker": "0941.HK",
        "ownership_pct": "100% wholly-owned subsidiary of China Mobile Limited (SEHK: 0941.HK)",
        "local_currency": "PKR",
        "sector": "Telecommunications & Mobile Broadband",
        "headquarters": "Islamabad, Pakistan",
        "wikipedia_title": "Zong_4G",
        "required_search_anchors": ["Zong 4G", "CMPak", "China Mobile Pakistan", "Zong Pakistan", "PTA", "telecom"],
        "negative_keywords": [
            "slave ship", "1781", "massacre", "Kelly Zong", "Wahaha",
            "Zong Qinghou", "beverage", "bottled water", "historic ship", "abolition"
        ],
        "subsidiary_kpis": {
            "reporting_basis": "Undisclosed standalone (Consolidated under China Mobile Limited [SEHK: 0941.HK] & PTA Market Reports)",
            "annual_revenue": "Undisclosed standalone (Consolidated under China Mobile Limited [0941.HK])",
            "ebitda": "Undisclosed standalone (Consolidated under China Mobile Limited [0941.HK])",
            "subscribers": "~50M+ mobile subscribers (~26% market share; Pakistan's #2 telecom & 4G broadband leader)",
            "digital_ecosystem": "My Zong App, PayMax digital payments, 15,000+ 4G LTE sites, 5G commercial readiness & enterprise IoT",
            "credit_rating": "Backed by parent China Mobile Limited (Moody's A1 / S&P A+)"
        }
    },
    "ufone": {
        "canonical_name": "Ufone 4G (Pak Telecom Mobile Limited / PTML)",
        "trade_name": "Ufone 4G",
        "legal_entity_name": "Pak Telecom Mobile Limited (PTML)",
        "entity_type": "SUBSIDIARY",
        "ticker": None,
        "parent_company": "Pakistan Telecommunication Company Limited (PSX: PTC) / e& (Etisalat)",
        "parent_ticker": "PTC.KA",
        "ownership_pct": "100% owned by PTCL Group (managed by e& / Etisalat)",
        "local_currency": "PKR",
        "sector": "Telecommunications & Mobile Services",
        "headquarters": "Islamabad, Pakistan",
        "wikipedia_title": "Ufone",
        "required_search_anchors": ["Ufone", "PTCL", "PTML", "Pakistan telecom", "UPaisa"],
        "negative_keywords": ["UFO", "alien", "music"],
        "subsidiary_kpis": {
            "reporting_basis": "Consolidated under PTCL Group (PSX: PTC) financial disclosures",
            "annual_revenue": "Consolidated under PTCL Group (PSX: PTC)",
            "ebitda": "Consolidated under PTCL Group (PSX: PTC)",
            "subscribers": "~26M+ mobile subscribers (expanding via Telenor Pakistan acquisition integration)",
            "digital_ecosystem": "UPaisa branchless banking, Ufone 4G broadband, Shoq OTT",
            "credit_rating": "Backed by PTCL Group & e& (Etisalat)"
        }
    },
    "telenor pakistan": {
        "canonical_name": "Telenor Pakistan (Private) Limited",
        "trade_name": "Telenor Pakistan",
        "legal_entity_name": "Telenor Pakistan (Private) Limited",
        "entity_type": "SUBSIDIARY",
        "ticker": None,
        "parent_company": "PTCL Group / e& (transitioning from Telenor ASA)",
        "parent_ticker": "PTC.KA",
        "ownership_pct": "Wholly-owned telecom subsidiary (PTCL / e& acquisition)",
        "local_currency": "PKR",
        "sector": "Telecommunications & Digital Services",
        "headquarters": "Islamabad, Pakistan",
        "wikipedia_title": "Telenor_Pakistan",
        "required_search_anchors": ["Telenor Pakistan", "PTCL", "Easypaisa", "Pakistan telecom"],
        "negative_keywords": ["Norway football", "music"],
        "subsidiary_kpis": {
            "reporting_basis": "Consolidated under parent telecom filings & PTA operational disclosures",
            "annual_revenue": "Consolidated under parent group filings",
            "ebitda": "Consolidated under parent group filings",
            "subscribers": "~43M+ cellular subscribers across Pakistan",
            "digital_ecosystem": "MyTelenor App, historical Easypaisa ecosystem affiliation, 4G nationwide network",
            "credit_rating": "Parent-backed telecom operator"
        }
    },
    "samsung": {
        "canonical_name": "Samsung Electronics Co., Ltd.",
        "trade_name": "Samsung Electronics",
        "legal_entity_name": "Samsung Electronics Co., Ltd.",
        "entity_type": "PUBLIC",
        "ticker": "005930.KS",
        "parent_company": "Samsung Group (Standalone Listed Flagship)",
        "parent_ticker": None,
        "ownership_pct": "Publicly Traded Corporation (KRX: 005930.KS)",
        "local_currency": "KRW",
        "sector": "Technology — Semiconductors & Consumer Electronics",
        "headquarters": "Suwon, South Korea",
        "wikipedia_title": "Samsung_Electronics",
        "required_search_anchors": ["Samsung Electronics", "005930", "Galaxy", "HBM", "semiconductor", "foundry"],
        "negative_keywords": ["Samsung Heavy Industries", "Samsung Life Insurance", "Samsung Biologics", "shipbuilding"],
        "subsidiary_kpis": {}
    },
    "jazz pharmaceuticals": {
        "canonical_name": "Jazz Pharmaceuticals plc",
        "trade_name": "Jazz Pharmaceuticals",
        "legal_entity_name": "Jazz Pharmaceuticals plc",
        "entity_type": "PUBLIC",
        "ticker": "JAZZ",
        "parent_company": None,
        "parent_ticker": None,
        "ownership_pct": "Publicly Traded Corporation (NASDAQ: JAZZ)",
        "local_currency": "USD",
        "sector": "Healthcare — Biopharmaceuticals",
        "headquarters": "Dublin, Ireland",
        "wikipedia_title": "Jazz_Pharmaceuticals",
        "required_search_anchors": ["Jazz Pharmaceuticals", "NASDAQ: JAZZ", "biopharma", "oncology", "neuroscience"],
        "negative_keywords": ["Jazz Pakistan", "VEON", "JazzCash", "Utah Jazz", "NBA", "music"],
        "subsidiary_kpis": {}
    },
    "motive": {
        "canonical_name": "Motive Technologies, Inc.",
        "trade_name": "Motive",
        "legal_entity_name": "Motive Technologies, Inc. (formerly KeepTruckin, Inc.)",
        "entity_type": "PRIVATE",
        "ticker": None,
        "parent_company": None,
        "parent_ticker": None,
        "ownership_pct": "Privately Held Enterprise (Form S-1 Filer — Proposed NYSE: MTVE)",
        "local_currency": "USD",
        "sector": "AI Fleet Management, Physical Operations & Commercial Telematics",
        "headquarters": "San Francisco, California",
        "wikipedia_title": "Motive_(company)",
        "required_search_anchors": [
            "Motive Technologies", "KeepTruckin", "Shoaib Makani",
            "fleet", "telematics", "dashcam", "Samsara", "MTVE"
        ],
        "negative_keywords": [
            "possible motive", "ulterior motive", "motive behind", "motive for",
            "profit motive", "home invasion", "hammer attack", "murder", "homicide",
            "police discuss", "police investigate", "shooting", "stabbing", "true crime",
            "People.com", "Toronto Police"
        ],
        "subsidiary_kpis": {}
    }
}

# Alias mappings to canonical keys in CURATED_RESOLVED_ENTITIES
ENTITY_ALIASES: Dict[str, str] = {
    "jazz": "jazz",
    "jazz pakistan": "jazz",
    "jazzworld": "jazz",
    "jazzworld pakistan": "jazz",
    "jazzworld pakistan limited": "jazz",
    "pmcl": "jazz",
    "mobilink": "jazz",
    "pakistan mobile communications": "jazz",
    "pakistan mobile communications limited": "jazz",
    "zong": "zong",
    "zong 4g": "zong",
    "zong pakistan": "zong",
    "cmpak": "zong",
    "china mobile pakistan": "zong",
    "china mobile pakistan limited": "zong",
    "ufone": "ufone",
    "ufone 4g": "ufone",
    "ptml": "ufone",
    "telenor pakistan": "telenor pakistan",
    "samsung": "samsung",
    "samsung electronics": "samsung",
    "samsung electronics co., ltd.": "samsung",
    "005930.ks": "samsung",
    "jazz pharmaceuticals": "jazz pharmaceuticals",
    "jazz pharma": "jazz pharmaceuticals",
    "motive": "motive",
    "motive technologies": "motive",
    "motive technologies inc": "motive",
    "motive technologies, inc.": "motive",
    "keeptruckin": "motive",
    "keep truckin": "motive",
    "mtve": "motive",
}


class EntityResolverAgent(BaseAgent):
    """
    Pre-Flight Entity Disambiguation Agent:
    Runs BEFORE parallel subagents to eliminate disambiguation collapses on short,
    ambiguous, or regional corporate names (e.g. 'Jazz', 'Zong', 'Samsung').
    Outputs a strict Pydantic `ResolvedEntity` consumed by all downstream tools & agents.
    """
    def __init__(self):
        super().__init__(
            name="Entity Resolver",
            role="Pre-Flight Corporate Entity Disambiguation Specialist",
            system_prompt="""You are a corporate entity disambiguation specialist.
Given a user query (possibly a short, ambiguous, or regional company name), identify the exact corporate entity
and return ONLY valid JSON matching the requested schema (no prose, no markdown fences)."""
        )

    def resolve(
        self,
        user_query: str,
        region_hint: Optional[str] = None,
        industry_hint: Optional[str] = None,
        financial_probe: Optional[Dict[str, Any]] = None
    ) -> ResolvedEntity:
        """
        Deterministically + LLM-assisted resolves `user_query` into a strict `ResolvedEntity`.
        Guarantees every downstream Wikipedia, Finance, and News RSS query uses anchored terms
        and excludes negative collision keywords.
        """
        raw = user_query.strip()
        norm = re.sub(r'\s+', ' ', raw.lower()).strip()

        # Explicit ticker disambiguation: uppercase 'JAZZ' explicitly means Jazz Pharmaceuticals (NASDAQ: JAZZ),
        # whereas 'Jazz' or 'jazz' defaults to regional/telecom Jazz Pakistan (unless pharma hint is given)
        if raw == "JAZZ" or (industry_hint and "pharma" in industry_hint.lower() and "jazz" in norm):
            return ResolvedEntity(**CURATED_RESOLVED_ENTITIES["jazz pharmaceuticals"])

        # 1. Deterministic lookup for notorious ambiguous / regional / subsidiary entities
        if norm in ENTITY_ALIASES:
            key = ENTITY_ALIASES[norm]
            return ResolvedEntity(**CURATED_RESOLVED_ENTITIES[key])

        # Check region/industry hint matches for partial ambiguous names
        if "jazz" in norm and ("pakistan" in norm or "veon" in norm or (region_hint and "pakistan" in region_hint.lower())):
            return ResolvedEntity(**CURATED_RESOLVED_ENTITIES["jazz"])
        if "zong" in norm and ("pakistan" in norm or "4g" in norm or "cmpak" in norm or "china mobile" in norm or (region_hint and "pakistan" in region_hint.lower())):
            return ResolvedEntity(**CURATED_RESOLVED_ENTITIES["zong"])

        # 2. If financial_probe was provided (for general public/private queries), build structured ResolvedEntity
        if financial_probe:
            is_public = financial_probe.get("is_public", False)
            data = financial_probe.get("data", {})
            official_name = data.get("company_name") or raw
            symbol = data.get("symbol") if is_public else None
            sector = data.get("sector") or industry_hint or "Technology & Services"
            industry = data.get("industry") or ""
            exchange = data.get("exchange") or ""

            clean_trade = re.sub(
                r',?\s*\b(?:Co\.?,?\s*Ltd\.?|Corporation|Corp\.?|Incorporated|Inc\.?|Limited|Ltd\.?|PLC|S\.A\.S?\.?|S\.A\.R\.L\.?|SA|SAS|SARL|N\.V\.?|NV|B\.V\.?|BV|S\.p\.A\.?|SpA|AG|GmbH|KGaA|SE|AB|ASA|Oyj|LLC|PBC|Holdings)(?=\s|$|[,\.])\.?',
                '', official_name, flags=re.IGNORECASE
            ).strip(" ,.") or raw

            hq_parts = [p for p in [data.get("headquarters_city"), data.get("headquarters_country")] if p]
            inferred_hq = ", ".join(hq_parts) if hq_parts else (region_hint or "Global")

            anchors = []
            if clean_trade and len(clean_trade.split()) > 1:
                anchors.append(clean_trade)
            if official_name and official_name.lower() != clean_trade.lower() and official_name not in anchors:
                anchors.append(official_name)
            if symbol and symbol != "PRIVATE / UNLISTED":
                anchors.append(symbol)
            if sector and sector not in anchors:
                anchors.append(sector.split("&")[0].strip())
            if industry and industry not in anchors:
                anchors.append(industry.split("&")[0].strip())
            if region_hint:
                anchors.append(region_hint)
            if not anchors:
                anchors.extend([f"{clean_trade} company", f"{clean_trade} corporate", f"{clean_trade} enterprise"])

            negatives = ["album", "song", "band", "movie", "novel", "obituary"]
            if len(clean_trade.split()) == 1:
                negatives.extend(["murder", "homicide", "home invasion", "shooting", "stabbing", "police discuss", "true crime"])
            # Build clean Wikipedia title candidate (stripped of SA/SE/NV/Inc/Ltd)
            wiki_title = clean_trade.replace(" ", "_")

            return ResolvedEntity(
                canonical_name=official_name,
                trade_name=clean_trade,
                legal_entity_name=official_name,
                entity_type="PUBLIC" if is_public else "PRIVATE",
                ticker=symbol,
                parent_company=None,
                parent_ticker=None,
                ownership_pct=f"Publicly Traded Corporation ({exchange}: {symbol})" if is_public else "Privately Held Enterprise",
                local_currency=(data.get("current_price", "USD").split()[-1] if is_public and data.get("current_price", "N/A") != "N/A" else "USD"),
                sector=sector,
                headquarters=inferred_hq,
                wikipedia_title=wiki_title,
                required_search_anchors=list(dict.fromkeys([a for a in anchors if a])),
                negative_keywords=list(dict.fromkeys(negatives)),
                subsidiary_kpis={}
            )

        # 3. LLM-assisted disambiguation fallback for unknown short/ambiguous queries (when no financial_probe yet)
        if len(raw.split()) == 1 and not raw.isupper():
            try:
                prompt = f"""Disambiguate the corporate entity '{raw}' (region hint: {region_hint or 'Pakistan/Global commercial'}, industry hint: {industry_hint or 'Technology/Telecom/Commercial'}).
Return ONLY a JSON object with keys:
canonical_name, trade_name, legal_entity_name, entity_type ("PUBLIC"|"PRIVATE"|"SUBSIDIARY"), ticker (string or null),
parent_company (string or null), parent_ticker (string or null), local_currency, sector, headquarters,
wikipedia_title, required_search_anchors (list of 4-6 distinct domain/product/company anchors — NEVER include the bare single word '{raw}' alone),
negative_keywords (list of 5-8 unrelated collision terms, including common English noun phrases or crime/entertainment collisions if '{raw}' is a common dictionary word)."""
                resp = self.generate_response(prompt)
                m = re.search(r'\{.*\}', resp, re.DOTALL)
                if m:
                    parsed = json.loads(m.group(0))
                    if parsed.get("canonical_name") and parsed.get("entity_type") in ("PUBLIC", "PRIVATE", "SUBSIDIARY"):
                        return ResolvedEntity(**parsed)
            except Exception:
                pass

        # Safe universal fallback
        fallback_negatives = ["album", "song", "band", "movie", "obituary"]
        if len(raw.split()) == 1:
            fallback_negatives.extend(["murder", "homicide", "home invasion", "shooting", "police discuss", "true crime"])
        return ResolvedEntity(
            canonical_name=raw,
            trade_name=raw,
            legal_entity_name=raw,
            entity_type="PRIVATE",
            ticker=None,
            sector=industry_hint or "Commercial Technology & Services",
            headquarters=region_hint or "Global",
            wikipedia_title=raw.replace(" ", "_"),
            required_search_anchors=[f"{raw} Technologies", f"{raw} company", f"{raw} corporate", f"{raw} software"],
            negative_keywords=fallback_negatives
        )
