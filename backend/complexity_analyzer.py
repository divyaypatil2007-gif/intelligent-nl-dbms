"""
backend/complexity_analyzer.py
--------------------------------
Analyzes a preprocessed token list + linked schema and classifies
the query as either SIMPLE or HARD.

SIMPLE  → handled by the rule-based RuleEngine (7 SQL clauses)
HARD    → routed to the local LLM (joins, subqueries, multi-condition, etc.)

Classification is score-based: each detected hard signal adds a weight.
If the total score reaches the HARD_THRESHOLD, the query is HARD.
"""

from backend.dictionary_loader import DictionaryLoader


# ---------------------------------------------------------------------------
# Hard signals and their weights
# ---------------------------------------------------------------------------
# Adjust weights here to tune the boundary between SIMPLE and HARD.

HARD_THRESHOLD = 1  # one confirmed hard signal is enough

SIGNAL_WEIGHTS = {
    "multi_table_join":      10,   # 2+ distinct tables detected → JOIN needed
    "explicit_join_keyword":  10,  # user literally said "join / joined with / …"
    "multi_condition_logic":   8,  # AND / OR between two filter conditions
    "subquery_indicator":      8,  # "which … is the highest among", "whose X > avg"
    "set_operation":          10,  # UNION / INTERSECT / EXCEPT intent
    "case_when":              10,  # CASE WHEN / IF THEN style phrasing
    "window_function":        10,  # RANK / ROW_NUMBER / OVER / PARTITION BY
    "nested_aggregate":        8,  # "average of totals", "sum of counts"
    "comparison_after_agg":    6,  # "products whose price > average price"
    "ranked_aggregation":     10,  # "top N by aggregate", aggregate + limit
    "argmax_argmin_extremum": 10,  # "Product with maximum price", argmax/argmin
    "relational_intent":      10,  # "who ordered", "who placed", "placed by"
    "domain_status_temporal": 10,  # "out of stock", "recently placed", "latest"
    "value_filtered_aggregate": 10,  # "revenue from UPI", aggregate on specific value
    "relative_date_temporal": 10,  # "in the last 7 days", "in January 2025", "yesterday"
    "having_aggregate_filter": 10,  # "categories with more than 5 products", "spending > 10000"
    "anti_join_negative_existence": 10,  # "products never ordered", "customers with no orders"
}


