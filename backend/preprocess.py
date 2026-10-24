import re
import spacy


class Preprocessor:

    def __init__(self):

        self.nlp = spacy.load("en_core_web_sm")

        # Multi-word phrases used in our project
        self.phrase_map = {

            "greater than or equal to": "greater_than_equal",
            "less than or equal to": "less_than_equal",

            "greater than": "greater_than",
            "less than": "less_than",

            "more than": "more_than",

            "not equal to": "not_equal",
            "equal to": "equal",

            "starts with": "starts_with",
            "ends with": "ends_with",

            "order by": "order_by",
            "group by": "group_by",

            "ascending order": "ascending_order",
            "descending order": "descending_order",

            "how many": "how_many",

            # COUNT phrasings: collapse to unambiguous token
            "total number of": "total_number_of",
            "number of": "number_of",

            # Sorting compound phrasings: collapse to sorting-dict tokens
            # so "lowest first" is never mistaken as the MIN aggregate
            "highest first": "highest_first",
            "lowest first": "lowest_first",
            "largest first": "largest_first",
            "smallest first": "smallest_first",
            "newest first": "newest_first",
            "oldest first": "oldest_first",
            "a to z": "a_to_z",
            "z to a": "z_to_a",
            "most expensive": "most_expensive",
            "least expensive": "least_expensive",
            "who ordered": "who_ordered",
            "who placed": "who_placed",
            "placed by": "placed_by",
            "supplied by": "supplied_by",
            "delivered to": "delivered_to",
            "out of stock": "out_of_stock",
            "in stock": "in_stock",
        }

    def normalize_word_numbers(self, query):
        """Converts number words (e.g. 'five' -> '5', 'twenty five' -> '25') to digits."""
        small_nums = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
            "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
            "eighty": 80, "ninety": 90
        }
        pattern = r'\b(' + '|'.join(small_nums.keys()) + r')\b'
        res = re.sub(pattern, lambda m: str(small_nums[m.group(0).lower()]), query, flags=re.IGNORECASE)
        # Handle 'N hundred' -> N00, 'N thousand' -> N000
        res = re.sub(r'(\d+)\s+hundred\b', lambda m: str(int(m.group(1)) * 100), res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s+thousand\b', lambda m: str(int(m.group(1)) * 1000), res, flags=re.IGNORECASE)
        # Handle '20 5' -> 25 (tens + units)
        res = re.sub(r'\b([2-9]0)\s+([1-9])\b', lambda m: str(int(m.group(1)) + int(m.group(2))), res)
        return res

    def preprocess(self, query):

        query = query.lower()

        # Normalize number words (e.g. 'five' -> '5', 'twenty five' -> '25')
        query = self.normalize_word_numbers(query)

        # Handle pluralization annotations like customer(s) -> customers, product(s) -> products
        query = re.sub(r'\(s\)', 's', query)
        query = re.sub(r'[(),!?";:]', ' ', query)

        # Normalize currency symbols and prefixes (₹, $, rs, rs., inr)
        query = query.replace("₹", " ").replace("$", " ")
        query = re.sub(r'\b(?:rs\.?|inr)\b', ' ', query, flags=re.IGNORECASE)

        # Replace multi-word phrases first
        for phrase, replacement in sorted(
            self.phrase_map.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):
            query = query.replace(phrase, replacement)

        doc = self.nlp(query)

        tokens = []

        for token in doc:

            if token.is_punct:
                continue

            if token.is_space:
                continue

            tokens.append({

                "text": token.text,
                "lemma": token.lemma_.lower(),
                "pos": token.pos_,
                "is_stop": token.is_stop,
                "is_number": token.like_num

            })

        return tokens
