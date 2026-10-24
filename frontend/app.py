import sys
import os
import pandas as pd
import streamlit as st

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.preprocess import Preprocessor
from backend.schema_linker import SchemaLinker
from backend.query_builder import QueryBuilder
from backend.complexity_analyzer import ComplexityAnalyzer
from backend.rule_engine import RuleEngine
from backend.llm_router import LLMRouter
from backend.sql_executor import SQLExecutor
from backend.query_metadata import explain_query_metadata
from backend.dictionary_loader import DictionaryLoader
from backend.fuzzy_matcher import FuzzyMatcher
from backend.date_parser import DateParser
from streamlit_mic_recorder import speech_to_text

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NL-DBMS Intelligent Query Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Premium Custom Styling (Dark & Light Theme Adaptive)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3.5rem;
        max-width: 1400px;
    }

    /* Header Container */
    .hero-header {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.07) 0%, rgba(124, 58, 237, 0.07) 100%);
        border: 1px solid rgba(99, 102, 241, 0.18);
        border-radius: 18px;
        padding: 1.8rem 2.2rem;
        margin-bottom: 1.8rem;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6, #EC4899);
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.12);
        color: #4F46E5;
        border: 1px solid rgba(99, 102, 241, 0.25);
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.15;
        margin: 0 0 0.9rem 0;
        background: linear-gradient(135deg, #0F172A 15%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    @media (prefers-color-scheme: dark) {
        .hero-title {
            background: linear-gradient(135deg, #F8FAFC 20%, #60A5FA 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-badge {
            background: rgba(99, 102, 241, 0.22);
            color: #A5B4FC;
            border-color: rgba(99, 102, 241, 0.4);
        }
    }

    /* Header Meta Tags */
    .header-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
    }
    .header-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.25);
        color: #334155;
    }
    @media (prefers-color-scheme: dark) {
        .header-pill {
            background: rgba(30, 41, 59, 0.7);
            border-color: rgba(148, 163, 184, 0.2);
            color: #CBD5E1;
        }
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .pulse-dot.green {
        background-color: #10B981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
    }
    .pulse-dot.blue {
        background-color: #3B82F6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
    }

    /* Clear (X) button styling */
    button:has(p:contains("✖")), button:has(span:contains("✖")) {
        border-radius: 10px !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }
    button:has(p:contains("✖")):hover, button:has(span:contains("✖")):hover {
        color: #EF4444 !important;
        border-color: #F87171 !important;
        background: rgba(239, 68, 68, 0.08) !important;
    }

    /* KPI / Stat Card Grid */
    .stat-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(226, 232, 240, 0.9);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
    }
    @media (prefers-color-scheme: dark) {
        .stat-card {
            background: rgba(30, 41, 59, 0.75);
            border-color: rgba(51, 65, 85, 0.8);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }
        .stat-card:hover {
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.35);
        }
    }

    .stat-label {
        font-size: 0.73rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748B;
        margin-bottom: 0.35rem;
    }
    .stat-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
    }
    @media (prefers-color-scheme: dark) {
        .stat-label {
            color: #94A3B8;
        }
        .stat-value {
            color: #F1F5F9;
        }
    }

    /* Badges */
    .metric-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.84rem;
        font-weight: 700;
    }
    .badge-simple {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .badge-hard {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .badge-engine {
        background-color: #EEF2FF;
        color: #4338CA;
        border: 1px solid #C7D2FE;
    }

    @media (prefers-color-scheme: dark) {
        .badge-simple {
            background-color: rgba(6, 95, 70, 0.35);
            color: #6EE7B7;
            border-color: rgba(16, 185, 129, 0.4);
        }
        .badge-hard {
            background-color: rgba(146, 64, 14, 0.35);
            color: #FCD34D;
            border-color: rgba(245, 158, 11, 0.4);
        }
        .badge-engine {
            background-color: rgba(67, 56, 202, 0.35);
            color: #A5B4FC;
            border-color: rgba(99, 102, 241, 0.4);
        }
    }

    /* Modern Card Container */
    .feature-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(226, 232, 240, 0.9);
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    @media (prefers-color-scheme: dark) {
        .feature-card {
            background: rgba(30, 41, 59, 0.65);
            border-color: rgba(51, 65, 85, 0.8);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        }
    }

    .feature-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
        color: #1E293B;
    }
    @media (prefers-color-scheme: dark) {
        .feature-card-header {
            color: #F1F5F9;
        }
    }

    /* Timing / Results Banner */
    .results-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        background: linear-gradient(135deg, rgba(241, 245, 249, 0.8) 0%, rgba(226, 232, 240, 0.6) 100%);
        border: 1px solid rgba(203, 213, 225, 0.8);
        border-radius: 12px;
        padding: 0.85rem 1.3rem;
        margin: 1.2rem 0;
    }
    @media (prefers-color-scheme: dark) {
        .results-banner {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
            border-color: rgba(51, 65, 85, 0.9);
        }
    }

    .benchmark-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.92rem;
        font-weight: 600;
        color: #2563EB;
    }
    @media (prefers-color-scheme: dark) {
        .benchmark-badge {
            color: #60A5FA;
        }
    }

    /* Sidebar Refinements */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(148, 163, 184, 0.15);
    }
    .sidebar-section-title {
        font-size: 0.88rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin: 1.2rem 0 0.5rem 0;
    }
    @media (prefers-color-scheme: dark) {
        .sidebar-section-title {
            color: #94A3B8;
        }
    }

    /* Polished Voice Banner */
    .voice-card {
        background: rgba(99, 102, 241, 0.06);
        border: 1px dashed rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 0.75rem 1.1rem;
        margin-bottom: 0.9rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .voice-card-text {
        font-size: 0.84rem;
        color: #475569;
    }
    @media (prefers-color-scheme: dark) {
        .voice-card-text {
            color: #CBD5E1;
        }
    }

    /* Button Enhancements */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.18s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
    }

    /* Polished Clear (✖) Button */
    div.stButton > button[key="clear_query_btn"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
    }
    div.stButton > button[key="clear_query_btn"]:hover {
        color: #EF4444 !important;
        background-color: #FEE2E2 !important;
        border-color: #FCA5A5 !important;
        transform: scale(1.03) !important;
    }

    /* Auto-expanding Code Box without scrolling */
    [data-testid="stCodeBlock"] {
        max-height: none !important;
        height: auto !important;
        width: 100% !important;
        margin-top: 0.2rem !important;
        margin-bottom: 1.2rem !important;
    }
    [data-testid="stCodeBlock"] pre {
        max-height: none !important;
        height: auto !important;
        min-height: auto !important;
        overflow-y: visible !important;
        overflow-x: auto !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
        padding: 1.25rem 1.5rem !important;
        border-radius: 12px !important;
        line-height: 1.65 !important;
        font-size: 0.98rem !important;
        border: 1px solid rgba(99, 102, 241, 0.28) !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
    }
    [data-testid="stCodeBlock"] code {
        max-height: none !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Pipeline Components (Cached for instant reuse)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_components():
    return {
        "preprocessor": Preprocessor(),
        "linker": SchemaLinker(),
        "builder": QueryBuilder(),
        "analyzer": ComplexityAnalyzer(),
        "rule_engine": RuleEngine(),
        "llm_router": LLMRouter(),
        "executor": SQLExecutor(),
        "dict_loader": DictionaryLoader(),
        "fuzzy_matcher": FuzzyMatcher(),
        "date_parser": DateParser()
    }

components = get_components()
dict_data = components["dict_loader"].get_dictionary()

# -----------------------------------------------------------------------------
# Sidebar: Database Schema & Quick Examples
# -----------------------------------------------------------------------------
# Input Session State & Dynamic Counter Callbacks
if "query_counter" not in st.session_state:
    st.session_state["query_counter"] = 0
    st.session_state["main_nl_query_0"] = "Show top 5 products"

def on_clear_query():
    st.session_state["query_counter"] = st.session_state.get("query_counter", 0) + 1
    new_k = f"main_nl_query_{st.session_state['query_counter']}"
    st.session_state[new_k] = ""
    st.session_state["execute_now"] = False
    st.session_state.pop("last_executed_query", None)

def on_select_example(query_text):
    st.session_state["query_counter"] = st.session_state.get("query_counter", 0) + 1
    new_k = f"main_nl_query_{st.session_state['query_counter']}"
    st.session_state[new_k] = query_text
    st.session_state["execute_now"] = True

with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:1.2rem;">
            <span style="font-size:1.6rem;">⚡</span>
            <div>
                <div style="font-weight:800; font-size:1.15rem; line-height:1.2;">NL-DBMS</div>
                <div style="font-size:0.75rem; color:#64748B; font-weight:600;">STUDIO CONTROLS</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">🗄️ Database Schema</div>', unsafe_allow_html=True)
    st.caption("Active DB: **inventory_management** (MySQL 8.0+)")

    tables = dict_data.get("tables", {})
    columns = dict_data.get("columns", {})

    with st.expander("Explore Tables & Columns", expanded=False):
        for t_name in sorted(columns.keys()):
            col_list = list(columns[t_name].keys())
            st.markdown(f"**`{t_name}`** ({len(col_list)} cols)")
            st.caption(", ".join(col_list))
            st.divider()

    st.markdown('<div class="sidebar-section-title">💡 Quick Examples</div>', unsafe_allow_html=True)
    st.caption("Click any query to load and test immediately:")

    tab_simple, tab_joins, tab_filters = st.tabs(["⚡ Simple", "🔗 Joins & Hard", "📅 Dates & Typos"])

    with tab_simple:
        simple_queries = [
            ("Top 5 Products", "Show top 5 products"),
            ("Products Price > 500", "Show products whose price is greater than 500"),
            ("Warehouses in Pune", "Show warehouses in Pune"),
            ("Average Price of Products", "Show average price of products"),
        ]
        for label, q_text in simple_queries:
            st.button(
                label,
                key=f"s_{label}",
                on_click=on_select_example,
                args=(q_text,),
                use_container_width=True
            )

    with tab_joins:
        hard_queries = [
            ("Products with Categories", "List all products with their category name"),
            ("Orders with Customers", "Show orders along with customer details"),
            ("Suppliers for High-Cost Items", "Display suppliers supplying products whose cost price is above 5000"),
            ("Anti-Join: Never Ordered", "Which products have never been ordered?"),
            ("Categories > 3 Products", "Show categories having more than 3 products"),
        ]
        for label, q_text in hard_queries:
            st.button(
                label,
                key=f"h_{label}",
                on_click=on_select_example,
                args=(q_text,),
                use_container_width=True
            )

    with tab_filters:
        filter_queries = [
            ("Orders in Last 30 Days", "Show orders in the last 30 days"),
            ("Orders in January 2025", "Show orders placed in January 2025"),
            ("Fuzzy Typo: 'leptops'", "Show all leptops in stock"),
        ]
        for label, q_text in filter_queries:
            st.button(
                label,
                key=f"f_{label}",
                on_click=on_select_example,
                args=(q_text,),
                use_container_width=True
            )

    st.markdown('<div class="sidebar-section-title">🔌 System Status</div>', unsafe_allow_html=True)
    llm_online = components["llm_router"].is_available()
    if llm_online:
        st.markdown(f"""
            <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:8px 12px; margin-bottom:8px; font-size:0.83rem;">
                <span class="pulse-dot green"></span> <b>Local LLM Online</b><br>
                <span style="font-size:0.75rem; color:#64748B;">Model: <code>{components['llm_router'].model_name}</code></span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:10px; padding:8px 12px; margin-bottom:8px; font-size:0.83rem;">
                <span class="pulse-dot" style="background-color:#F59E0B;"></span> <b>Local LLM Offline</b><br>
                <span style="font-size:0.75rem; color:#64748B;">Run <code>ollama serve</code> to enable local AI</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.3); border-radius:10px; padding:8px 12px; font-size:0.83rem;">
            <span class="pulse-dot blue"></span> <b>MySQL Database Connected</b><br>
            <span style="font-size:0.75rem; color:#64748B;">Schema: <code>inventory_management</code></span>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Main Hero Header (Redesigned, Clean, Modern - removed verbose subtitle)
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="hero-header">
        <div class="hero-badge">⚡ Intelligent Database Engine</div>
        <h1 class="hero-title">NL-DBMS Query Studio</h1>
        <div class="header-tags">
            <span class="header-pill"><span class="pulse-dot green"></span> Hybrid Architecture: Rule Engine + Local GPU LLM</span>
            <span class="header-pill">🗄️ MySQL: inventory_management</span>
            <span class="header-pill">⚡ Real-Time Benchmarking</span>
        </div>
    </div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# User Query Input & Voice Controls
# -----------------------------------------------------------------------------
# Voice Input Section
col_mic, col_mic_tip = st.columns([1.1, 4.9])
with col_mic:
    voice_input = speech_to_text(
        start_prompt="🎤 Speak Query",
        stop_prompt="⏹️ Stop Recording",
        just_once=True,
        use_container_width=True,
        language="en",
        key="voice_recorder_widget"
    )
with col_mic_tip:
    st.markdown("""
        <div class="voice-card">
            <span style="font-size:1.1rem;">🎙️</span>
            <span class="voice-card-text"><b>Voice Query Mode:</b> Click <b>Speak Query</b>, speak your question in natural English, then tap <b>Stop</b> to execute.</span>
        </div>
    """, unsafe_allow_html=True)

if voice_input:
    on_select_example(voice_input)
    st.rerun()

# Text Query Input Row (with Instant ✖ Clear Button)
curr_key = f"main_nl_query_{st.session_state.get('query_counter', 0)}"
if curr_key not in st.session_state:
    st.session_state[curr_key] = ""

col_input, col_clear, col_submit = st.columns([5.2, 0.5, 1.3])
with col_input:
    user_query = st.text_input(
        "Enter your natural language question:",
        key=curr_key,
        placeholder="Type your question in natural language (e.g. 'Show orders placed in January 2025' or 'Count suppliers registered')",
        label_visibility="collapsed"
    )
with col_clear:
    st.button(
        "✖",
        key="clear_query_btn",
        on_click=on_clear_query,
        help="Clear input question and results",
        use_container_width=True
    )
with col_submit:
    submitted = st.button("🚀 Run Query", type="primary", key="run_query_btn", use_container_width=True)

should_run = submitted or st.session_state.pop("execute_now", False)

if should_run:
    if not user_query or not user_query.strip():
        st.warning("Please type a question to query the database.")
    else:
        st.session_state["query_input_text"] = user_query
        st.session_state["last_executed_query"] = user_query
        # Step 0a: Fuzzy Typo & Entity Matching
        clean_query, corrections = components["fuzzy_matcher"].correct_query(user_query)

        # Step 0b: Relative & Calendar Date Parsing
        date_clause, date_desc = components["date_parser"].parse_date_expression(clean_query)

        # Show auto-correction info pills if triggered
        if corrections:
            corr_list = [f"**{c['original']}** ➔ **{c['corrected']}** ({c['score']}% match)" for c in corrections]
            st.info(f"💡 **Fuzzy Typo Auto-Corrected:** {', '.join(corr_list)}")

        if date_clause:
            st.success(f"🗓️ **Relative/Calendar Date Filter Applied:** `{date_clause}` *({date_desc})*")

        # Step 1: Preprocess (with cleaned query)
        tokens = components["preprocessor"].preprocess(clean_query)

        # Step 2: Schema Linking
        linked_schema = components["linker"].link_schema(tokens)

        # Step 3: Complexity Analysis
        analysis = components["analyzer"].analyze(tokens, linked_schema)
        complexity = analysis["complexity"]
        signals = analysis["signals"]

        # Step 4: Routing (Rule Engine vs Local LLM) + Tier 3 Auto-Healing
        if complexity == "SIMPLE":
            q_obj = components["builder"].build(linked_schema)
            candidate_sql = components["rule_engine"].generate_sql(q_obj)

            # Tier 1 & 2 Validation + Tier 3 Auto-Healing for candidate query
            valid_res = components["llm_router"].validate_and_heal(
                nl_query=clean_query,
                sql=candidate_sql,
                tokens=tokens,
                linked_schema=linked_schema
            )

            if valid_res["is_valid"]:
                sql = valid_res["sql"]
                if valid_res.get("auto_healed"):
                    generator_name = "Self-Healed (Auto-Corrected)"
                    generator_desc = f"Auto-repaired: {', '.join(valid_res.get('issues_fixed', []))}"
                    engine_badge_class = "badge-simple"
                    explanation = valid_res.get("explanation", "Auto-healed candidate query to match user intent.")
                else:
                    generator_name = "Rule-Based Engine"
                    generator_desc = "Deterministic pattern matching against schema dictionaries"
                    engine_badge_class = "badge-simple"
                    explanation = "Single-table query resolved deterministically by mapping dictionary patterns directly to schema metadata."
            else:
                # Fallback to trained local LLM when RuleEngine cannot deterministically resolve query or fails validation
                llm_result = components["llm_router"].query(
                    nl_query=clean_query,
                    linked_schema=linked_schema,
                    signals=["rule_engine_fallback"]
                )
                sql = llm_result.get("sql")
                explanation = llm_result.get("explanation", "Resolved using trained local LLM fallback.")
                if llm_result.get("auto_healed"):
                    generator_name = f"Local LLM (Self-Healed)"
                    generator_desc = f"Repaired requirements: {', '.join(llm_result.get('issues_fixed', []))}"
                else:
                    generator_name = f"Local LLM ({components['llm_router'].model_name})"
                    generator_desc = "Neural schema synthesis via local GPU LLM fallback"
                engine_badge_class = "badge-hard"
        else:
            llm_result = components["llm_router"].query(
                nl_query=clean_query,
                linked_schema=linked_schema,
                signals=signals
            )
            sql = llm_result.get("sql")
            explanation = llm_result.get("explanation", "Complex query synthesized using specialized local LLM.")
            if llm_result.get("auto_healed"):
                generator_name = f"Local LLM (Self-Healed)"
                generator_desc = f"Auto-repaired: {', '.join(llm_result.get('issues_fixed', []))}"
            else:
                generator_name = f"Local LLM ({components['llm_router'].model_name})"
                generator_desc = "Multi-table join / complex aggregation synthesized by local LLM"
            engine_badge_class = "badge-hard"

        # Step 5: Table and Metadata Explanation
        table_meta = explain_query_metadata(
            sql=sql,
            complexity=complexity,
            primary_table=linked_schema.get("table"),
            joins=linked_schema.get("joins")
        )

        # ---------------------------------------------------------------------
        # Section 1: KPI Summary Cards Grid
        # ---------------------------------------------------------------------
        badge_type = "badge-simple" if complexity == "SIMPLE" else "badge-hard"
        signals_display = ", ".join(signals) if signals else "single_table_pattern"

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        col_kpi1, col_kpi2, col_kpi3 = st.columns([1, 1.4, 1.6])

        with col_kpi1:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">Query Complexity</div>
                    <div class="stat-value">
                        <span class="metric-badge {badge_type}">● {complexity}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_kpi2:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">Active Engine</div>
                    <div class="stat-value">
                        <span class="metric-badge {engine_badge_class}">⚙️ {generator_name}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_kpi3:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">Routing Signals</div>
                    <div class="stat-value" style="font-size:0.95rem;">
                        <code style="padding: 2px 8px; border-radius: 6px;">{signals_display}</code>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # Section 2: Generated SQL (Full Width & Auto-Expanding) + Schema Link
        # ---------------------------------------------------------------------
        st.markdown("""
            <div class="feature-card-header" style="margin-bottom:0.4rem;">
                <span>💻</span>
                <span>Generated SQL Query</span>
            </div>
        """, unsafe_allow_html=True)

        if sql:
            st.code(sql, language="sql")
        else:
            st.error("Could not construct SQL query for this question.")

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Query Logic and Schema Mapping Cards
        col_exp_logic, col_exp_meta = st.columns([1.8, 1.2])

        with col_exp_logic:
            st.markdown("""
                <div class="feature-card-header">
                    <span>🧠</span>
                    <span>Query Logic & Explanation</span>
                </div>
            """, unsafe_allow_html=True)
            st.info(explanation)

        with col_exp_meta:
            st.markdown("""
                <div class="feature-card-header">
                    <span>📍</span>
                    <span>Schema Origin & References</span>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Origin:** {table_meta['source_description']}")
            if table_meta["tables"]:
                st.caption(f"Referenced Tables: {', '.join([f'`{t}`' for t in table_meta['tables']])}")

        # ---------------------------------------------------------------------
        # Section 3: Execution Metrics & Data Records
        # ---------------------------------------------------------------------
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div class="feature-card-header">
                <span>📊</span>
                <span>Database Records & Execution Benchmark</span>
            </div>
        """, unsafe_allow_html=True)

        if sql and not sql.startswith("["):
            with st.spinner("Executing against MySQL inventory_management..."):
                metrics = components["executor"].execute_with_metrics(sql)

            if metrics["success"]:
                # High-end metrics bar
                st.markdown(f"""
                    <div class="results-banner">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span class="pulse-dot green"></span>
                            <span style="font-weight:700;">Query Executed Successfully</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:18px;">
                            <span class="benchmark-badge">⏱️ {metrics['formatted_time']}</span>
                            <span style="font-size:0.85rem; font-weight:600; color:#64748B;">Latency: {metrics['execution_time_sec']}s</span>
                            <span style="font-size:0.85rem; font-weight:700; background:rgba(99,102,241,0.12); color:#4F46E5; padding:2px 8px; border-radius:6px;">{metrics['row_count']} rows</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if metrics["row_count"] > 0:
                    df = pd.DataFrame(metrics["rows"], columns=metrics["columns"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Query executed successfully, but 0 matching records were found in the database.")
            else:
                st.error(f"SQL Execution Error: {metrics['error']}")
        else:
            st.warning("Cannot execute query. Check generator output above.")
