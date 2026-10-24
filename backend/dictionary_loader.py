import json
import os


class DictionaryLoader:

    def __init__(self):

        data_folder = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data"
        )

        self.dictionary = {}

        files = [
            "tables.json",
            "columns.json",
            "operations.json",
            "comparison.json",
            "logical.json",
            "sorting.json",
            "aggregates.json",
            "joins.json",
            "values.json"
        ]

        for file in files:

            path = os.path.join(data_folder, file)

            with open(path, "r", encoding="utf-8") as f:

                data = json.load(f)

                self.dictionary.update(data)

    def get_dictionary(self):

        return self.dictionary