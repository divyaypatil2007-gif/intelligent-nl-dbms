import re


def explain_query_metadata(sql: str, complexity: str, primary_table: str, joins: list = None) -> dict:
    """
    Extracts table names, column names, and generates human-readable
    explanations detailing where records are retrieved from.
    """
    if not sql:
        return {
            "tables": [],
            "source_description": "No SQL query generated."
        }

    # Extract tables mentioned
    tables_found = set()
    if joins:
        for t in joins:
            tables_found.add(t)
    if primary_table:
        tables_found.add(primary_table)

    # Regex search for FROM and JOIN table references
    matches = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z_0-9]+)', sql, flags=re.IGNORECASE)
    for m in matches:
        tables_found.add(m.lower())

    tables_list = sorted(list(tables_found))

    if len(tables_list) == 1:
        source_desc = f"Records are queried directly from the primary table `{tables_list[0]}`."
    elif len(tables_list) > 1:
        tables_formatted = ", ".join([f"`{t}`" for t in tables_list])
        source_desc = f"Records are combined across multiple tables ({tables_formatted}) using relational foreign key links."
    else:
        source_desc = "Records are retrieved based on the database schema relationships."

    return {
        "tables": tables_list,
        "source_description": source_desc
    }
