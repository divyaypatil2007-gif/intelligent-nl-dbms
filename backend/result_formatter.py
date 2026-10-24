class ResultFormatter:

    def __init__(self):
        pass

    def display(self, results):

        if results is None:
            print("No result returned.")
            return

        if len(results) == 0:
            print("No records found.")
            return

        print("-" * 80)

        for row in results:
            print(row)

        print("-" * 80)
