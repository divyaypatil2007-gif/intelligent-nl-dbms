from backend.schema_linker import SchemaLinker


class RuleEngine:

    def __init__(self):
        # Use SchemaLinker to look up table column metadata for fallback resolution
        self._linker = SchemaLinker()

    def generate_sql(self, query):

        operation = query["operation"]
        table = query["table"]
        columns = query["select_columns"]
        aggregate = query["aggregate"]
        where = query["where"]
        order_by = query["order_by"]
        group_by = query["group_by"]
        having = query["having"]
        limit = query["limit"]

        if table is None:
            return None

        # -----------------------------
        # SELECT / AGGREGATE
        # -----------------------------

        if aggregate == "COUNT":

            if group_by:
                sql = f"SELECT {group_by}, COUNT(*) FROM {table}"
            else:
                sql = f"SELECT COUNT(*) FROM {table}"

        elif aggregate in ["SUM", "AVG", "MAX", "MIN"]:

            non_numeric = {
                "Customer_Name", "description", "address", "Email",
                "Warehouse_Name", "Location", "Manager", "Product_Name",
                "Category_Name", "Supplier_Name", "Unit", "payment_method",
                "Order_Status", "phone", "GST_NO", "Contact_Person",
                "Order_ID", "Customer_ID", "Supplier_ID", "Warehouse_ID",
                "Category_ID", "Product_ID", "Order_detail_id", "Supplier_order_id"
            }

            candidate_cols = [c for c in columns if c != "*" and c != group_by and c not in non_numeric]

            if candidate_cols:
                resolved = candidate_cols[0]
            else:
                numeric_priority = [
                    "Selling_Price",
                    "Cost_Price",
                    "Total_Amount",
                    "Subtotal",
                    "Purchase_Price",
                    "Quantity",
                ]

                table_columns = self._linker.get_table_columns(table)
                resolved = None

                for col in numeric_priority:
                    if col in table_columns:
                        resolved = col
                        break

            if resolved is None:
                return None

            if group_by:
                sql = f"SELECT {group_by}, {aggregate}({resolved}) FROM {table}"
            else:
                sql = f"SELECT {aggregate}({resolved}) FROM {table}"

        else:

            if columns == ["*"]:
                if group_by:
                    sql = f"SELECT {group_by} FROM {table}"
                else:
                    column_string = "*"
                    sql = f"SELECT {column_string} FROM {table}"
            else:
                cols_to_select = list(columns)
                if group_by and group_by not in cols_to_select:
                    cols_to_select.insert(0, group_by)
                column_string = ", ".join(cols_to_select)
                sql = f"SELECT {column_string} FROM {table}"

        # -----------------------------
        # WHERE
        # -----------------------------

        if where:

            column = where["column"]
            operator = where["operator"]
            value = where["value"]

            if operator == "BETWEEN":
                sql += f" WHERE {column} BETWEEN {value}"
            elif operator == "LIKE":
                sql += f" WHERE {column} LIKE '%{value}%'"
            elif operator == "STARTS_WITH":
                sql += f" WHERE {column} LIKE '{value}%'"
            elif operator == "ENDS_WITH":
                sql += f" WHERE {column} LIKE '%{value}'"
            elif str(value).isdigit():
                sql += f" WHERE {column} {operator} {value}"
            else:
                # Restore Title Case for string values (proper nouns like city names)
                formatted_value = str(value).title()
                if column in ["address", "Location", "description"] and operator == "=":
                    sql += f" WHERE {column} LIKE '%{formatted_value}%'"
                else:
                    sql += f" WHERE {column} {operator} '{formatted_value}'"

        # -----------------------------
        # GROUP BY
        # -----------------------------

        if group_by:

            sql += f" GROUP BY {group_by}"

        # -----------------------------
        # HAVING
        # -----------------------------

        if having:

            sql += (
                f" HAVING {having['aggregate']}({having['column']}) "
                f"{having['operator']} {having['value']}"
            )

        # -----------------------------
        # ORDER BY
        # -----------------------------

        if order_by:

            sql += f" ORDER BY {order_by['column']} {order_by['direction']}"

        # -----------------------------
        # LIMIT
        # -----------------------------

        if limit:

            sql += f" LIMIT {limit}"

        sql += ";"

        return sql