import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "policies"


class OKFPolicyService:
    """Open Knowledge Format (OKF) Policy Service.

    Parses Markdown files with YAML frontmatter to provide zero-hallucination
    deterministic policy grounding to the AI supervisor and HR cockpit.
    """

    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.reload_policies()

    def reload_policies(self) -> None:
        """Scan directory and parse all OKF policy files into memory cache."""
        self._cache.clear()
        if not self.knowledge_dir.exists():
            return

        for file_path in self.knowledge_dir.glob("*.md"):
            try:
                text = file_path.read_text(encoding="utf-8")
                policy_data = self._parse_okf_file(text, file_path.name)
                code = policy_data.get("policy_code", file_path.stem.upper())
                self._cache[code] = policy_data
            except Exception as e:
                pass

    def _parse_okf_file(self, raw_text: str, filename: str) -> Dict[str, Any]:
        """Extract YAML frontmatter and Markdown body."""
        frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
        match = frontmatter_pattern.match(raw_text)

        if match:
            yaml_content = match.group(1)
            body = raw_text[match.end() :].strip()
            metadata = yaml.safe_load(yaml_content) or {}
        else:
            metadata = {"title": filename.replace(".md", "").capitalize()}
            body = raw_text.strip()

        return {
            "policy_code": metadata.get("policy_code", "POL-GEN-00"),
            "title": metadata.get("title", "Company Policy"),
            "leave_type": metadata.get("leave_type", "casual").lower(),
            "annual_allowance": metadata.get("annual_allowance", 0),
            "max_consecutive_days": metadata.get("max_consecutive_days", 5),
            "notice_period_days": metadata.get("notice_period_days", 1),
            "is_paid": metadata.get("is_paid", True),
            "carryover_limit": metadata.get("carryover_limit", 0),
            "requires_manager_approval": metadata.get("requires_manager_approval", True),
            "tags": metadata.get("tags", []),
            "last_updated": metadata.get("last_updated", "2026-11-06"),
            "metadata": metadata,
            "markdown_content": body,
            "filename": filename,
        }

    def list_policies(self) -> List[Dict[str, Any]]:
        """Return all active OKF policy documents."""
        return list(self._cache.values())

    def get_policy_by_type(self, leave_type: str) -> Optional[Dict[str, Any]]:
        """Find policy matching a specific leave type (e.g. 'casual', 'sick', 'annual', 'unpaid')."""
        target = leave_type.strip().lower()
        for p in self._cache.values():
            if p["leave_type"] == target:
                return p
        return None

    def get_policy_by_code(self, policy_code: str) -> Optional[Dict[str, Any]]:
        """Retrieve policy by official policy code (e.g. 'POL-CAS-01')."""
        return self._cache.get(policy_code.upper())

    def format_grounding_context(self, leave_type: str) -> str:
        """Format targeted OKF policy rules into high-density prompt text for LLM supervisor."""
        pol = self.get_policy_by_type(leave_type)
        if not pol:
            return "General Company Leave Policy: Standard manager approval required."

        return (
            f"Official Policy: {pol['title']} [{pol['policy_code']}]\n"
            f"- Paid Status: {'Paid' if pol['is_paid'] else 'Unpaid (Loss of Pay applies)'}\n"
            f"- Annual Entitlement: {pol['annual_allowance']} days\n"
            f"- Advance Notice Required: {pol['notice_period_days']} days\n"
            f"- Max Consecutive Block: {pol['max_consecutive_days']} days\n"
            f"- Verbatim Policy Clauses:\n{pol['markdown_content'][:400]}..."
        )

    def update_policy_content(self, policy_code: str, new_content: str) -> Dict[str, Any]:
        """Update an OKF markdown document and refresh cache."""
        target = self.get_policy_by_code(policy_code)
        if not target:
            raise ValueError(f"Policy code {policy_code} not found")

        filepath = self.knowledge_dir / target["filename"]
        # Reconstruct with existing YAML frontmatter
        yaml_str = yaml.dump(target["metadata"], default_flow_style=False)
        full_text = f"---\n{yaml_str}---\n\n{new_content.strip()}\n"
        filepath.write_text(full_text, encoding="utf-8")

        self.reload_policies()
        return self.get_policy_by_code(policy_code)


okf_service = OKFPolicyService()
