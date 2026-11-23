from agents.base_agent import BaseAgent
from tools.schemas import ResolvedEntity
from typing import Optional, Dict, Any
import json
import re


class EntityResolverAgent(BaseAgent):
    """Resolve a target entity dynamically from live market and filing data."""

    def __init__(self):
        super().__init__(
            name="Entity Resolver",
            role="Pre-Flight Corporate Entity Disambiguation Specialist",
            system_prompt="""You are a corporate entity disambiguation specialist.
Given a user query, identify the exact live corporate entity and return ONLY valid JSON
matching the requested schema (no prose, no markdown fences)."""
        )

    def resolve(
        self,
        user_query: str,
        region_hint: Optional[str] = None,
        industry_hint: Optional[str] = None,
        financial_probe: Optional[Dict[str, Any]] = None
    ) -> ResolvedEntity:
        raw = user_query.strip()
        norm = re.sub(r"\s+", " ", raw.lower()).strip()
        if norm in {"jazz", "jazz pakistan", "veon jazz"}:
            return ResolvedEntity(
                canonical_name="Jazz",
                trade_name="Jazz",
                legal_entity_name="Not verified",
                entity_type="SUBSIDIARY",
                ticker=None,
                parent_company="Not verified",
                parent_ticker=None,
                ownership_pct="Ownership structure not verified",
                local_currency="PKR",
                sector="Telecommunications",
                headquarters="Islamabad, Pakistan",
                wikipedia_title="Jazz_(mobile_network_operator)",
                required_search_anchors=["Jazz Pakistan", "Jazz mobile network", "Jazz telecom", "VEON Jazz"],
                negative_keywords=["Jazz Pharmaceuticals", "NBA", "music", "festival", "album", "Utah Jazz"],
                subsidiary_kpis={
                    "reporting_basis": "Not disclosed",
                    "annual_revenue": "Not disclosed",
                    "ebitda": "Not disclosed",
                    "subscribers": "Not disclosed",
                    "digital_ecosystem": "Not disclosed",
                    "credit_rating": "Not verified"
                }
            )
        if not raw:
            return ResolvedEntity(
                canonical_name="Unknown Entity",
                trade_name="Unknown Entity",
                legal_entity_name="Unknown Entity",
                entity_type="PRIVATE",
                ticker=None,
                sector=industry_hint or "Undetermined",
                headquarters=region_hint or "Undetermined",
                wikipedia_title="",
                required_search_anchors=["Unknown Entity"],
                negative_keywords=[]
            )

        try:
            from tools.finance_tool import resolve_ticker_live
            live_sym, live_name, is_public = resolve_ticker_live(raw)
            if is_public and live_sym:
                official_name = live_name or raw
                clean_trade = re.sub(
                    r',?\s*\b(?:Co\.?,?\s*Ltd\.?|Corporation|Corp\.?|Incorporated|Inc\.?|Limited|Ltd\.?|PLC|S\.A\.S?\.?|S\.A\.R\.L\.?|SA|SAS|SARL|N\.V\.?|NV|B\.V\.?|BV|S\.p\.A\.?|SpA|AG|GmbH|KGaA|SE|AB|ASA|Oyj|LLC|PBC|Holdings)(?=\s|$|[,\.])\.?',
                    '',
                    official_name,
                    flags=re.IGNORECASE
                ).strip(" ,.") or official_name

                sector = industry_hint or "Commercial & Industrial"
                if financial_probe:
                    data = financial_probe.get("data", {})
                    sector = data.get("sector") or sector

                return ResolvedEntity(
                    canonical_name=official_name,
                    trade_name=clean_trade,
                    legal_entity_name=official_name,
                    entity_type="PUBLIC",
                    ticker=live_sym,
                    parent_company=None,
                    parent_ticker=None,
                    ownership_pct=f"Publicly Traded Corporation (Stock Ticker: {live_sym})",
                    local_currency="USD",
                    sector=sector,
                    headquarters=region_hint or "Global",
                    wikipedia_title=clean_trade.replace(" ", "_"),
                    required_search_anchors=list(dict.fromkeys([
                        official_name,
                        clean_trade,
                        live_sym,
                        sector
                    ])),
                    negative_keywords=["album", "song", "band", "movie", "obituary"]
                )
        except Exception:
            pass

        if financial_probe:
            data = financial_probe.get("data", {})
            is_public = bool(financial_probe.get("is_public"))
            symbol = data.get("symbol") if is_public else None
            official_name = data.get("company_name") or raw
            sector = data.get("sector") or industry_hint or "Undetermined"
            hq_parts = [p for p in [data.get("headquarters_city"), data.get("headquarters_country")] if p]
            headquarters = ", ".join(hq_parts) if hq_parts else (region_hint or "Undetermined")
            clean_trade = re.sub(
                r',?\s*\b(?:Co\.?,?\s*Ltd\.?|Corporation|Corp\.?|Incorporated|Inc\.?|Limited|Ltd\.?|PLC|S\.A\.S?\.?|S\.A\.R\.L\.?|SA|SAS|SARL|N\.V\.?|NV|B\.V\.?|BV|S\.p\.A\.?|SpA|AG|GmbH|KGaA|SE|AB|ASA|Oyj|LLC|PBC|Holdings)(?=\s|$|[,\.])\.?',
                '',
                official_name,
                flags=re.IGNORECASE
            ).strip(" ,.") or raw

            return ResolvedEntity(
                canonical_name=official_name,
                trade_name=clean_trade,
                legal_entity_name=official_name,
                entity_type="PUBLIC" if is_public else "PRIVATE",
                ticker=symbol,
                parent_company=None,
                parent_ticker=None,
                ownership_pct=f"Publicly Traded Corporation (Stock Ticker: {symbol})" if is_public else "Privately Held Enterprise",
                local_currency="USD",
                sector=sector,
                headquarters=headquarters,
                wikipedia_title=clean_trade.replace(" ", "_"),
                required_search_anchors=list(dict.fromkeys([
                    official_name,
                    clean_trade,
                    symbol,
                    sector
                ])),
                negative_keywords=["album", "song", "band", "movie", "obituary"]
            )

        try:
            prompt = f"""Disambiguate the corporate entity '{raw}' (region hint: {region_hint or 'Global'}, industry hint: {industry_hint or 'Unknown'}).
Use only live, verifiable corporate identity information. Return ONLY a JSON object with keys:
canonical_name, trade_name, legal_entity_name, entity_type ("PUBLIC"|"PRIVATE"|"SUBSIDIARY"), ticker (string or null),
parent_company (string or null), parent_ticker (string or null), local_currency, sector, headquarters,
wikipedia_title, required_search_anchors (list of 4-6 distinct domain/product/company anchors),
negative_keywords (list of 5-8 unrelated collision terms)."""
            response = self.generate_response(prompt)
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if parsed.get("canonical_name") and parsed.get("entity_type") in ("PUBLIC", "PRIVATE", "SUBSIDIARY"):
                    return ResolvedEntity(**parsed)
        except Exception:
            pass

        return ResolvedEntity(
            canonical_name=raw,
            trade_name=raw,
            legal_entity_name=raw,
            entity_type="PRIVATE",
            ticker=None,
            sector=industry_hint or "Undetermined",
            headquarters=region_hint or "Undetermined",
            wikipedia_title=raw.replace(" ", "_"),
            required_search_anchors=[f"{raw} company", f"{raw} corporate", raw],
            negative_keywords=["album", "song", "band", "movie", "obituary"]
        )
