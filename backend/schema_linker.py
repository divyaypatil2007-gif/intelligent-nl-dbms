import re
from backend.dictionary_loader import DictionaryLoader





class SchemaLinker:



    def __init__(self):



        loader = DictionaryLoader()

        self.dictionary = loader.get_dictionary()



        self.tables = self.dictionary["tables"]

        self.columns = self.dictionary["columns"]

        self.operations = self.dictionary["operations"]

        self.comparisons = self.dictionary["comparison_operators"]

        self.aggregates = self.dictionary["aggregate_functions"]

        self.sorting = self.dictionary["sorting"]



    # --------------------------------------------------

    # Detect Operation

    # --------------------------------------------------



    def find_operation(self, tokens):



        for token in tokens:



            word = token["lemma"]



            for operation, synonyms in self.operations.items():



                if word in synonyms:

                    return operation



        return "SELECT"



    # --------------------------------------------------

    # Detect Table

    # --------------------------------------------------



    def find_table(self, tokens):



        # Direct table detection



        for token in tokens:



            word = token["lemma"]



            for table, synonyms in self.tables.items():



                if word in synonyms:

                    return table



        # Infer table from column names



        return self.infer_table_from_columns(tokens)



    # --------------------------------------------------

    # Get Columns

    # --------------------------------------------------



    def get_table_columns(self, table):



        if table is None:

            return {}



        return self.columns.get(table, {})



    # --------------------------------------------------

    # Detect Aggregate

    # --------------------------------------------------



    def find_aggregate(self, tokens):



        for token in tokens:



            word = token["lemma"]



            for aggregate, synonyms in self.aggregates.items():



                if word in synonyms:

                    return aggregate



        return None



    # --------------------------------------------------

    # Detect SELECT Columns

    # --------------------------------------------------



    def find_select_columns(self, tokens, table, joins=None):

        selected_columns = []

        # Check if user explicitly requested complete details / all columns / everything
        query_text = " ".join(t.get("text", "").lower() for t in tokens)
        query_lemmas = " ".join(t.get("lemma", "").lower() for t in tokens)

        all_details_intent = (
            "complete detail" in query_lemmas or "complete details" in query_text
            or "all detail" in query_lemmas or "all details" in query_text
            or "full detail" in query_lemmas or "full details" in query_text
            or "entire detail" in query_lemmas or "entire details" in query_text
            or "everything" in query_lemmas or "everything" in query_text
            or "all column" in query_lemmas or "all columns" in query_text
            or "all information" in query_text or "complete information" in query_text
            or "all data" in query_text or "complete data" in query_text
            or "complete record" in query_lemmas or "complete records" in query_text
            or "all record" in query_lemmas or "all records" in query_text
            or (("complete" in query_lemmas or "full" in query_lemmas) and ("detail" in query_lemmas or "info" in query_lemmas or "information" in query_lemmas))
        )

        if all_details_intent:
            return ["*"]

        # Identify filter / condition boundary (e.g. "where", "whose", "with", "except", "having", "greater", "between")
        filter_start_idx = len(tokens)
        filter_boundary_words = {
            "where", "whose", "with", "having", "except", "excluding", "without",
            "between", "greater", "less", "above", "below", "exceeding", "equal",
            ">", "<", "=", "!=", "<>", ">=", "<=",
            "less_than", "greater_than", "more_than", "at_least", "at_most",
            "costing", "priced", "costs", "pricing", "under", "over", "after", "before",
            "during", "within", "located", "based", "situated", "placed", "totaling", "amounting"
        }
        for i, t in enumerate(tokens):
            w = t["text"].lower()
            l = t["lemma"].lower()
            if w in filter_boundary_words or l in filter_boundary_words:
                filter_start_idx = i
                break

        # Only examine projection tokens before the filter condition starts
        proj_tokens = tokens[:filter_start_idx]

        # Table-level entity words that identify the table, NOT specific columns
        table_entity_words = {
            "product", "products", "item", "items", "goods",
            "supplier", "suppliers", "vendor", "vendors",
            "customer", "customers", "client", "clients",
            "warehouse", "warehouses", "storage",
            "order", "orders"
        }

        # Check if user explicitly asked for name/title (e.g. "product name", "names", "title")
        explicit_name_requested = any(
            t["text"].lower() in {"name", "names", "title", "titles"} or
            t["lemma"].lower() in {"name", "title"}
            for t in proj_tokens
        )

        # Collect columns from primary table, and from joined tables if present
        tables_to_search = joins if (joins and len(joins) > 1) else [table]
        for tbl in tables_to_search:
            tbl_columns = self.get_table_columns(tbl)
            if not tbl_columns:
                continue

            for token in proj_tokens:
                word = token["lemma"].lower()
                text_lower = token["text"].lower()

                if text_lower in {"show", "get", "find", "list", "display", "fetch", "give", "tell", "all", "top", "the", "a", "an", "of", "in", "and", "or"}:
                    continue

                if (word in table_entity_words or text_lower in table_entity_words) and not explicit_name_requested:
                    continue

                for column, synonyms in tbl_columns.items():
                    if column.endswith("_Name") and not explicit_name_requested and (word in table_entity_words or text_lower in table_entity_words):
                        continue

                    if word in synonyms or text_lower in synonyms:
                        if column not in selected_columns:
                            selected_columns.append(column)

        if len(selected_columns) == 0:
            return ["*"]

        return selected_columns


    # Detect Comparison Operator

    # --------------------------------------------------



    def find_comparison(self, tokens):



        # Weak copula/prepositions that should not override explicit comparisons

        weak_synonyms = {"is", "in", "at"}



        detected_op = None

        for token in tokens:

            word_lemma = token["lemma"]

            word_text = token["text"].lower()

            for operator, synonyms in self.comparisons.items():

                match = (word_lemma in synonyms) or (word_text in synonyms)

                if match:

                    if word_text not in weak_synonyms and word_lemma not in weak_synonyms:

                        # Found an explicit comparison (e.g. greater_than, less_than, equal, between)

                        return operator

                    elif detected_op is None:

                        detected_op = operator



        return detected_op



        # --------------------------------------------------



    # Detect Value

    # --------------------------------------------------



    def find_value(self, tokens, comparison_index=-1):
        # Check for quoted string first (e.g. 'Patil Electronics' or "Patil Electronics")
        query_full = " ".join(t.get("text", "") for t in tokens)
        quoted_match = re.search(r"['\"]([^'\"]+)['\"]", query_full)
        if quoted_match:
            return quoted_match.group(1).strip()




        # Build ignore set: common SQL words + all table synonyms + all column synonyms + stopwords

        # This prevents table/column keywords, prepositions, articles, and stopwords from being mistaken as filter values



        ignore_words = {

            "show", "get", "display", "list", "find", "give", "tell", "fetch",

            "where", "whose", "with", "without", "in", "at", "of", "from", "to", "by", "for", "on", "into",

            "the", "a", "an", "this", "that", "these", "those", "all", "any", "some", "every", "each",

            "both", "few", "more", "most", "other", "such", "no", "nor", "not", "only", "own", "same",

            "so", "than", "too", "very", "can", "will", "just", "should", "now",

            "what", "which", "who", "whom", "whose", "how", "many", "much",

            "greater", "less", "equal", "than", "above", "below", "over", "under", "higher", "lower",

            "highest", "lowest", "maximum", "minimum", "average", "avg", "total",

            "count", "sum", "top", "first", "last", "limit",

            "sort", "sorted", "ascending", "descending", "order", "ordered",

            "group", "per", "each", "all", "every", "by", "wise",

            "locate", "located", "locating", "situated", "based", "living",

            "named", "called", "having", "is", "are", "was", "were", "be", "been", "being",

            "register", "registered", "registration", "exist", "existing", "present", "active", "there", "available", "record", "recorded"

        }



        # Add all table-name synonyms and their individual words

        for synonyms in self.tables.values():

            for s in synonyms:

                ignore_words.add(s)

                for part in s.split():

                    ignore_words.add(part)



        # Add all column-name synonyms and their individual words

        for table_cols in self.columns.values():

            for synonyms in table_cols.values():

                for s in synonyms:

                    ignore_words.add(s)

                    for part in s.split():

                        ignore_words.add(part)



        # Add aggregate synonyms and their individual words

        for synonyms in self.aggregates.values():

            for s in synonyms:

                ignore_words.add(s)

                for part in s.split():

                    ignore_words.add(part)



        # Add sorting synonyms and their individual words

        for synonyms in self.sorting.values():

            for s in synonyms:

                ignore_words.add(s)

                for part in s.split():

                    ignore_words.add(part)



        # 1. If comparison operator index is known, prioritize tokens AFTER the operator

        if comparison_index != -1:

            if comparison_index + 1 < len(tokens):

                after_tokens = tokens[comparison_index + 1:]

                # 1a. Numeric value after operator

                for token in after_tokens:

                    if token["is_number"]:

                        return token["text"]

                # 1b. Non-ignored word(s) after operator (e.g. "Pune", "Patil Electronics", "UPI")
                val_words = []
                for token in after_tokens:
                    w = token["text"]
                    if token["lemma"] not in ignore_words and token["text"].lower() not in ignore_words:
                        if w.isalnum() or w in {"&", "-", "_"}:
                            val_words.append(w)
                if val_words:
                    return " ".join(val_words).title()

            # If comparison operator was specified but no value exists after it, do NOT scan before it

            return None



        # 2. First preference across all tokens: numeric value

        for token in tokens:

            if token["is_number"]:

                return token["text"]



        # 3. Fallback: string value across all tokens

        for token in tokens:

            if token["is_number"]:

                continue



            word = token["text"]



            if token["lemma"] in ignore_words or token["text"].lower() in ignore_words:

                continue



            if word.isalpha():

                return word



        return None



    # --------------------------------------------------

    # Detect WHERE Clause

    # --------------------------------------------------



    def find_where(self, tokens, table):



        table_columns = self.get_table_columns(table)



        if not table_columns:

            return None



        # Collect all table synonyms to check if prepositions are pointing to tables

        all_table_synonyms = set()

        for synonyms in self.tables.values():

            for s in synonyms:

                all_table_synonyms.add(s)

                for part in s.split():

                    all_table_synonyms.add(part)



        operator = self.find_comparison(tokens)



        if operator is None:

            return None



        comparison_index = -1

        weak_synonyms = {"is", "in", "at", "from", "of"}



        # First try to find explicit non-weak operator token

        for i, token in enumerate(tokens):

            word_lemma = token["lemma"]

            word_text = token["text"].lower()

            for op, synonyms in self.comparisons.items():

                if ((word_lemma in synonyms) or (word_text in synonyms)) and op == operator:

                    if word_text not in weak_synonyms and word_lemma not in weak_synonyms:

                        comparison_index = i

                        break

            if comparison_index != -1:

                break



        # Fallback to weak matching token for the operator ONLY IF it does not introduce a table name

        if comparison_index == -1:

            for i, token in enumerate(tokens):

                word_lemma = token["lemma"]

                word_text = token["text"].lower()

                for op, synonyms in self.comparisons.items():

                    if ((word_lemma in synonyms) or (word_text in synonyms)) and op == operator:

                        # Check if token points to a table (e.g. "in [the] inventory", "at [the] warehouse")

                        next_idx = i + 1

                        if next_idx < len(tokens) and tokens[next_idx]["lemma"] in {"the", "a", "an"}:

                            next_idx += 1

                        if next_idx < len(tokens):

                            next_lemma = tokens[next_idx]["lemma"]

                            next_text = tokens[next_idx]["text"].lower()

                            if next_lemma in all_table_synonyms or next_text in all_table_synonyms:

                                # Preposition introduces a table name, NOT a WHERE comparison

                                continue

                        comparison_index = i

                        break

                if comparison_index != -1:

                    break



        if comparison_index == -1:

            return None



        if operator == "BETWEEN":

            numbers = [t["text"] for t in tokens if t["is_number"]]

            if len(numbers) >= 2:

                value = f"{numbers[0]} AND {numbers[1]}"

            else:

                return None

        else:

            value = self.find_value(tokens, comparison_index)



        if value is None:

            return None



        detected_column = None



        # Collect all table synonyms to skip during column search

        # (e.g., "warehouse" identifies the table, not the WHERE column)

        all_table_synonyms = set()

        for synonyms in self.tables.values():

            for s in synonyms:

                all_table_synonyms.add(s)



        # Search BEFORE operator



        for i in range(comparison_index - 1, -1, -1):



            word = tokens[i]["lemma"]



            # Skip if this word is a table synonym — it identifies the table, not a filter column

            if word in all_table_synonyms:

                continue



            for column, synonyms in table_columns.items():



                if word in synonyms or tokens[i]["text"].lower() in synonyms:



                    detected_column = column

                    break



            if detected_column:

                break



        # Search AFTER operator



        if detected_column is None:



            for i in range(comparison_index + 1, len(tokens)):



                word = tokens[i]["lemma"]



                # Skip if this word is a table synonym

                if word in all_table_synonyms:

                    continue



                for column, synonyms in table_columns.items():



                    if word in synonyms:



                        detected_column = column

                        break



                if detected_column:

                    break



        # Default numeric columns (when value is a number)



        if detected_column is None:



            priority_numeric = [

                "Selling_Price",

                "Cost_Price",

                "Quantity",

                "Total_Amount",

                "Subtotal",

            ]



            for column in priority_numeric:



                if column in table_columns:



                    detected_column = column

                    break



        # Default text columns (when no numeric column matched — likely a string WHERE)



        if detected_column is None and value and not str(value).isdigit():

            table_default_text_col = {
                "supplier": "Supplier_Name",
                "products": "Product_Name",
                "customer": "Customer_Name",
                "warehouse": "Location",
                "category": "Category_Name",
            }
            if table in table_default_text_col and table_default_text_col[table] in table_columns:
                detected_column = table_default_text_col[table]
            else:
                priority_text = [
                    "Supplier_Name",
                    "Product_Name",
                    "Customer_Name",
                    "Warehouse_Name",
                    "Category_Name",
                    "Location",
                    "address",
                    "Order_Status",
                ]

                for column in priority_text:
                    if column in table_columns:
                        detected_column = column
                        break



        if detected_column is None:

            return None



        return {"column": detected_column, "operator": operator, "value": value}



        # --------------------------------------------------



    # Detect ORDER BY

    # --------------------------------------------------



    def find_order_by(self, tokens, table):



        table_columns = self.get_table_columns(table)



        if not table_columns:

            return None



        direction = None

        has_sort_keyword = False



        for token in tokens:



            word = token["lemma"]



            for key, synonyms in self.sorting.items():



                if word in synonyms:



                    if key == "ASC":

                        direction = "ASC"



                    elif key == "DESC":

                        direction = "DESC"



                    elif key == "ORDER_BY":

                        # A sort keyword was found — direction will default to ASC

                        has_sort_keyword = True



        # If an explicit direction was set, use it; otherwise default to ASC

        # when a generic sort keyword (sort/sorted/order_by) was detected

        if direction is None and has_sort_keyword:

            direction = "ASC"



        if direction is None:

            return None



        # If user explicitly mentioned a column



        selected_columns = self.find_select_columns(tokens, table)



        if selected_columns:



            return {"column": selected_columns[0], "direction": direction}



        # Otherwise choose a default sortable column



        priority = [

            "Selling_Price",

            "Cost_Price",

            "Quantity",

            "Total_Amount",

            "Product_Name",

            "Customer_Name",

            "Supplier_Name",

            "Warehouse_Name",

        ]



        for column in priority:



            if column in table_columns:



                return {"column": column, "direction": direction}



        return None



    # --------------------------------------------------

    # Detect LIMIT

    # --------------------------------------------------



    def find_limit(self, tokens):



        def to_int(token):

            if not token:

                return None

            txt = str(token.get("text", "")).lower().strip()

            if txt.isdigit():

                return int(txt)

            word_map = {

                "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,

                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,

                "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,

                "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,

                "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,

                "eighty": 80, "ninety": 90, "hundred": 100

            }

            return word_map.get(txt, None)



        # Pattern 1: "top N", "first N", "last N"



        for i in range(len(tokens) - 1):



            if tokens[i]["lemma"] in ["top", "first", "last"]:



                val = to_int(tokens[i + 1])

                if val is not None:

                    return val



        # Pattern 2: "show N products" — number appears before a table keyword



        table_synonyms = set()



        for synonyms in self.tables.values():

            for s in synonyms:

                table_synonyms.add(s)



        for i in range(len(tokens) - 1):



            val = to_int(tokens[i])

            if val is not None:



                if tokens[i + 1]["lemma"] in table_synonyms:



                    return val



        return None



    # --------------------------------------------------

    # Detect GROUP BY

    # --------------------------------------------------



    def find_group_by(self, tokens, table):



        table_columns = self.get_table_columns(table)



        if not table_columns:

            return None



        lemmas = [token["lemma"] for token in tokens]



        # Only trigger if the user actually asks for grouping

        group_keywords = ["group", "group_by", "each", "per", "wise", "by"]



        if not any(word in lemmas for word in group_keywords):

            return None



        # Positional candidate extraction:

        # e.g. "category-wise" -> candidate before "wise"

        # e.g. "per category", "each category", "by category" -> candidate after trigger word

        detected_candidate = None

        for i, token in enumerate(tokens):

            w = token["lemma"]

            if w == "wise" and i > 0:

                detected_candidate = tokens[i - 1]["lemma"]

                break

            elif w in ["per", "each", "by", "group_by"] and i < len(tokens) - 1:

                detected_candidate = tokens[i + 1]["lemma"]

                break



        if detected_candidate:

            for column, synonyms in table_columns.items():

                if detected_candidate in synonyms:

                    return column



        # Entity words of this table to skip (e.g. "product" for "products" table)

        entity_words = set(self.tables.get(table, []))



        # Priority list: check if any token matches a synonym of these columns

        priority = [

            "Category_ID",

            "Category_Name",

            "Warehouse_ID",

            "Warehouse_Name",

            "Supplier_ID",

            "Supplier_Name",

            "Customer_ID",

            "Customer_Name",

            "Order_Status",

            "payment_method",

            "Location",

        ]



        for column in priority:

            if column in table_columns:

                for token in tokens:

                    w = token["lemma"]

                    if w in group_keywords or w in entity_words:

                        continue

                    if w in table_columns[column]:

                        return column



        # Fallback: scan all available columns for this table

        # Only return a column if the token is an EXACT match to one of its synonyms

        # (prevents wide accidental matching)

        aggregate_words = set()

        for agg_syns in self.aggregates.values():

            aggregate_words.update(agg_syns)



        for token in tokens:

            word = token["lemma"]



            # Skip group control keywords, table entity names, and aggregate function words

            if word in group_keywords or word in entity_words or word in aggregate_words:

                continue



            for column, synonyms in table_columns.items():

                if word in synonyms:

                    return column



        return None



    # --------------------------------------------------

    # Detect HAVING

    # --------------------------------------------------



    def find_having(self, tokens, table):



        aggregate = self.find_aggregate(tokens)



        if aggregate is None:

            return None



        group_column = self.find_group_by(tokens, table)



        if group_column is None:

            return None



        operator = self.find_comparison(tokens)



        if operator is None:

            return None



        value = self.find_value(tokens)



        if value is None:

            return None



        return {

            "aggregate": aggregate,

            "column": group_column,

            "operator": operator,

            "value": value,

        }



        # --------------------------------------------------



    # Detect JOIN Requirement

    # --------------------------------------------------



    def find_join(self, tokens):

        detected_tables = []

        # 1. Direct table detection from table synonyms
        for token in tokens:
            word = token["lemma"]
            text_lower = token["text"].lower()
            for table, synonyms in self.tables.items():
                if word in synonyms or text_lower in synonyms:
                    if table not in detected_tables:
                        detected_tables.append(table)

        # 2. Check if a non-ID content column from an external table is explicitly requested
        # AND is not already satisfied by the currently detected table(s)
        token_lemmas = {t["lemma"].lower() for t in tokens}
        token_texts = {t["text"].lower() for t in tokens}
        all_token_words = token_lemmas | token_texts

        bigrams = set()
        for i in range(len(tokens) - 1):
            bigrams.add(tokens[i]["lemma"].lower() + " " + tokens[i+1]["lemma"].lower())
            bigrams.add(tokens[i]["text"].lower() + " " + tokens[i+1]["text"].lower())

        all_candidate_words = all_token_words | bigrams
        ignore_words = {
            "show", "list", "display", "find", "get", "give", "all", "each", "every",
            "name", "names", "id", "ids", "total", "sum", "average", "avg", "count",
            "max", "min", "highest", "lowest", "more", "less", "greater", "available",
            "in", "at", "on", "from", "with", "whose", "where", "and", "or",
            "product", "products", "warehouse", "warehouses", "customer", "customers",
            "supplier", "suppliers", "order", "orders", "category", "categories"
        }

        # Collect all column synonyms already present in currently detected tables
        already_covered_synonyms = set()
        for dt in detected_tables:
            cols_in_dt = self.columns.get(dt, {})
            for cname, syns in cols_in_dt.items():
                for syn in syns:
                    already_covered_synonyms.add(syn.lower())

        # Only look for an external table if candidate words match a column that is NOT covered by any detected table
        for table, col_dict in self.columns.items():
            if table in detected_tables:
                continue
            for col_name, syns in col_dict.items():
                if col_name.endswith("_ID") or col_name.endswith("_id"):
                    continue
                matched = False
                for syn in syns:
                    syn_lower = syn.lower()
                    if syn_lower in ignore_words or syn_lower in already_covered_synonyms:
                        continue
                    if syn_lower in all_candidate_words:
                        if table not in detected_tables:
                            detected_tables.append(table)
                        matched = True
                        break
                if matched:
                    break

        # Disambiguate warehouse and inventory
        if "warehouse" in detected_tables and "inventory" in detected_tables:
            detected_tables = [t for t in detected_tables if t in ["warehouse", "inventory"]]

        if len(detected_tables) > 1:
            return detected_tables

        return None


    # Infer Table from Column Names

    # --------------------------------------------------



    def infer_table_from_columns(self, tokens):



        scores = {}



        for table in self.columns:

            scores[table] = 0



        for token in tokens:



            word = token["lemma"]



            for table, table_columns in self.columns.items():



                for synonyms in table_columns.values():



                    if word in synonyms:

                        scores[table] += 1



        best_table = None

        best_score = 0



        for table, score in scores.items():



            if score > best_score:

                best_score = score

                best_table = table



        if best_score == 0:

            return None



        return best_table



    # --------------------------------------------------

    # Default SELECT Columns

    # --------------------------------------------------



    def get_default_columns(self, table):
        return ["*"]



    # --------------------------------------------------

    # Default Aggregate Column

    # --------------------------------------------------



    def get_default_aggregate_column(self, table, aggregate):



        table_columns = self.get_table_columns(table)



        if aggregate == "COUNT":



            priority = [

                "Product_ID",

                "Customer_ID",

                "Supplier_ID",

                "Warehouse_ID",

                "Order_ID",

            ]



        else:



            priority = [

                "Selling_Price",

                "Cost_Price",

                "Quantity",

                "Total_Amount",

                "Subtotal",

            ]



        for column in priority:



            if column in table_columns:

                return column



        if table_columns:

            return list(table_columns.keys())[0]



        return None



    # --------------------------------------------------

    # Normalize Aggregate Queries

    # --------------------------------------------------



    def prepare_select_columns(self, table, aggregate, select_columns):



        if aggregate is None:



            if len(select_columns) == 0:

                return self.get_default_columns(table)



            return select_columns



        if len(select_columns) == 0:



            column = self.get_default_aggregate_column(table, aggregate)



            if column is not None:

                select_columns.append(column)



        return select_columns



        # --------------------------------------------------



    # Main Linking Function

    # --------------------------------------------------



    def link_schema(self, tokens):



        # --------------------------------------------

        # Detect Main Table

        # --------------------------------------------



        table = self.find_table(tokens)



        if table is None:

            table = self.infer_table_from_columns(tokens)



        # --------------------------------------------

        # Detect JOIN

        # --------------------------------------------



        joins = self.find_join(tokens)



        # --------------------------------------------

        # Detect Operation

        # --------------------------------------------



        operation = self.find_operation(tokens)



        # --------------------------------------------

        # Detect Aggregate

        # --------------------------------------------



        aggregate = self.find_aggregate(tokens)



        # --------------------------------------------

        # Detect Selected Columns

        # --------------------------------------------



        select_columns = self.find_select_columns(tokens, table, joins=joins)



        select_columns = self.prepare_select_columns(table, aggregate, select_columns)



        # --------------------------------------------

        # Detect WHERE

        # --------------------------------------------



        where = self.find_where(tokens, table)



        # Aggregate-only words should NOT become WHERE clauses



        if aggregate is not None:



            aggregate_words = []



            for synonyms in self.aggregates.values():

                aggregate_words.extend(synonyms)



            if where is not None:



                if str(where["value"]).lower() in aggregate_words:

                    where = None



        # --------------------------------------------

        # Detect ORDER BY

        # --------------------------------------------



        order_by = self.find_order_by(tokens, table)



        # --------------------------------------------

        # Detect GROUP BY

        # --------------------------------------------



        group_by = self.find_group_by(tokens, table)



        # --------------------------------------------

        # Detect HAVING

        # --------------------------------------------



        having = self.find_having(tokens, table)



        # --------------------------------------------

        # Detect LIMIT

        # --------------------------------------------



        limit = self.find_limit(tokens)



        # --------------------------------------------

        # Final Schema

        # --------------------------------------------



        linked_schema = {

            "operation": operation,

            "table": table,

            "joins": joins,

            "select_columns": select_columns,

            "where": where,

            "aggregate": aggregate,

            "order_by": order_by,

            "group_by": group_by,

            "having": having,

            "limit": limit,

        }



        return linked_schema

