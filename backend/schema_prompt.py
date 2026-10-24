"""
backend/schema_prompt.py
-------------------------
Helper to format database schema (tables, columns, foreign keys/joins)
into a structured prompt for the LLM to achieve high accuracy on HARD queries.
"""

from backend.dictionary_loader import DictionaryLoader


def expand_bridge_tables(detected_tables: list) -> list:
    """
    Expands detected tables with intermediate bridge tables to prevent
    hallucinated direct joins.
    """
    if not detected_tables:
        return []
    tables = set(detected_tables)

    # Customer and products require customer_order and customer_order_details
    if "customer" in tables and "products" in tables:
        tables.add("customer_order")
        tables.add("customer_order_details")
    elif "customer" in tables and "customer_order_details" in tables:
        tables.add("customer_order")
    elif "customer_order" in tables and "products" in tables:
        tables.add("customer_order_details")

    # Supplier and products require supplier_order
    if "supplier" in tables and "products" in tables:
        tables.add("supplier_order")

    # Warehouse and products require inventory
    if "warehouse" in tables and "products" in tables:
        tables.add("inventory")

    # Category and customer require products and orders
    if "category" in tables and "customer" in tables:
        tables.add("products")
        tables.add("customer_order")
        tables.add("customer_order_details")

    return sorted(list(tables))


def get_schema_context():
    loader = DictionaryLoader()
    dictionary = loader.get_dictionary()

    columns = dictionary.get("columns", {})
    joins = dictionary.get("joins", [])

    lines = ["MySQL Database Schema (`inventory_management`):"]
    for table_name in columns:
        cols = list(columns[table_name].keys())
        lines.append(f"- Table `{table_name}`: columns = [{', '.join(cols)}]")

    if joins:
        lines.append("\nForeign Key Relationships / Direct Joins:")
        for j in joins:
            left_t = j["left_table"]
            left_c = j["left_column"]
            right_t = j["right_table"]
            right_c = j["right_column"]
            lines.append(f"- `{left_t}`.`{left_c}` = `{right_t}`.`{right_c}`")

    lines.append("\nMandatory Multi-Table Relational Paths:")
    lines.append("- Customer <-> Products: customer c -> customer_order co (on Customer_ID) -> customer_order_details cod (on Order_ID) -> products p (on Product_ID)")
    lines.append("  (CRITICAL: customer_order_details DOES NOT have Customer_ID. NEVER write cod.Customer_ID = c.Customer_ID!)")
    lines.append("- Supplier <-> Products: supplier s -> supplier_order so (on Supplier_ID) -> products p (on Product_ID)")
    lines.append("  (CRITICAL: products DOES NOT have Supplier_ID. NEVER write p.Supplier_ID = s.Supplier_ID!)")
    lines.append("- Products <-> Warehouse: products p -> inventory i (on Product_ID) -> warehouse w (on Warehouse_ID)")
    lines.append("- Products <-> Category: products p -> category c (on Category_ID)")
    lines.append("\nDate & Time Filter Rules:")
    lines.append("- Relative dates: for 'last N days/months', use `Order_Date >= CURDATE() - INTERVAL N DAY/MONTH`")
    lines.append("- Calendar months/years: use `MONTH(Order_Date) = N` or `YEAR(Order_Date) = YYYY`")
    lines.append("- Date ranges: use `Order_Date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`")
    lines.append("\nHAVING Clause Rules:")
    lines.append("- For group-level aggregate filters (e.g. 'categories with more than N products', 'customers who placed > N orders', 'spending > N'):")
    lines.append("  Use `GROUP BY <entity_id>, <entity_name> HAVING <aggregate_condition>`. NEVER place aggregate functions (COUNT, SUM, AVG) in WHERE!")
    lines.append("\nAnti-Join / Negative Existence Rules:")
    lines.append("- For 'never ordered', 'no orders', 'never supplied':")
    lines.append("  Use `LEFT JOIN ... WHERE <joined_key> IS NULL` or `NOT EXISTS`.")
    lines.append("  Example: `SELECT p.Product_ID, p.Product_Name FROM products p LEFT JOIN customer_order_details cod ON p.Product_ID = cod.Product_ID WHERE cod.Product_ID IS NULL;`")

    return "\n".join(lines)


def build_sql_prompt(nl_query: str, detected_tables: list = None):
    schema_info = get_schema_context()

    expanded_tables = expand_bridge_tables(detected_tables) if detected_tables else []
    tables_hint = ""
    if expanded_tables:
        tables_hint = f"\nTables likely relevant (including required bridges): {', '.join([f'`{t}`' for t in expanded_tables])}"

    system_instruction = (
        "You are an expert MySQL database query assistant trained specifically on the `inventory_management` database. "
        "Convert the user's natural language request into a valid, executable SQL query for MySQL 8.\n\n"
        "STRICT SQL RULES:\n"
        "1. Output ONLY valid JSON with exactly two fields: 'sql' and 'explanation'.\n"
        "2. The SQL must be 100% COMPLETE and EXECUTABLE. NEVER use placeholders like '?', '$1', or ':param'.\n"
        "3. NEVER invent non-existent columns. customer_order_details has NO Customer_ID. products has NO Supplier_ID.\n"
        "4. Always use table aliases and explicit JOIN ON conditions.\n"
        "5. End every query with a semicolon `;`.\n"
        "6. Do NOT include markdown blocks or backticks outside the JSON response.\n"
        "7. Complete Entity Detail Rule: When the user asks to show, display, find, get, or list whole entities in general (e.g. 'Show products...', 'Show suppliers...', 'Show customers...', 'Show orders...', 'List warehouses...', 'Show suppliers except X'), and does NOT explicitly ask for specific individual columns (such as 'only names', 'just phone numbers', 'names and prices'), select ALL columns using `SELECT * FROM <table>` (or `SELECT <table>.*`) so that complete entity details are returned!\n"
        "   Example: \"Show suppliers except 'Patil Electronics'\" -> `SELECT * FROM supplier WHERE Supplier_Name != 'Patil Electronics';`\n"
        "   Example: \"Show products whose price is between 500 and 2000\" -> `SELECT * FROM products WHERE Selling_Price BETWEEN 500 AND 2000;`\n\n"
        "Example Response Format:\n"
        "{\n"
        '  "sql": "SELECT p.Product_Name, c.Customer_Name FROM products p JOIN customer_order_details cod ON p.Product_ID = cod.Product_ID JOIN customer_order co ON cod.Order_ID = co.Order_ID JOIN customer c ON co.Customer_ID = c.Customer_ID;",\n'
        '  "explanation": "Joins products through customer_order_details and customer_order to customer to find customers who purchased each product."\n'
        "}\n"
    )

    user_prompt = (
        f"{schema_info}\n"
        f"{tables_hint}\n\n"
        f"User Question: \"{nl_query}\"\n\n"
        "JSON Response:"
    )

    return system_instruction, user_prompt
