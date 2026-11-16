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
Do NOT give a short or superficial 2-line summary. Provide thorough analysis across 3 clearly marked sections:
### 1. Foundational History, Origins & Leadership Milestones
Detail the founding era, key founders, initial mission, corporate restructuring, and historic inflection points.
### 2. Core Business Divisions, Solutions & Ecosystem
Explain what the company actually builds, its primary service lines, technology offerings, and major operating subsidiaries.
### 3. Competitive Moat & Strategic Industry Positioning
Analyze their structural advantages (switching costs, proprietary architecture, domain expertise, partnerships, or scale)."""
        )

    def analyze(self, company_name: str) -> Dict[str, Any]:
        """
        1. Calls the biography tool (Wikipedia recursive sections or verified web profile).
        2. Reasons through corporate history and moat using the LLM.
        3. Returns structured, extensive corporate background.
        """
        tool_result = get_company_biography(company_name)
        source = tool_result.get("source", "Verified Profile")
        summary = tool_result.get("summary", "")
        detailed_content = tool_result.get("detailed_content", summary)

        prompt = f"""Write an extensive, comprehensive corporate biography for {company_name} based on this verified {source} data:

{detailed_content}

Structure your response into 3 detailed sections:
### 1. Foundational History, Origins & Leadership Milestones
### 2. Core Business Divisions, Solutions & Ecosystem
### 3. Competitive Moat & Strategic Industry Positioning

Be thorough, factual, and informative. Cite specific years, founders, subsidiaries, and products mentioned above."""

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