class ComplexityAnalyzer:

    def __init__(self):

        loader = DictionaryLoader()
        dictionary = loader.get_dictionary()

        self.tables = dictionary["tables"]
        self.logical = dictionary["logical_operators"]

        # ------------------------------------------------------------------
        # Hard keyword sets — these trigger specific hard signals
        # ------------------------------------------------------------------

        # Explicit JOIN phrasing
        self.join_keywords = {
            "join", "joined", "combine", "combined", "merge", "merged",
            "with", "along", "together", "related", "relation", "linked",
            "connect", "connected", "associated", "across",
        }

        # Subquery / relative-clause indicators
        self.subquery_keywords = {
            "which", "whose", "that", "where",
            "among", "within", "inside", "comparing",
            "compared", "relative", "than_average", "than_avg",
            "above_average", "below_average",
        }

        # Set-operation indicators
        self.set_keywords = {
            "union", "intersect", "except", "minus",
            "combine", "combined", "together", "both",
        }

        # CASE WHEN / conditional phrasing
        self.case_keywords = {
            "if", "else", "case", "when", "then",
            "otherwise", "depending", "based",
        }

        # Window function indicators
        self.window_keywords = {
            "rank", "ranking", "ranked", "row_number", "rownumber",
            "over", "partition", "partition_by", "dense_rank",
            "lead", "lag", "ntile", "cumulative", "running",
            "running_total", "rolling",
        }

        # Nested aggregate indicators (e.g. "average of totals")
        self.nested_agg_connectors = {
            "of_total", "of_sum", "of_count", "of_average", "of_avg",
            "of_max", "of_min", "average_of", "sum_of_total",
        }

        # Logical AND/OR tokens (from logical.json)
        self.and_synonyms = set(self.logical.get("AND", []))
        self.or_synonyms  = set(self.logical.get("OR", []))

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def analyze(self, tokens: list, linked_schema: dict) -> dict:
        """
        Returns a result dict:
        {
            "complexity": "SIMPLE" | "HARD",
            "score":      int,
            "signals":    [list of triggered signal names],
            "reasons":    [list of human-readable reason strings],
        }
        """

        score   = 0
        signals = []
        reasons = []

        lemmas = [t["lemma"] for t in tokens]
        texts  = [t["text"].lower() for t in tokens]
        all_words = set(lemmas) | set(texts)

        # -------------------------------------------------------------------
        # Signal 1 — Multi-table JOIN (2+ distinct tables detected)
        #
        # Guard: remove the primary resolved table from the detected list
        # before counting. This prevents GROUP BY queries like
        # "Count products per category" from being flagged — schema_linker
        # detects both "products" and "category" as table tokens but resolves
        # a single primary table. A true JOIN is only needed when tables OTHER
        # THAN the primary one are also referenced for data retrieval.
        #
        # Additional GROUP BY exemption: if the only external table is the
        # source of the GROUP BY column (e.g. Category_Name from 'category'),
        # the user is doing a GROUP BY on a related key — not a full JOIN.
        # -------------------------------------------------------------------
        joins         = linked_schema.get("joins")
        primary_table = linked_schema.get("table")
        group_by_col  = linked_schema.get("group_by")
        having_clause = linked_schema.get("having")

        if joins and len(joins) >= 2:
            external_tables = [t for t in joins if t != primary_table]

            if external_tables:
                # Exemption 1: GROUP BY or HAVING already detected →
                # external table tokens are GROUP BY nouns, not JOIN targets.
                if group_by_col is not None or having_clause is not None:
                    external_tables = []  # not a real JOIN

                # Exemption 2: external table name appears right after a number
                # token (e.g. "more than 5 products", "5 customers") →
                # it is a COUNT noun, not a JOIN target.
                if external_tables:
                    # Build set of table synonyms for external tables
                    number_noun_tables = set()
                    for i in range(len(tokens) - 1):
                        if tokens[i]["is_number"]:
                            next_lemma = tokens[i + 1]["lemma"]
                            for t_name, t_syns in self.tables.items():
                                if next_lemma in t_syns and t_name != primary_table:
                                    number_noun_tables.add(t_name)
                    external_tables = [t for t in external_tables if t not in number_noun_tables]

            if len(external_tables) >= 1:
                score   += SIGNAL_WEIGHTS["multi_table_join"]
                signals.append("multi_table_join")
                reasons.append(
                    f"Query references multiple tables: {joins} — a JOIN is needed."
                )

        # -------------------------------------------------------------------
        # Signal 2 — Explicit JOIN keyword used by the user
        # -------------------------------------------------------------------
        if any(w in all_words for w in self.join_keywords - {"with", "both", "together"}):
            score   += SIGNAL_WEIGHTS["explicit_join_keyword"]
            signals.append("explicit_join_keyword")
            reasons.append(
                "User used a JOIN-related keyword (join / combine / merge / …)."
            )

        # -------------------------------------------------------------------
        # Signal 3 — Multi-condition logic (AND / OR between filter conditions)
        #
        # Guard: only flag when:
        #   (a) a WHERE condition is already detected — meaning AND/OR is
        #       chaining filter conditions (not just listing SELECT columns),
        #   OR
        #   (b) two or more AND/OR tokens appear — very likely multi-condition.
        #
        # This prevents "Show product name and price" (AND used to list columns)
        # from being wrongly classified as HARD.
        # -------------------------------------------------------------------
        has_and_or = any(w in all_words for w in self.and_synonyms | self.or_synonyms)
        has_where  = linked_schema.get("where") is not None

        # Count raw 'and'/'or' lemmas (pure logical tokens only)
        raw_logical = sum(
            1 for w in lemmas
            if w in self.and_synonyms or w in self.or_synonyms
        )

        # Fire only if AND/OR appears alongside a WHERE, or appears 2+ times
        # Exemption: BETWEEN uses 'AND' as range connector, not multiple WHERE clauses
        is_between = (linked_schema.get("where") or {}).get("operator") == "BETWEEN"
        if has_and_or and not is_between and (has_where or raw_logical >= 2):
            score   += SIGNAL_WEIGHTS["multi_condition_logic"]
            signals.append("multi_condition_logic")
            reasons.append(
                "Query contains AND/OR logic — likely multiple WHERE conditions."
            )

        # -------------------------------------------------------------------
        # Signal 4 — Subquery / nested comparison indicator
        # -------------------------------------------------------------------
        comparison_words = {"above", "below", "greater", "greater_than", "more", "more_than", "higher", "less", "less_than", "lower", "under", "over"}
        agg_words = {"average", "avg", "mean", "total", "sum", "count", "maximum", "max", "minimum", "min"}

        has_subquery_kw = any(w in all_words for w in self.subquery_keywords)
        has_comparison_kw = any(w in all_words for w in comparison_words)
        has_agg_kw = any(w in all_words for w in agg_words) or (linked_schema.get("aggregate") is not None)

        # Triggers if:
        # (1) Relative keywords like 'which/whose/among' with an aggregate, OR
        # (2) Comparison word alongside an aggregate word (e.g. 'above average', 'greater than average price')
        if (has_subquery_kw and has_agg_kw) or (has_comparison_kw and has_agg_kw):
            score   += SIGNAL_WEIGHTS["subquery_indicator"]
            signals.append("subquery_indicator")
            reasons.append(
                "Subquery indicator detected (comparison against an aggregate value, e.g. 'above average')."
            )

        # -------------------------------------------------------------------
        # Signal 5 — Set operation (UNION / INTERSECT / EXCEPT)
        # -------------------------------------------------------------------
        if any(w in all_words for w in self.set_keywords - {"both", "combine", "combined", "together"}):
            score   += SIGNAL_WEIGHTS["set_operation"]
            signals.append("set_operation")
            reasons.append(
                "Set-operation keyword detected (union / intersect / except)."
            )

        # -------------------------------------------------------------------
        # Signal 6 — CASE WHEN / conditional expression
        # -------------------------------------------------------------------
        if any(w in all_words for w in self.case_keywords - {"if", "based"}):
            score   += SIGNAL_WEIGHTS["case_when"]
            signals.append("case_when")
            reasons.append(
                "Conditional expression keyword detected (case / when / then / else)."
            )

        # -------------------------------------------------------------------
        # Signal 7 — Window function
        # -------------------------------------------------------------------
        if any(w in all_words for w in self.window_keywords):
            score   += SIGNAL_WEIGHTS["window_function"]
            signals.append("window_function")
            reasons.append(
                "Window function keyword detected (rank / over / partition / running / …)."
            )

        # -------------------------------------------------------------------
        # Signal 8 — Nested aggregate (e.g. "average of totals")
        # -------------------------------------------------------------------
        if any(w in all_words for w in self.nested_agg_connectors):
            score   += SIGNAL_WEIGHTS["nested_aggregate"]
            signals.append("nested_aggregate")
            reasons.append(
                "Nested aggregate pattern detected (e.g. 'average of totals')."
            )

        # -------------------------------------------------------------------
        # Signal 9 — Comparison after aggregate in same query
        # e.g. "show products whose price is greater than average price"
        # Detected by: aggregate token + comparison token + "than" + another aggregate
        # -------------------------------------------------------------------
        agg_words = {"average", "avg", "mean", "total", "sum", "count", "max", "min"}
        agg_tokens_found = [w for w in lemmas if w in agg_words]
        if len(agg_tokens_found) >= 2:
            score   += SIGNAL_WEIGHTS["comparison_after_agg"]
            signals.append("comparison_after_agg")
            reasons.append(
                "Multiple aggregate references in one query — likely a subquery pattern."
            )

        # -------------------------------------------------------------------
        # Signal 10 — Ranked aggregate / Top-N group ranking
        # e.g. "top 3 customers by total spending", "highest 5 categories by sales"
        # Whenever an aggregate is requested together with a LIMIT / Top-N,
        # or when "by" is used to order/group by an aggregate.
        # Single-table RuleEngine cannot rank aggregated groups.
        # -------------------------------------------------------------------
        has_limit_or_top = (linked_schema.get("limit") is not None) or any(w in all_words for w in ["top", "highest", "lowest", "best", "bottom"])
        has_agg_token = (linked_schema.get("aggregate") is not None) or any(w in all_words for w in agg_words)
        has_by_token = any(w in all_words for w in ["by", "per", "grouped_by", "group_by"])

        if (has_limit_or_top and has_agg_token and has_by_token) or (linked_schema.get("aggregate") is not None and linked_schema.get("limit") is not None):
            score   += SIGNAL_WEIGHTS["ranked_aggregation"]
            signals.append("ranked_aggregation")
            reasons.append(
                "Ranked aggregation pattern ('top N by aggregate') requires GROUP BY, ORDER BY, and LIMIT."
            )

        # -------------------------------------------------------------------
        # Signal 11 — Argmax / Argmin / Extremum entity query
        # e.g. "Product with the maximum selling price", "Customer with highest spending"
        # Triggers when a superlative/extremum keyword appears with a relative
        # preposition or pronoun ("with", "whose", "having", "which", "that").
        # Selecting an entity based on an extremum metric requires subquery or ORDER BY LIMIT.
        # -------------------------------------------------------------------
        extremum_words = {
            "maximum", "max", "highest", "most", "largest", "greatest", "best",
            "minimum", "min", "lowest", "least", "smallest", "cheapest", "costliest"
        }
        has_extremum = any(w in all_words for w in extremum_words)
        has_relational_prep = any(w in all_words for w in ["with", "whose", "having", "which", "that"])

        if has_extremum and has_relational_prep:
            score   += SIGNAL_WEIGHTS["argmax_argmin_extremum"]
            signals.append("argmax_argmin_extremum")
            reasons.append(
                "Argmax/argmin extremum query (entity with maximum/minimum metric) requires ordering or subquery."
            )

        # -------------------------------------------------------------------
        # Signal 12 — Relational intent
        # e.g. "customers who ordered laptops", "orders placed by Aarav"
        # -------------------------------------------------------------------
        relational_tokens = {"who", "whom", "who_ordered", "who_placed", "placed_by", "supplied_by", "delivered_to"}
        if any(w in all_words for w in relational_tokens):
            score   += SIGNAL_WEIGHTS["relational_intent"]
            signals.append("relational_intent")
            reasons.append("Relational intent keyword ('who ordered', 'who placed', 'placed by') indicates cross-table relationship.")

        # -------------------------------------------------------------------
        # Signal 13 — Domain status & temporal ranking
        # e.g. "out of stock", "5 most recently placed orders"
        # -------------------------------------------------------------------
        status_temporal_tokens = {"out_of_stock", "in_stock", "recent", "recently", "latest", "earliest", "newest", "most_expensive", "least_expensive"}
        if any(w in all_words for w in status_temporal_tokens):
            score   += SIGNAL_WEIGHTS["domain_status_temporal"]
            signals.append("domain_status_temporal")
            reasons.append("Status or temporal ranking detected ('out of stock', 'recently', 'latest').")

        # -------------------------------------------------------------------
        # Signal 14 — Value-filtered aggregate
        # e.g. "total revenue from UPI payments"
        # -------------------------------------------------------------------
        value_tokens = {"upi", "cash", "card", "net_banking", "pending", "packed", "shipped", "delivered", "cancelled"}
        has_val = any(w in all_words for w in value_tokens)
        has_agg_val = (linked_schema.get("aggregate") is not None) or any(w in all_words for w in agg_words)
        if has_val and has_agg_val:
            score   += SIGNAL_WEIGHTS["value_filtered_aggregate"]
            signals.append("value_filtered_aggregate")
            reasons.append("Filtered aggregate query (aggregate conditioned on specific status or payment value).")

        # -------------------------------------------------------------------
        # Signal 15 — Relative or calendar date expression
        # e.g. "orders in the last 7 days", "placed yesterday", "in January 2025"
        # -------------------------------------------------------------------
        date_words = {"yesterday", "today", "tomorrow", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"}
        has_date_word = any(w in all_words for w in date_words)
        has_temporal_unit = any(w in all_words for w in ["days", "day", "months", "month", "weeks", "week", "years", "year"])
        has_temporal_modifier = any(w in all_words for w in ["last", "past", "next", "previous"])
        has_relative_window = has_temporal_unit and has_temporal_modifier
        has_year = any(w.isdigit() and len(w) == 4 and w.startswith("20") for w in all_words)

        if has_date_word or has_relative_window or (has_year and any(w in all_words for w in ["in", "during", "for", "placed", "ordered"])):
            score   += SIGNAL_WEIGHTS["relative_date_temporal"]
            signals.append("relative_date_temporal")
            reasons.append("Relative or calendar date filter detected (requires MySQL INTERVAL or date functions).")

        # -------------------------------------------------------------------
        # Signal 16 — HAVING clause / Group-level Aggregate Filtering
        # e.g. "categories having more than 5 products", "customers who placed > 2 orders"
        # -------------------------------------------------------------------
        has_having_word = "having" in all_words
        comp_words = {
            "more", "more_than", "greater", "greater_than", "less", "less_than",
            "fewer", "fewer_than", "above", "below", "exceeding", "over", "under", "at_least", "least"
        }
        group_entities = {
            "category", "categories", "customer", "customers",
            "supplier", "suppliers", "warehouse", "warehouses"
        }
        agg_nouns = {
            "product", "products", "order", "orders", "item", "items",
            "unit", "units", "quantity", "stock", "spending", "revenue", "sale", "sales", "total"
        }
        has_comp_noun = any(w in all_words for w in comp_words) and any(w in all_words for w in agg_nouns) and any(w in all_words for w in group_entities)
        
        if has_having_word or has_comp_noun:
            score   += SIGNAL_WEIGHTS["having_aggregate_filter"]
            signals.append("having_aggregate_filter")
            reasons.append("Group-level aggregate condition detected (requires GROUP BY ... HAVING clause).")

        # -------------------------------------------------------------------
        # Signal 17 — Anti-Join / Negative Relational Existence
        # e.g. "products never ordered", "customers who never placed an order", "no orders"
        # -------------------------------------------------------------------
        neg_words = {"never", "no", "zero", "not", "without", "unordered", "unbought", "none"}
        rel_action_words = {"ordered", "order", "orders", "purchased", "purchase", "bought", "placed", "supplied", "supplying", "supply"}
        has_neg = any(w in all_words for w in neg_words)
        has_action = any(w in all_words for w in rel_action_words)
        
        # Check specific combinations like "never ordered", "no orders", "not placed"
        is_anti_join = (
            ("never" in all_words and has_action) or
            ("no" in all_words and any(w in all_words for w in ["order", "orders", "supplier", "product"])) or
            ("without" in all_words and has_action) or
            (has_neg and any(w in all_words for w in ["ordered", "placed", "supplied"]))
        )
        if is_anti_join:
            score   += SIGNAL_WEIGHTS["anti_join_negative_existence"]
            signals.append("anti_join_negative_existence")
            reasons.append("Anti-join / negative relational existence query (requires LEFT JOIN ... WHERE IS NULL or NOT EXISTS).")

        # -------------------------------------------------------------------
        # Final classification
        # -------------------------------------------------------------------
        complexity = "HARD" if score >= HARD_THRESHOLD else "SIMPLE"

        return {
            "complexity": complexity,
            "score":      score,
            "signals":    signals,
            "reasons":    reasons,
        }
