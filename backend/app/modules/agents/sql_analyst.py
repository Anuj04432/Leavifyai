import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.llm_client import MultiProviderLLMRouter

logger = logging.getLogger("leavify.agents.sql_analyst")

WORKFORCE_SCHEMA = """
Database Schema (PostgreSQL):
1. employees:
   - id: UUID (Primary Key)
   - company_id: UUID (Must filter by company_id = :company_id)
   - employee_code: VARCHAR
   - first_name: VARCHAR
   - last_name: VARCHAR
   - email: VARCHAR
   - designation: VARCHAR
   - department_id: UUID (Foreign Key -> departments.id)
   - date_of_joining: DATE
   - date_of_exit: DATE
   - employment_type: VARCHAR ('full_time', 'part_time', 'contract')
   - salary_basic: NUMERIC (Monthly basic salary)
   - is_active: BOOLEAN

2. departments:
   - id: UUID (Primary Key)
   - company_id: UUID (Filter by company_id = :company_id)
   - name: VARCHAR
   - description: TEXT

3. leave_requests:
   - id: UUID (Primary Key)
   - employee_id: UUID (Foreign Key -> employees.id)
   - leave_policy_id: UUID (Foreign Key -> leave_policies.id)
   - start_date: DATE
   - end_date: DATE
   - total_days: NUMERIC
   - reason: TEXT
   - status: VARCHAR ('pending', 'approved', 'rejected', 'cancelled')
   - is_paid: BOOLEAN
   - created_at: TIMESTAMP

4. leave_balances:
   - id: UUID (Primary Key)
   - employee_id: UUID (Foreign Key -> employees.id)
   - leave_policy_id: UUID (Foreign Key -> leave_policies.id)
   - year: INTEGER
   - total_allocated: NUMERIC
   - used: NUMERIC
   - pending: NUMERIC
   - carried_forward: NUMERIC

5. leave_policies:
   - id: UUID (Primary Key)
   - company_id: UUID (Filter by company_id = :company_id)
   - name: VARCHAR
   - leave_type: VARCHAR ('annual', 'sick', 'casual', 'unpaid')
   - days_allowed: NUMERIC
   - is_paid: BOOLEAN
"""

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE|COMMIT|ROLLBACK|REPLACE|VACUUM|MERGE|CREATE)\b",
    re.IGNORECASE,
)


class ExecutiveSQLAnalyst:
    """
    Safe Read-Only Text-to-SQL Engine for Executives, HR, and Management.
    Empowers higher leadership to ask any organizational, headcount, or leave question.
    Enforces strict multi-tenancy and read-only execution guardrails.
    """

    def __init__(self, db: AsyncSession, company_id: uuid.UUID, llm: MultiProviderLLMRouter):
        self.db = db
        self.company_id = company_id
        self.llm = llm

    def is_analytical_query(self, prompt: str) -> bool:
        """Determines if prompt requires database analytics / lookup."""
        low = prompt.lower().strip()
        keywords = [
            "similar name", "same name", "duplicate", "how many", "headcount",
            "most leave", "most leaves", "who took", "who has taken", "department",
            "joined", "hire", "who is", "list employee", "list staff", "top leave",
            "frequent leave", "leave record", "balance", "breakdown", "average",
            "active employee", "inactive", "designation", "role", "organization", "company",
            "salary", "compensation", "highest", "lowest", "least", "fewer", "less leaves",
            "sick leave", "casual leave", "annual leave", "used leave", "all the leaves",
            "took leave", "took leaves", "which employee", "which employe", "names of",
            "names", "name", "who are", "those employee", "those employees", "employee name"
        ]
        return any(k in low for k in keywords)

    def validate_sql(self, sql: str) -> bool:
        """Enforces read-only safety on generated queries."""
        cleaned = sql.strip().strip(";").strip()
        if not re.match(r"^\s*(SELECT|WITH)\s+", cleaned, re.IGNORECASE):
            return False
        if FORBIDDEN_SQL_PATTERNS.search(cleaned):
            return False
        return True

    async def generate_sql(self, question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Prompts LLM to convert question into a clean PostgreSQL SELECT query with optional conversation context."""
        history_context = ""
        if chat_history:
            recent_turns = [
                f"{item.get('role', 'user').capitalize()}: {item.get('content', '')}"
                for item in chat_history[-4:]
            ]
            history_context = "Recent Conversation Context:\n" + "\n".join(recent_turns) + "\n\n"

        system_instruction = (
            f"You are a PostgreSQL Database Expert for Leavify.ai.\n{WORKFORCE_SCHEMA}\n"
            "Rules for writing SQL:\n"
            "1. ONLY write a single read-only SELECT or WITH statement.\n"
            "2. ALWAYS scope to the current company by filtering with `company_id = :company_id` (or joining tables that have company_id).\n"
            "3. Use standard PostgreSQL functions (e.g. COUNT, SUM, AVG, ILIKE, LOWER, DATE_TRUNC).\n"
            "4. NEVER write INSERT, UPDATE, DELETE, or DDL statements.\n"
            "5. If the user refers to pronouns like 'those employees' or 'them', resolve them from the conversation context.\n"
            "6. Return ONLY the raw SQL query. Do not wrap in markdown or explanation."
        )
        content_prompt = f"{history_context}Current Question: {question}"
        raw_sql = await self.llm.generate_text(system_instruction, content_prompt)
        if not raw_sql:
            return None

        clean_sql = raw_sql.strip()
        if clean_sql.startswith("```"):
            clean_sql = clean_sql.split("\n", 1)[1]
            if clean_sql.endswith("```"):
                clean_sql = clean_sql.rsplit("```", 1)[0]
            if clean_sql.startswith("sql"):
                clean_sql = clean_sql[3:].strip()

        clean_sql = clean_sql.strip().rstrip(";")
        if "LIMIT" not in clean_sql.upper():
            clean_sql += " LIMIT 50"

        return clean_sql

    async def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Safely executes the validated SQL query with company_id binding."""
        if not self.validate_sql(sql):
            logger.warning(f"Rejected unsafe SQL query: {sql}")
            return []

        try:
            res = await self.db.execute(text(sql), {"company_id": str(self.company_id)})
            rows = [dict(r._mapping) for r in res.fetchall()]
            return rows
        except Exception as e:
            logger.warning(f"Error executing SQL analyst query: {e}")
            return []

    async def answer_question(self, question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Full pipeline: Question (+ Context) -> SQL -> Execution -> Natural Executive Summary."""
        sql = await self.generate_sql(question, chat_history=chat_history)
        if not sql or not self.validate_sql(sql):
            return None

        rows = await self.execute_query(sql)

        # Format rows into natural answer
        formatting_instruction = (
            "You are the Leavify.ai Executive Intelligence Analyst.\n"
            f"The user asked: '{question}'\n"
            f"The database returned these records (JSON):\n{json.dumps(rows, default=str)}\n"
            "Summarize the answer clearly and concisely for an executive / HR manager. "
            "Use bullet points or bold numbers where appropriate. If no records were found, explain clearly."
        )
        answer = await self.llm.generate_text(formatting_instruction, "Provide executive summary.")
        return answer
