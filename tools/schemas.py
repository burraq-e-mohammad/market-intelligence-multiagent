from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any
import re


class VerifiedOfficer(BaseModel):
    """
    Strict Pydantic schema for a verified corporate officer.
    Prevents misattributed titles (e.g. assigning 'CEO' to executives from other companies
    mentioned in news/Wikipedia body text, or listing multiple simultaneous CEOs).
    """
    name: str = Field(..., min_length=3, max_length=80)
    title: str = Field(..., min_length=2, max_length=120)
    role_category: Literal[
        "INTERIM_CEO", "CEO", "CHAIR", "CFO", "PRESIDENT", "COO", "EXECUTIVE"
    ] = "EXECUTIVE"
    is_former: bool = False
    source: str = "Verified Filing"
    priority: int = 3  # Lower is higher authority: 1=Breaking News/SEC, 2=Registry, 3=Infobox

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        # Remove honorific prefixes like Mr., Ms., Dr.
        cleaned = re.sub(r'^(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s+', '', v.strip())
        # Collapse whitespace
        cleaned = " ".join(cleaned.split())
        # Reject clearly invalid non-person phrases
        invalid_tokens = {
            "the", "company", "corporation", "board", "committee", "executive",
            "chief", "officer", "interim", "president", "chairman", "founder",
            "inc", "ltd", "llc", "corp", "group", "holdings"
        }
        words = [w.lower().strip(".,") for w in cleaned.split()]
        if len(words) < 2 or len(words) > 4:
            raise ValueError(f"Invalid person name length: '{cleaned}'")
        if words[0] in invalid_tokens or words[-1] in invalid_tokens:
            raise ValueError(f"Non-person token in officer name: '{cleaned}'")
        return cleaned

    def formatted(self) -> str:
        return f"{self.name} ({self.title})"


class FiscalCalendarContext(BaseModel):
    """
    Universal Fiscal Calendar Grounding model.
    Maps calendar dates to any company's exact fiscal year and fiscal quarter.
    """
    fiscal_year_end_month: int = Field(12, ge=1, le=12)
    fiscal_year_end_label: str = "December 31 (Calendar Year)"
    is_calendar_year: bool = True
    current_fiscal_year: int
    current_fiscal_quarter: str
    most_recent_reported_quarter: str
    most_recent_quarter_end_label: str
    quarter_mapping_summary: str


class VerifiedEntityProfile(BaseModel):
    """
    Standardized, schema-validated corporate entity profile consumed by all agents.
    """
    company_name: str
    founding_info: str = ""
    active_officers: List[VerifiedOfficer] = Field(default_factory=list)
    verified_leadership: List[str] = Field(default_factory=list)
    verified_acquisitions: List[str] = Field(default_factory=list)
    verified_segments: List[str] = Field(default_factory=list)
    breaking_governance: List[str] = Field(default_factory=list)
    breaking_regulatory: List[str] = Field(default_factory=list)


def classify_role_category(title: str) -> Literal[
    "INTERIM_CEO", "CEO", "CHAIR", "CFO", "PRESIDENT", "COO", "EXECUTIVE"
]:
    """Deterministically categorize a corporate officer title with strict precedence."""
    t = title.lower()
    if "interim ceo" in t or "interim chief executive" in t or "acting ceo" in t:
        return "INTERIM_CEO"
    if "chief executive" in t or re.search(r'\bceo\b', t):
        return "CEO"
    if "chair" in t:
        return "CHAIR"
    if "chief financial" in t or re.search(r'\bcfo\b', t):
        return "CFO"
    if "chief operating" in t or re.search(r'\bcoo\b', t):
        return "COO"
    if "president" in t:
        return "PRESIDENT"
    return "EXECUTIVE"


def parse_officer_string(raw: str, source: str = "Verified Source", priority: int = 2) -> Optional[VerifiedOfficer]:
    """Parse strings like 'Colette Kress (Interim CEO & CFO)' into a validated VerifiedOfficer."""
    m = re.match(r'^([^\(]+?)\s*\(([^\)]+)\)\s*$', raw.strip())
    if not m:
        return None
    name, title = m.group(1).strip(), m.group(2).strip()
    is_former = any(tok in title.lower() for tok in ["former", "ex-", "resigned", "retired", "departed"])
    try:
        return VerifiedOfficer(
            name=name,
            title=title,
            role_category=classify_role_category(title),
            is_former=is_former,
            source=source,
            priority=priority
        )
    except Exception:
        return None


