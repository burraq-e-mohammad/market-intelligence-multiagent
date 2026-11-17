from agents.base_agent import BaseAgent
from tools.wiki_tool import get_company_biography
from typing import Dict, Any

class BiographyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Company Biographer",
            role="Chief Corporate Historian & Strategic Moat Analyst",
            system_prompt="""You are a senior corporate historian and strategic enterprise analyst.
Your job is to provide an in-depth, structured, and comprehensive corporate biography for the target enterprise.
Do NOT give a short or superficial summary. Never output apologies, refusal disclaimers, or meta-commentary about missing data.
If the company is a privately held or unlisted technology enterprise, synthesize its commercial footprint, core engineering offerings, strategic acquisitions, awards, and market delivery scale into 3 clearly marked sections:
### 1. Foundational History, Origins & Leadership Milestones
Detail the founding era, commercial evolution, geographic delivery footprint, major acquisitions, and key corporate inflection points.
### 2. Core Business Divisions, Solutions & Ecosystem
Explain what the company actually builds, its primary service lines (e.g. digital transformation, product engineering, cloud, AI, cybersecurity), and enterprise industry solutions.
### 3. Competitive Moat & Strategic Industry Positioning
Analyze structural advantages (domain engineering talent, enterprise client retention, specialized vertical consulting, and technology partnerships)."""
        )

    def analyze(self, company_name: str) -> Dict[str, Any]:
        """
        1. Calls the biography tool (Wikipedia verified sections or corporate media announcements).
        2. Reasons through corporate history and moat using the LLM.
        3. Returns structured, extensive corporate background.
        """
        tool_result = get_company_biography(company_name)
        source = tool_result.get("source", "Verified Profile")
        summary = tool_result.get("summary", "")
        detailed_content = tool_result.get("detailed_content", summary)

        prompt = f"""You are the Chief Corporate Historian & Strategic Enterprise Analyst.
Synthesize an authoritative, comprehensive corporate biography for {company_name} based on this verified {source} intelligence:

{detailed_content}

Strict Output Requirements:
1. Deliver comprehensive, professional, multi-paragraph corporate analysis.
2. Structure your response into exactly 3 detailed sections:
### 1. Foundational History, Origins & Leadership Milestones
### 2. Core Business Divisions, Solutions & Ecosystem
### 3. Competitive Moat & Strategic Industry Positioning
3. Synthesize all verified commercial milestones, acquisitions, recognitions, and technology services mentioned above.
4. Do NOT output disclaimers, apologies, or meta-notes. Write an authoritative, executive-level corporate biography."""

        llm_analysis = self.generate_response(prompt)
        
        # Fallback if in heuristic mode
        if "Report]" in llm_analysis:
            llm_analysis = (
                f"### 1. Foundational History, Origins & Leadership Milestones\n"
                f"{summary}\n\n"
                f"### 2. Core Business Divisions, Solutions & Ecosystem\n"
                f"{company_name} delivers specialized enterprise technology, software engineering, and digital modernization services across its target regional and global markets. "
                f"The organization leverages structured business units to deliver agile development, cloud migration, and data intelligence.\n\n"
                f"### 3. Competitive Moat & Strategic Industry Positioning\n"
                f"The firm's competitive moat is reinforced by deep client relationships, high switching costs for mission-critical systems, "
                f"and certified technology delivery partnerships with global software vendors."
            )

        return {
            "status": "success",
            "source": source,
            "url": tool_result.get("url", ""),
            "analysis": llm_analysis
        }
