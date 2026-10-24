"""
backend/llm_router.py
----------------------
Local LLM handler via Ollama with Tier 3 Semantic Self-Correction Loop.

When a query is classified as HARD by ComplexityAnalyzer or falls back from RuleEngine,
this module calls the specialized local model (inventory-sql by default, trained on
inventory_management) with schema context, runs full semantic requirement & database
validation via QueryValidator, and auto-heals any wrong query before returning it to the user.
"""

import json
import re
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any, Tuple
from backend.schema_prompt import build_sql_prompt, get_schema_context
from backend.query_validator import QueryValidator


class LLMRouter:

    def __init__(self, model_name: str = "inventory-sql", host: str = "http://localhost:11434"):
        self.host = host
        self.api_url = f"{host}/api/generate"
        self.model_name = self._resolve_model(model_name)
        self.validator = QueryValidator()

    def _resolve_model(self, preferred_model: str) -> str:
        """Chooses preferred model if installed in Ollama, else falls back to base model."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                installed = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                if preferred_model in installed or f"{preferred_model}:latest" in installed:
                    return preferred_model
                if "inventory-sql" in installed:
                    return "inventory-sql"
                if "qwen2.5-coder:3b" in installed or "qwen2.5-coder" in installed:
                    return "qwen2.5-coder:3b"
        except Exception:
            pass
        return preferred_model

    def is_available(self) -> bool:
        """Check if Ollama server is running locally."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def clean_sql(self, sql: str, nl_query: Optional[str] = None) -> str:
        """Sanitizes generated SQL ensuring valid syntax and no markdown fences."""
        if not sql:
            return sql

        cleaned = sql.strip()

        # Strip markdown fences
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Fix truncated beginning (e.g. "IN supplier_order ..." -> "SELECT * FROM ...")
        if re.match(r'^(?:IN|JOIN)\s+', cleaned, re.IGNORECASE):
            cleaned = "SELECT * FROM products p " + cleaned

        # Replace standalone '?' placeholder with default ID 1
        cleaned = re.sub(r'=\s*\?', '= 1', cleaned)
        cleaned = re.sub(r'IN\s*\(\s*\?\s*\)', 'IN (1)', cleaned)

        # Remove trailing comments or extra whitespace
        cleaned = re.sub(r";\s*--.*$", ";", cleaned)

        # If user asked for entities in general without specific column attributes:
        # e.g., "Show suppliers except 'Patil Electronics'" or "Show products whose price is..."
        # and query has no JOINs: promote single/name column projection to SELECT *
        if nl_query:
            nl_low = nl_query.lower()
            entity_words = ["products", "suppliers", "customers", "warehouses", "orders", "inventory", "categories", "supplier", "product", "customer", "warehouse", "order"]
            asks_for_entity = any(
                re.search(rf"\b(?:show|get|display|list|find|fetch)\s+(?:all\s+)?{e}\b", nl_low)
                for e in entity_words
            )
            asks_specific_column = any(
                col_word in nl_low
                for col_word in [" name", " names", "price", "prices", "phone", "contact", "email", "address", "city", "location", " id", "status", "quantity", "stock"]
            )
            # If user asked for entities in general without specific column attributes:
            if asks_for_entity and not asks_specific_column and "JOIN" not in cleaned.upper():
                cleaned = re.sub(
                    r"^SELECT\s+(?:(?:\w+\.)?\w+(?:_Name)?(?:\s*,\s*(?:\w+\.)?\w+)?)\s+FROM\s+(\w+)",
                    r"SELECT * FROM \1",
                    cleaned,
                    flags=re.IGNORECASE
                )

        # Ensure query ends with semicolon
        if not cleaned.endswith(";"):
            cleaned += ";"

        return cleaned

    def _call_ollama(self, prompt: str, system: Optional[str] = None) -> str:
        """Sends request to Ollama generate API."""
        if not self.is_available():
            raise urllib.error.URLError(f"Ollama server is not running locally at {self.host}.")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": -1,  # Keep model permanently warm in GPU memory
            "options": {
                "temperature": 0.0,
                "num_predict": 512
            }
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return resp_data.get("response", "").strip()

    def heal_query(
        self,
        nl_query: str,
        broken_sql: str,
        issues: List[str],
        linked_schema: Optional[Dict[str, Any]] = None,
        max_attempts: int = 2
    ) -> Dict[str, Any]:
        """
        Tier 3 LLM Self-Correction Loop:
        Sends the user request, the broken candidate SQL, and the exact validation issues
        back to the local LLM to automatically heal the query.
        """
        current_sql = broken_sql
        current_explanation = "Query repaired via Self-Correction Loop."
        issues_fixed = list(issues)
        detected_tables = (
            (linked_schema.get("joins") or ([linked_schema.get("table")] if linked_schema.get("table") else []))
            if linked_schema else []
        )
        system_instruction, _ = build_sql_prompt(nl_query, detected_tables)
        schema_info = get_schema_context()

        for attempt in range(1, max_attempts + 1):
            formatted_issues = "\n".join([f"- {iss}" for iss in issues])
            correction_prompt = (
                f"{schema_info}\n\n"
                f"User Request: \"{nl_query}\"\n\n"
                f"Candidate SQL Generated: `{current_sql}`\n\n"
                f"VALIDATION FAILED with the following issue(s):\n"
                f"{formatted_issues}\n\n"
                f"CRITICAL REPAIR TASK:\n"
                f"1. Fix EVERY issue listed above so the query satisfies 100% of the user's natural language requirements.\n"
                f"2. Ensure the query is valid MySQL 8 and uses ONLY real tables and columns from the schema.\n"
                f"3. Return ONLY valid JSON with 'sql' and 'explanation' fields.\n\n"
                f"JSON Response:"
            )

            try:
                response_text = self._call_ollama(prompt=correction_prompt, system=system_instruction)
                clean_json_str = response_text
                if clean_json_str.startswith("```"):
                    clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str, flags=re.IGNORECASE)
                    clean_json_str = re.sub(r"\s*```$", "", clean_json_str).strip()

                parsed = json.loads(clean_json_str)
                candidate_healed_sql = self.clean_sql(parsed.get("sql", "").strip(), nl_query=nl_query)
                candidate_explanation = parsed.get("explanation", current_explanation).strip()

                # Re-validate candidate healed query
                is_valid, remaining_issues = self.validator.validate(nl_query, candidate_healed_sql, linked_schema=linked_schema)
                if is_valid:
                    return {
                        "sql": candidate_healed_sql,
                        "explanation": f"Auto-Healed: {candidate_explanation}",
                        "auto_healed": True,
                        "original_sql": broken_sql,
                        "issues_fixed": issues_fixed,
                        "attempts": attempt
                    }
                else:
                    # Update for next iteration if attempts remain
                    current_sql = candidate_healed_sql
                    issues = remaining_issues
            except Exception:
                break

        # Fallback heuristic if LLM is offline or could not completely resolve:
        # e.g., missing limit
        healed_heuristic = current_sql
        limit_match = re.search(r'\b(?:top|first|last|limit)\s+(\d+)\b', nl_query.lower())
        if limit_match and "LIMIT" not in healed_heuristic.upper():
            n = limit_match.group(1)
            healed_heuristic = healed_heuristic.rstrip(";").strip() + f" LIMIT {n};"
            is_valid, _ = self.validator.validate(nl_query, healed_heuristic, linked_schema=linked_schema)
            if is_valid:
                return {
                    "sql": healed_heuristic,
                    "explanation": f"Auto-Healed: Attached missing LIMIT {n} clause.",
                    "auto_healed": True,
                    "original_sql": broken_sql,
                    "issues_fixed": issues_fixed,
                    "attempts": attempt
                }

        return {
            "sql": current_sql,
            "explanation": current_explanation,
            "auto_healed": False,
            "original_sql": broken_sql,
            "issues_fixed": [],
            "attempts": max_attempts
        }

    def validate_and_heal(
        self,
        nl_query: str,
        sql: str,
        tokens: Optional[List[Dict[str, Any]]] = None,
        linked_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Universal Validator & Healer:
        Inspects ANY candidate query (from RuleEngine OR LLM).
        If issues are found, activates Tier 3 self-correction to heal it before display.
        """
        if not sql:
            return {
                "sql": None,
                "explanation": "No query generated to validate.",
                "auto_healed": False,
                "is_valid": False,
                "issues": ["Empty SQL query."]
            }

        is_valid, issues = self.validator.validate(nl_query, sql, tokens=tokens, linked_schema=linked_schema)

        if is_valid:
            return {
                "sql": sql,
                "explanation": None,
                "auto_healed": False,
                "is_valid": True,
                "issues": []
            }

        # Query has errors or misses user requirements -> trigger auto-healing
        heal_result = self.heal_query(
            nl_query=nl_query,
            broken_sql=sql,
            issues=issues,
            linked_schema=linked_schema
        )
        heal_result["is_valid"] = (heal_result.get("auto_healed") is True)
        heal_result["issues"] = issues
        return heal_result

    def query(self, nl_query: str, linked_schema: dict, signals: list) -> dict:
        """
        Route a HARD query to the local LLM with schema context, then validate and auto-heal.
        """
        detected_tables = linked_schema.get("joins") or ([linked_schema.get("table")] if linked_schema.get("table") else [])
        system_instruction, user_prompt = build_sql_prompt(nl_query, detected_tables)

        try:
            response_text = self._call_ollama(prompt=user_prompt, system=system_instruction)

            # Strip possible markdown wrapper
            clean_json_str = response_text
            if clean_json_str.startswith("```"):
                clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str, flags=re.IGNORECASE)
                clean_json_str = re.sub(r"\s*```$", "", clean_json_str).strip()

            try:
                parsed = json.loads(clean_json_str)
                sql = self.clean_sql(parsed.get("sql", "").strip(), nl_query=nl_query)
                explanation = parsed.get("explanation", "").strip()
            except json.JSONDecodeError:
                sql = self.clean_sql(response_text, nl_query=nl_query)
                explanation = "Query generated from natural language intent."

            # Tier 3 Auto-Healing Validation
            validated_res = self.validate_and_heal(
                nl_query=nl_query,
                sql=sql,
                linked_schema=linked_schema
            )

            if validated_res.get("auto_healed"):
                sql = validated_res["sql"]
                explanation = validated_res.get("explanation") or explanation

            return {
                "sql": sql,
                "explanation": explanation,
                "signals": signals,
                "auto_healed": validated_res.get("auto_healed", False),
                "issues_fixed": validated_res.get("issues_fixed", [])
            }

        except urllib.error.URLError:
            return {
                "sql": None,
                "explanation": (
                    f"Ollama server is not reachable at {self.host}. "
                    f"Please ensure Ollama is installed and running (`ollama serve`), "
                    f"and model '{self.model_name}' is downloaded (`ollama create inventory-sql -f models/Modelfile`)."
                ),
                "signals": signals,
                "auto_healed": False
            }
        except Exception as e:
            return {
                "sql": None,
                "explanation": f"LLM error: {str(e)}",
                "signals": signals,
                "auto_healed": False
            }