def reconcile_officers(
    candidates: List[VerifiedOfficer],
    breaking_governance: Optional[List[str]] = None
) -> List[VerifiedOfficer]:
    """
    Universal Strict Role-Binding & Cardinality Enforcer:
    1. Marks any executive mentioned as resigning/stepping down in breaking governance news as former.
    2. Extracts newly appointed Interim CEO / CEO / Chair from breaking governance disclosures.
    3. Deduplicates officers by normalized name (retaining highest-authority source/title).
    4. Enforces singular C-suite cardinality:
       - At most ONE active CEO / Interim CEO per company (if Interim CEO exists, drops stale CEO entries).
       - Never allows noisy co-occurrence scrapes to list 3-4 simultaneous 'CEOs'.
    """
    gov_texts = breaking_governance or []
    combined_gov = " ".join(gov_texts)

    # 1. Detect executives who resigned / stepped down in breaking governance news
    departed_names = set()
    resign_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s+(?:has\s+)?(?:resigned|resigns|stepped down|steps down|departed|exited|ousted)',
        r'(?:resignation|departure|exit)\s+of\s+(?:former\s+)?(?:CEO\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)'
    ]
    for pat in resign_patterns:
        for m in re.finditer(pat, combined_gov):
            departed_names.add(m.group(1).strip().lower())

    # 2. Detect newly appointed leaders from breaking governance disclosures
    extracted_from_gov: List[VerifiedOfficer] = []
    role_group = r'(Interim CEO(?:\s*&\s*CFO)?|Chief Executive Officer|CEO|Chair(?:man)? of the Board|Board Chair)'
    name_group = r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)'
    appt_patterns = [
        (rf'(?:appointed|named|names)\s+(?:CFO\s+)?{name_group}\s+(?:as\s+)?{role_group}', 1),
        (rf'(?:and|,)\s+(?:CFO\s+)?{name_group}\s+as\s+{role_group}', 1),
        (rf'{name_group}\s+(?:was\s+)?(?:appointed|named|became)\s+(?:as\s+)?{role_group}', 1),
    ]
    for pat, prio in appt_patterns:
        for m in re.finditer(pat, combined_gov):
            cand_name, cand_title = m.group(1).strip(), m.group(2).strip()
            try:
                extracted_from_gov.append(
                    VerifiedOfficer(
                        name=cand_name,
                        title=cand_title,
                        role_category=classify_role_category(cand_title),
                        is_former=False,
                        source="Breaking Governance Disclosure",
                        priority=prio
                    )
                )
            except Exception:
                pass

    all_cands = extracted_from_gov + list(candidates)

    # 3. Mark departed executives as former and deduplicate by name (keeping best priority)
    by_name: Dict[str, VerifiedOfficer] = {}
    for officer in all_cands:
        norm_key = re.sub(r'\s+[a-z]\.?\s+', ' ', officer.name.lower()).strip()
        is_departed = any(
            norm_key == re.sub(r'\s+[a-z]\.?\s+', ' ', d).strip() or officer.name.lower() == d
            for d in departed_names
        )
        if is_departed or officer.is_former:
            continue

        existing = by_name.get(norm_key)
        if not existing:
            by_name[norm_key] = officer
        else:
            # Prefer lower priority number (higher authority); break ties by more specific title
            if officer.priority < existing.priority:
                by_name[norm_key] = officer
            elif officer.priority == existing.priority:
                if officer.role_category == "INTERIM_CEO" and existing.role_category != "INTERIM_CEO":
                    by_name[norm_key] = officer
                elif len(officer.title) > len(existing.title):
                    by_name[norm_key] = officer

    active = sorted(by_name.values(), key=lambda o: (o.priority, 0 if o.role_category in ("INTERIM_CEO", "CEO") else 1))

    # 4. Enforce Singular CEO / Interim CEO Cardinality
    has_interim_ceo = any(o.role_category == "INTERIM_CEO" for o in active)
    final_officers: List[VerifiedOfficer] = []
    ceo_slot_filled = False

    for officer in active:
        if officer.role_category == "INTERIM_CEO":
            if not ceo_slot_filled:
                final_officers.append(officer)
                ceo_slot_filled = True
        elif officer.role_category == "CEO":
            if has_interim_ceo or ceo_slot_filled:
                # Skip duplicate/stale CEO when an Interim CEO or higher-priority CEO is already bound
                continue
            final_officers.append(officer)
            ceo_slot_filled = True
        else:
            final_officers.append(officer)

    return final_officers[:6]
