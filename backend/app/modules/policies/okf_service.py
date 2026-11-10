import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "policies"


class OKFPolicyService:
    """Open Knowledge Format (OKF) Policy Service with multi-tenant company isolation.

    Parses Markdown files with YAML frontmatter to provide zero-hallucination
    deterministic policy grounding to the AI supervisor and HR cockpit.
    """

    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.templates_dir = knowledge_dir / "templates"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._company_caches: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._ensure_templates()
        self.reload_policies()

    def _ensure_templates(self) -> None:
        """Ensure standard default starter templates exist."""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            starter_files = ["annual.md", "casual.md", "sick.md", "unpaid.md"]
            for sf in starter_files:
                src = self.knowledge_dir / sf
                if src.exists():
                    shutil.copy(src, self.templates_dir / sf)

    def _seed_company_templates(self, company_dir: Path) -> None:
        """Seeds the 4 pristine starter policies into a newly registered company's directory."""
        company_dir.mkdir(parents=True, exist_ok=True)
        # Copy from templates directory or knowledge directory
        source_dir = self.templates_dir if self.templates_dir.exists() else self.knowledge_dir
        for sf in ["annual.md", "casual.md", "sick.md", "unpaid.md"]:
            src = source_dir / sf
            if src.exists() and not (company_dir / sf).exists():
                shutil.copy(src, company_dir / sf)

    def get_company_dir(self, company_id: Optional[Union[uuid.UUID, str]] = None) -> Path:
        """Returns the isolated filesystem directory for a company, seeding defaults if new."""
        if not company_id:
            return self.templates_dir if self.templates_dir.exists() else self.knowledge_dir

        cid_str = str(company_id)
        c_dir = self.knowledge_dir / cid_str
        if not c_dir.exists() or not any(c_dir.glob("*.md")):
            self._seed_company_templates(c_dir)
        return c_dir

    def reload_policies(self, company_id: Optional[Union[uuid.UUID, str]] = None) -> None:
        """Scan directory and parse all OKF policy files into memory cache for a company or globally."""
        if company_id:
            cid_str = str(company_id)
            c_dir = self.get_company_dir(company_id)
            c_cache: Dict[str, Dict[str, Any]] = {}
            for file_path in c_dir.glob("*.md"):
                try:
                    text = file_path.read_text(encoding="utf-8")
                    policy_data = self._parse_okf_file(text, file_path.name)
                    code = policy_data.get("policy_code", file_path.stem.upper())
                    c_cache[code] = policy_data
                except Exception:
                    pass
            self._company_caches[cid_str] = c_cache
            return

        # Fallback / Global reload
        self._cache.clear()
        scan_dir = self.templates_dir if self.templates_dir.exists() else self.knowledge_dir
        for file_path in scan_dir.glob("*.md"):
            try:
                text = file_path.read_text(encoding="utf-8")
                policy_data = self._parse_okf_file(text, file_path.name)
                code = policy_data.get("policy_code", file_path.stem.upper())
                self._cache[code] = policy_data
            except Exception:
                pass

    def _get_cache(self, company_id: Optional[Union[uuid.UUID, str]] = None) -> Dict[str, Dict[str, Any]]:
        """Retrieve the in-memory policy cache for a specific company or global templates."""
        if not company_id:
            if not self._cache:
                self.reload_policies()
            return self._cache

        cid_str = str(company_id)
        if cid_str not in self._company_caches:
            self.reload_policies(company_id)
        return self._company_caches.get(cid_str, {})

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
            "leave_type": str(metadata.get("leave_type") or "casual").lower(),
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

    def list_policies(self, company_id: Optional[Union[uuid.UUID, str]] = None) -> List[Dict[str, Any]]:
        """Return all active OKF policy documents for a specific company."""
        return list(self._get_cache(company_id).values())

    def get_policy_by_type(
        self,
        leave_type: str,
        company_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find policy matching a specific leave type for a company."""
        target = leave_type.strip().lower()
        for p in self._get_cache(company_id).values():
            if p["leave_type"] == target:
                return p
        return None

    def get_policy_by_code(
        self,
        policy_code: str,
        company_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve policy by official policy code for a company."""
        return self._get_cache(company_id).get(policy_code.upper())

    def format_grounding_context(
        self,
        leave_type: str,
        company_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> str:
        """Format targeted OKF policy rules into high-density prompt text for LLM supervisor."""
        pol = self.get_policy_by_type(leave_type, company_id=company_id)
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

    def update_policy_content(
        self,
        policy_code: str,
        new_content: str,
        company_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Dict[str, Any]:
        """Update an OKF markdown document and refresh company cache."""
        target = self.get_policy_by_code(policy_code, company_id=company_id)
        if not target:
            raise ValueError(f"Policy code {policy_code} not found")

        target_dir = self.get_company_dir(company_id)
        filepath = target_dir / target["filename"]

        # Reconstruct with existing YAML frontmatter
        yaml_str = yaml.dump(target["metadata"], default_flow_style=False)
        full_text = f"---\n{yaml_str}---\n\n{new_content.strip()}\n"
        filepath.write_text(full_text, encoding="utf-8")

        self.reload_policies(company_id)
        return self.get_policy_by_code(policy_code, company_id)

    def create_or_upload_policy(
        self,
        filename: str,
        content: str,
        company_id: Optional[Union[uuid.UUID, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a new or updated policy document to the company's OKF directory."""
        target_dir = self.get_company_dir(company_id)

        safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename).lower()
        if not safe_name.endswith(".md"):
            safe_name = f"{safe_name.rsplit('.', 1)[0]}.md"

        filepath = target_dir / safe_name

        frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
        match = frontmatter_pattern.match(content)

        if match:
            full_text = content
        else:
            meta = metadata or {}
            leave_type = meta.get("leave_type", safe_name.replace(".md", "")).lower()
            code_prefix = leave_type[:3].upper()
            frontmatter_dict = {
                "policy_code": meta.get("policy_code", f"POL-{code_prefix}-01"),
                "title": meta.get("title", f"{leave_type.capitalize()} Leave Policy"),
                "leave_type": leave_type,
                "annual_allowance": int(meta.get("annual_allowance", 12)),
                "max_consecutive_days": int(meta.get("max_consecutive_days", 5)),
                "notice_period_days": int(meta.get("notice_period_days", 1)),
                "is_paid": bool(meta.get("is_paid", True)),
                "carryover_limit": int(meta.get("carryover_limit", 0)),
                "requires_manager_approval": bool(meta.get("requires_manager_approval", True)),
                "tags": [leave_type, "leave_policy", "hr"],
                "last_updated": "2026-11-06",
            }
            yaml_str = yaml.dump(frontmatter_dict, default_flow_style=False)
            full_text = f"---\n{yaml_str}---\n\n{content.strip()}\n"

        filepath.write_text(full_text, encoding="utf-8")
        self.reload_policies(company_id)

        parsed = self._parse_okf_file(full_text, safe_name)
        code = parsed.get("policy_code")
        return self.get_policy_by_code(code, company_id) or parsed


okf_service = OKFPolicyService()
