import time
from backend.database import Database


class SQLExecutor:

    def __init__(self):
        self.db = Database()

    def execute_with_metrics(self, sql):
        """
        Executes a SQL query and returns execution time, row count,
        column names, and records.

        Returns
        -------
        dict:
            {
                "success": bool,
                "columns": list of str,
                "rows": list of tuples,
                "row_count": int,
                "execution_time_sec": float,
                "formatted_time": str (e.g. "9 rows in set (0.14 sec)"),
                "error": str or None
            }
        """
        if not sql:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_sec": 0.0,
                "formatted_time": "0 rows in set (0.00 sec)",
                "error": "No SQL query provided."
            }

        start_time = time.perf_counter()
        try:
            self.db.cursor.execute(sql)
            rows = self.db.cursor.fetchall()
            elapsed = time.perf_counter() - start_time

            # Extract column headers
            columns = [col[0] for col in self.db.cursor.description] if self.db.cursor.description else []
            row_count = len(rows)

            row_label = "row" if row_count == 1 else "rows"
            formatted_time = f"{row_count} {row_label} in set ({elapsed:.2f} sec)"

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "execution_time_sec": round(elapsed, 4),
                "formatted_time": formatted_time,
                "error": None
            }

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_sec": round(elapsed, 4),
                "formatted_time": f"0 rows in set ({elapsed:.2f} sec)",
                "error": str(e)
            }

    def execute(self, sql):
        """Legacy helper for backward compatibility."""
        result = self.execute_with_metrics(sql)
        return result["rows"] if result["success"] else None