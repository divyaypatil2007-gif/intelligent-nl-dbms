"""
backend/date_parser.py
-----------------------
Parses relative and calendar date expressions into valid MySQL date clauses.
Supports phrases like:
- "last 7 days", "past 30 days", "last month", "last 6 months"
- "in 2025", "in January 2025", "yesterday", "today"
- "between 2025-01-01 and 2025-01-31"
"""

import re
from datetime import datetime


class DateParser:

    MONTHS = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }

    def parse_date_expression(self, query: str, date_column: str = "Order_Date") -> tuple[str | None, str | None]:
        """
        Extracts a SQL condition and human-readable explanation from a query.
        Returns: (sql_condition, explanation) or (None, None)
        """
        q = query.lower()

        # 1. ISO Date Range: "between YYYY-MM-DD and YYYY-MM-DD"
        iso_range = re.search(r'between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})', q)
        if iso_range:
            d1, d2 = iso_range.groups()
            return f"{date_column} BETWEEN '{d1}' AND '{d2}'", f"Filtered between {d1} and {d2}"

        # 2. Relative days: "last N days" / "past N days"
        rel_days = re.search(r'(?:in\s+the\s+|within\s+the\s+|during\s+the\s+)?(?:last|past)\s+(\d+)\s+days?', q)
        if rel_days:
            n = rel_days.group(1)
            return f"{date_column} >= CURDATE() - INTERVAL {n} DAY", f"Within the last {n} days"

        # 3. Relative months: "last N months" / "past N months"
        rel_months = re.search(r'(?:in\s+the\s+|within\s+the\s+|during\s+the\s+)?(?:last|past)\s+(\d+)\s+months?', q)
        if rel_months:
            n = rel_months.group(1)
            return f"{date_column} >= CURDATE() - INTERVAL {n} MONTH", f"Within the last {n} months"

        # 4. "last month" / "past month"
        if re.search(r'\b(?:last|past)\s+month\b', q):
            return f"{date_column} >= CURDATE() - INTERVAL 1 MONTH", "Within the last month"

        # 5. "last week" / "past week"
        if re.search(r'\b(?:last|past)\s+week\b', q):
            return f"{date_column} >= CURDATE() - INTERVAL 7 DAY", "Within the last 7 days"

        # 6. "yesterday"
        if re.search(r'\byesterday\b', q):
            return f"{date_column} = CURDATE() - INTERVAL 1 DAY", "Placed yesterday"

        # 7. "today"
        if re.search(r'\btoday\b', q):
            return f"{date_column} = CURDATE()", "Placed today"

        # 8. Specific Month + Year: "in January 2025"
        for m_name, m_num in self.MONTHS.items():
            pattern = rf'\b(?:in\s+)?{m_name}\s+(\d{{4}})\b'
            m_match = re.search(pattern, q)
            if m_match:
                yr = m_match.group(1)
                return f"MONTH({date_column}) = {m_num} AND YEAR({date_column}) = {yr}", f"In {m_name.title()} {yr}"

        # 9. Specific Month only: "in January"
        for m_name, m_num in self.MONTHS.items():
            pattern = rf'\b(?:in\s+|for\s+)?{m_name}\b'
            if re.search(pattern, q):
                return f"MONTH({date_column}) = {m_num}", f"In {m_name.title()}"

        # 10. Specific Year: "in 2025" / "year 2025" (must be preceded by in/year/during/of/for)
        yr_match = re.search(r'\b(?:in|year|during|of|for)\s+(20\d\d|19\d\d)\b', q)
        if yr_match and "day" not in q:
            prefix = q[:yr_match.start()]
            if not re.search(r'\b(?:between|price|cost|amount|quantity|id|rs|inr|\$)\b', prefix):
                yr = yr_match.group(1)
                return f"YEAR({date_column}) = {yr}", f"In year {yr}"

        return None, None
