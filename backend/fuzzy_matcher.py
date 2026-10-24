"""

backend/fuzzy_matcher.py

-------------------------

Fuzzy typo and entity matching using RapidFuzz.

Auto-corrects misspelled product names, cities, categories, supplier names,

and common database terminology before query processing.



Guards against false positives by ensuring valid English query words,

prepositions, sorting terms, and numbers are never altered.

"""



from rapidfuzz import process, fuzz

from rapidfuzz.distance import Levenshtein

from backend.dictionary_loader import DictionaryLoader





class FuzzyMatcher:



    # Recognized English query words, sorting instructions, and verbs that MUST NOT be altered

    ENGLISH_QUERY_WORDS = {

        # Query verbs & action words

        "show", "list", "find", "get", "give", "display", "all", "each", "every",

        "who", "what", "which", "whose", "where", "how", "many", "much", "having",

        "placed", "ordered", "bought", "sold", "added", "created", "stored",

        "supplied", "paying", "paid", "arranged", "sort", "sorted", "sorting", "ranking",

        "order", "orders", "group", "grouped", "from", "to", "into", "register", "registered", "registration", "exist", "existing", "present", "there",

        # Prepositions, articles & conjunctions

        "a", "an", "the", "in", "on", "at", "by", "for", "with", "without",

        "of", "and", "or", "not", "is", "are", "was", "were", "be", "been",

        "through", "across", "between", "than", "as", "like", "such",

        # Comparatives, Superlatives & Sorting terms

        "more", "less", "greater", "fewer", "above", "below", "under", "over",

        "higher", "lower", "highest", "lowest", "most", "least", "cheapest",

        "expensive", "costliest", "best", "worst", "maximum", "minimum", "max", "min",

        "top", "first", "last", "bottom", "ascending", "descending", "asc", "desc",

        # Scope, completeness and detail terms

        "complete", "completed", "full", "entire", "everything", "detail", "details",

        "information", "info", "data", "attribute", "attributes", "field", "fields",

        # Price and financial terms

        "costing", "priced", "cost", "costs", "price", "prices", "pricing",

        "rate", "rates", "value", "values", "amount", "total", "average", "count",

        "sum", "avg", "record", "records", "item", "items", "stock",

        "quantity", "quantities", "number", "numbers", "name", "names", "id", "ids", "unit", "units",

        # Temporal & Date words

        "yesterday", "today", "tomorrow", "day", "days", "week", "weeks",

        "month", "months", "year", "years", "recent", "recently", "latest", "earliest",

        "january", "february", "march", "april", "may", "june", "july",

        "august", "september", "october", "november", "december"

    }



    def __init__(self):

        self._build_vocabulary()



    def _build_vocabulary(self):

        loader = DictionaryLoader()

        dictionary = loader.get_dictionary()



        self.vocab = set()

        self.canonical_map = {}



        # 1. Add table synonyms (both singular and plural)

        for tbl, syns in dictionary.get("tables", {}).items():

            self.vocab.add(tbl.lower())

            self.vocab.add(tbl.lower() + "s")

            self.canonical_map[tbl.lower()] = tbl

            for s in syns:

                s_lower = s.lower()

                self.vocab.add(s_lower)

                self.vocab.add(s_lower + "s")

                self.canonical_map[s_lower] = s



        # 2. Add column synonyms

        for tbl, cols in dictionary.get("columns", {}).items():

            for col, syns in cols.items():

                self.vocab.add(col.lower())

                self.canonical_map[col.lower()] = col

                for s in syns:

                    s_lower = s.lower()

                    self.vocab.add(s_lower)

                    self.canonical_map[s_lower] = s



        # 3. Add values (payment methods, statuses)

        for cat, vals in dictionary.get("values", {}).items():

            for v_name, syns in vals.items():

                self.vocab.add(v_name.lower())

                self.canonical_map[v_name.lower()] = v_name

                for s in syns:

                    s_lower = s.lower()

                    self.vocab.add(s_lower)

                    self.canonical_map[s_lower] = s



        # 4. Add common domain keywords

        domain_keywords = [

            "laptop", "mouse", "keyboard", "oil", "rice", "kurti", "jeans", "shirt",

            "football", "racket", "electronics", "grocery", "clothing", "sports",

            "stationery", "beauty", "pune", "mumbai", "delhi", "nagpur", "bangalore",

            "patil electronics", "sharma traders", "delivered", "pending", "shipped",

            "cancelled", "upi", "cash", "card", "net banking", "stock", "quantity",

            "warranty", "expensive", "cheapest", "revenue", "spending", "orders"

        ]

        for kw in domain_keywords:

            self.vocab.add(kw.lower())

            self.canonical_map[kw.lower()] = kw



        # 5. Populate actual values from Database if reachable

        try:

            from backend.database import Database

            db = Database()

            # Fetch product names

            db.cursor.execute("SELECT Product_Name FROM products LIMIT 100;")

            for (pname,) in db.cursor.fetchall():

                p_lower = pname.lower()

                self.vocab.add(p_lower)

                self.canonical_map[p_lower] = pname



            # Fetch suppliers

            db.cursor.execute("SELECT Supplier_Name FROM supplier LIMIT 50;")

            for (sname,) in db.cursor.fetchall():

                s_lower = sname.lower()

                self.vocab.add(s_lower)

                self.canonical_map[s_lower] = sname



            # Fetch customers

            db.cursor.execute("SELECT Customer_Name FROM customer LIMIT 50;")

            for (cname,) in db.cursor.fetchall():

                c_lower = cname.lower()

                self.vocab.add(c_lower)

                self.canonical_map[c_lower] = cname



            db.close()

        except Exception:

            pass



        self.vocab_list = list(self.vocab)



    def correct_query(self, query: str, threshold: float = 75.0) -> tuple[str, list[dict]]:

        """

        Scans words in the query for close typos against domain vocabulary.

        Preserves valid English query words, sorting terms, and numbers.

        Returns the corrected query and a list of corrections made.

        """

        words = query.split()

        corrected_words = []

        corrections = []



        i = 0

        while i < len(words):

            word = words[i]

            clean_word = word.strip(".,!?()\"';:").lower()



            # 1. Skip if it is a number, short token, recognized English word, or already in vocabulary

            if (

                clean_word in self.ENGLISH_QUERY_WORDS

                or clean_word in self.vocab

                or clean_word.isdigit()

                or len(clean_word) < 4

            ):

                corrected_words.append(word)

                i += 1

                continue



            # 2. Check 2-word phrase if next word exists

            matched_phrase = False

            if i + 1 < len(words):

                w2 = words[i + 1]

                w2_clean = w2.strip(".,!?()\"';:").lower()

                two_word = f"{clean_word} {w2_clean}"



                # If the exact 2-word phrase is already known, do not alter

                if two_word in self.vocab:

                    corrected_words.append(f"{word} {w2}")

                    i += 2

                    matched_phrase = True

                    continue



                # Only attempt 2-word fuzzy match if at least ONE of the words is NOT an English query word

                if not (clean_word in self.ENGLISH_QUERY_WORDS and w2_clean in self.ENGLISH_QUERY_WORDS):

                    candidates = [v for v in self.vocab_list if " " in v and abs(len(v) - len(two_word)) <= 3]

                    if candidates:

                        match = process.extractOne(two_word, candidates, scorer=fuzz.ratio, score_cutoff=85.0)

                        if match:

                            best_match, score, _ = match

                            canonical = self.canonical_map.get(best_match, best_match)

                            corrections.append({

                                "original": two_word,

                                "corrected": canonical,

                                "score": round(score, 1)

                            })

                            corrected_words.append(canonical)

                            i += 2

                            matched_phrase = True

                            continue



            # 3. Single-word fuzzy match (with strict edit distance constraints)

            if not matched_phrase:

                candidates = [v for v in self.vocab_list if " " not in v and abs(len(v) - len(clean_word)) <= 2]

                if candidates:

                    match = process.extractOne(clean_word, candidates, scorer=fuzz.ratio, score_cutoff=threshold)

                    if match:

                        best_match, score, _ = match

                        dist = Levenshtein.distance(clean_word, best_match)

                        max_allowed_dist = 2 if len(clean_word) < 8 else 3



                        if dist <= max_allowed_dist:

                            canonical = self.canonical_map.get(best_match, best_match)

                            corrections.append({

                                "original": clean_word,

                                "corrected": canonical,

                                "score": round(score, 1)

                            })

                            corrected_words.append(canonical)

                            i += 1

                            continue



                # No match or distance too high -> keep original word

                corrected_words.append(word)

                i += 1



        corrected_query = " ".join(corrected_words)

        return corrected_query, corrections

