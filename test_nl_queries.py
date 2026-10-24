"""
test_nl_queries.py
-------------------
Batch verification of diverse natural language queries.
"""

from backend.preprocess import Preprocessor
from backend.schema_linker import SchemaLinker
from backend.complexity_analyzer import ComplexityAnalyzer
from backend.rule_engine import RuleEngine
from backend.query_builder import QueryBuilder
from backend.llm_router import LLMRouter
from backend.sql_executor import SQLExecutor

pre = Preprocessor()
linker = SchemaLinker()
builder = QueryBuilder()
analyzer = ComplexityAnalyzer()
rule_engine = RuleEngine()
llm_router = LLMRouter()
executor = SQLExecutor()

test_queries = [
    "Display the customer(s) who placed the most expensive order.",
    "Show customers who ordered laptops",
    "Which products are out of stock?",
    "Find suppliers in Pune",
    "What is the total revenue from UPI payments?",
    "Show all orders placed by Aarav Sharma",
    "Which warehouse has the least stock?",
    "List the 5 most recently placed orders",
    "Show products whose warranty is 24 months",
    "Find the average order value",
    "Show categories having more than 3 products",
    "Which products have never been ordered?"
]

passed = 0
failed = 0

for idx, q in enumerate(test_queries, 1):
    tokens = pre.preprocess(q)
    linked_schema = linker.link_schema(tokens)
    analysis = analyzer.analyze(tokens, linked_schema)
    complexity = analysis["complexity"]
    signals = analysis["signals"]

    if complexity == "SIMPLE":
        q_obj = builder.build(linked_schema)
        sql = rule_engine.generate_sql(q_obj)
        if sql is not None:
            gen = "Rule Engine"
        else:
            llm_res = llm_router.query(q, linked_schema, ["fallback"])
            sql = llm_res.get("sql")
            gen = "Local LLM (fallback)"
    else:
        llm_res = llm_router.query(q, linked_schema, signals)
        sql = llm_res.get("sql")
        gen = f"Local LLM ({llm_router.model_name})"

    res = executor.execute_with_metrics(sql)
    success = res["success"]
    if success:
        passed += 1
    else:
        failed += 1

    status_str = "SUCCESS" if success else f"FAILED: {res.get('error')}"
    print(f"[{idx}] Q: {q}")
    print(f"    Complexity: {complexity} | Generator: {gen}")
    print(f"    SQL: {sql}")
    print(f"    Status: {status_str} | Rows: {res['row_count']} | Sample: {res['rows'][:1]}")
    print("-" * 70)

print(f"\nFinal: {passed} passed, {failed} failed out of {len(test_queries)}")
