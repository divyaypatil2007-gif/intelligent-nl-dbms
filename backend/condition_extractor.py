class ConditionExtractor:

    def __init__(self):
        pass

    def extract(self, tokens, linked_schema):

        """
        Extract WHERE condition from tokens.

        Returns:
        {
            "column": "...",
            "operator": "...",
            "value": "..."
        }

        or None
        """

        columns = linked_schema.get("select_columns", [])
        comparisons = linked_schema.get("comparisons", [])
        values = linked_schema.get("values", [])

        if len(columns) == 0:
            return None

        if len(comparisons) == 0:
            return None

        if len(values) == 0:
            return None

        return {
            "column": columns[-1],
            "operator": comparisons[0],
            "value": values[0]
        }