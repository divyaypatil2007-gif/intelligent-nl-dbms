class QueryBuilder:

    def __init__(self):
        pass

    def build(self, linked_schema):

        query = {}

        query["operation"] = linked_schema["operation"]
        query["table"] = linked_schema["table"]

        if len(linked_schema["select_columns"]) == 0:
            query["select_columns"] = ["*"]
        else:
            query["select_columns"] = linked_schema["select_columns"]

        query["where"] = linked_schema["where"]
        query["aggregate"] = linked_schema["aggregate"]
        query["order_by"] = linked_schema["order_by"]

        # New fields
        query["group_by"] = linked_schema.get("group_by")
        query["having"] = linked_schema.get("having")
        query["limit"] = linked_schema.get("limit")

        # Forward joins (not yet used by rule_engine, reserved for future)
        query["joins"] = linked_schema.get("joins")

        return query