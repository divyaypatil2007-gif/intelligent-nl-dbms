from backend.preprocess import Preprocessor
from backend.schema_linker import SchemaLinker
from backend.query_builder import QueryBuilder
from backend.complexity_analyzer import ComplexityAnalyzer
from backend.rule_engine import RuleEngine
from backend.llm_router import LLMRouter
from backend.sql_executor import SQLExecutor
from backend.result_formatter import ResultFormatter

preprocessor = Preprocessor()
linker       = SchemaLinker()
builder      = QueryBuilder()
analyzer     = ComplexityAnalyzer()
engine       = RuleEngine()
llm          = LLMRouter()
executor     = SQLExecutor()
formatter    = ResultFormatter()

if __name__ == "__main__":
    print("=" * 60)
    print(" Intelligent Natural Language Database Query System ")
    print("=" * 60)

    while True:

        query = input("\nEnter your question (type exit to quit): ")

    if query.lower() == "exit":
        print("\nThank You!")
        break

    # ----------------------------------------------------------
    # Step 1 — Preprocess
    # ----------------------------------------------------------
    tokens = preprocessor.preprocess(query)

    # ----------------------------------------------------------
    # Step 2 — Link Schema
    # ----------------------------------------------------------
    linked_schema = linker.link_schema(tokens)

    # ----------------------------------------------------------
    # Step 3 — Classify Complexity
    # ----------------------------------------------------------
    analysis = analyzer.analyze(tokens, linked_schema)
    complexity = analysis["complexity"]

    print(f"\n[Complexity] {complexity}", end="")
    if analysis["signals"]:
        print(f"  →  signals: {', '.join(analysis['signals'])}", end="")
    print()

    # ----------------------------------------------------------
    # Step 4 — Route: SIMPLE → RuleEngine | HARD → Local LLM
    # ----------------------------------------------------------
    sql = None
    explanation = None
    auto_healed = False
    issues_fixed = []

    if complexity == "SIMPLE":
        query_object = builder.build(linked_schema)
        candidate_sql = engine.generate_sql(query_object)

        # Tier 1 & 2 Validation + Tier 3 Auto-Healing for Rule Engine candidate
        validation_res = llm.validate_and_heal(
            nl_query=query,
            sql=candidate_sql,
            tokens=tokens,
            linked_schema=linked_schema
        )

        if validation_res["is_valid"]:
            sql = validation_res["sql"]
            if validation_res.get("auto_healed"):
                auto_healed = True
                issues_fixed = validation_res.get("issues_fixed", [])
                explanation = validation_res.get("explanation", "Auto-healed candidate query to match user intent.")
            else:
                explanation = "Generated via single-table deterministic Rule Engine."
        else:
            # Fallback to local LLM when RuleEngine cannot resolve or fails validation
            llm_response = llm.query(
                nl_query=query,
                linked_schema=linked_schema,
                signals=["rule_engine_fallback"],
            )
            sql = llm_response.get("sql")
            explanation = llm_response.get("explanation")
            auto_healed = llm_response.get("auto_healed", False)
            issues_fixed = llm_response.get("issues_fixed", [])

    else:
        # HARD query — send to local LLM with schema context + auto-healing
        llm_response = llm.query(
            nl_query=query,
            linked_schema=linked_schema,
            signals=analysis["signals"],
        )
        sql = llm_response.get("sql")
        explanation = llm_response.get("explanation")
        auto_healed = llm_response.get("auto_healed", False)
        issues_fixed = llm_response.get("issues_fixed", [])

    # ----------------------------------------------------------
    # Step 5 — Display SQL & Natural Language Explanation
    # ----------------------------------------------------------
    if auto_healed:
        print("\n[Auto-Healing Activated]")
        print(f"  Fixed requirements: {', '.join(issues_fixed)}")

    if sql:
        print("\nGenerated SQL:")
        print(sql)

    if explanation:
        print("\nExplanation:")
        print(explanation)

    # ----------------------------------------------------------
    # Step 6 — Execute and display results
    # ----------------------------------------------------------
    if sql and not sql.startswith("["):
        result = executor.execute(sql)
        print("\nResult:")
        formatter.display(result)
    elif not sql:
        print("\n[Notice] Could not generate SQL. Please check Ollama status if this is a hard query.")