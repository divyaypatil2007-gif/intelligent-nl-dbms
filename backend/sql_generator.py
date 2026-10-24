class SQLGenerator:

    def __init__(self):
        pass

    def generate(self, schema):

        query = ""

        # -------------------------
        # SELECT
        # -------------------------

        aggregate = schema.get("aggregate")
        columns = schema.get("select_columns", [])

        if aggregate:

            if len(columns) > 0:
                query += f"SELECT {aggregate}({columns[0]})"
            else:
                query += f"SELECT {aggregate}(*)"

        else:

            if len(columns) == 0:
                query += "SELECT *"
            else:
                query += "SELECT " + ", ".join(columns)

        # -------------------------
        # FROM
        # -------------------------

        table = schema.get("table")

        if table:
            query += f"\nFROM {table}"

        # -------------------------
        # JOIN
        # -------------------------

        joins = schema.get("joins")

        if joins:

            base = joins[0]

            for table_name in joins[1:]:

                query += f"\nJOIN {table_name}"

        # -------------------------
        # WHERE
        # -------------------------

        where = schema.get("where")

        if where:

            value = where["value"]

            if str(value).isdigit():
                value = value
            else:
                value = f"'{value}'"

            query += (
                f"\nWHERE {where['column']} "
                f"{where['operator']} "
                f"{value}"
            )

        # -------------------------
        # GROUP BY
        # -------------------------

        group = schema.get("group_by")

        if group:

            query += f"\nGROUP BY {group}"

        # -------------------------
        # HAVING
        # -------------------------

        having = schema.get("having")

        if having:

            query += (
                f"\nHAVING "
                f"{having['aggregate']}({having['column']}) "
                f"{having['operator']} "
                f"{having['value']}"
            )

        # -------------------------
        # ORDER BY
        # -------------------------

        order = schema.get("order_by")

        if order:

            query += (
                f"\nORDER BY "
                f"{order['column']} "
                f"{order['direction']}"
            )

        # -------------------------
        # LIMIT
        # -------------------------

        limit = schema.get("limit")

        if limit:

            query += f"\nLIMIT {limit}"

        query += ";"

        return query