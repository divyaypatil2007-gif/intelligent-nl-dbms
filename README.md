# ⚡ NL-DBMS: Intelligent Natural Language Database Query Studio

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MySQL 8.0](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai/)
[![spaCy](https://img.shields.io/badge/spaCy-3.7+-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)](https://spacy.io/)

An enterprise-grade, privacy-preserving **Text-to-SQL Query Studio** with a **Dual-Engine Architecture** and **Tier-3 Semantic Self-Correction Loop**. It translates conversational natural language inquiries into optimized, safe MySQL queries and executes them against an inventory management relational database.

---

## 🌟 Key Features

- **⚡ Dual-Engine Hybrid Routing**:
  - **Deterministic Rule Engine**: Instantly generates deterministic SQL for single-table queries (filter, sort, project, limit) with zero LLM inference latency (< 5ms).
  - **Local LLM Router**: Seamlessly routes complex, multi-table queries involving cross-table joins, subqueries, nested aggregations, and anti-joins to a locally hosted specialized model (`inventory-sql` on Ollama).
- **🛡️ Tier-3 Semantic Self-Correction & Auto-Healing**:
  - Validates SQL syntax, schema alignment, and semantic intent via `QueryValidator`.
  - Automatically identifies missing bridge joins, invalid column references, or improper `HAVING` vs `WHERE` clauses and repairs candidate SQL queries before execution.
- **🧠 Schema Linker & Fuzzy Matching**:
  - Employs token preprocessing with phrase collapsing via **spaCy** (`en_core_web_sm`).
  - Uses **RapidFuzz** token sort matching against database metadata dictionaries (`data/*.json`) to accurately map colloquial terms to schema tables, columns, and values.
- **🎙️ Voice Query Support**:
  - Integrated speech-to-text recording directly in the Streamlit UI to query databases verbally.
- **🔒 Fully Local & Air-Gapped**:
  - Powered by local open-weight models (`qwen2.5-coder:3b` / fine-tuned `inventory-sql`). Zero external API calls, ensuring full data privacy.
- **📊 Rich Interactive UI & CLI**:
  - Modern Streamlit dashboard displaying SQL syntax highlighting, live query execution metrics, query plan explanations, and interactive data tables with CSV export.
  - Dedicated interactive CLI interface (`main.py`) and automated test runner (`test_nl_queries.py`).

---

## 🏗️ System Architecture

```
User Query (Text / Voice)
          │
          ▼
┌───────────────────────────────────────────────┐
│              NLP Preprocessor                 │
│  - Phrase Normalization & Tokenization (spaCy) │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│          Schema Linker & Fuzzy Matcher        │
│  - Table/Column/Value Mapping (RapidFuzz)     │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│             Complexity Analyzer               │
│  - Signal Detection (Joins, Aggregates, Dates)│
└──────────────┬─────────────────┬──────────────┘
               │                 │
     [SIMPLE Query]        [HARD Query / Fallback]
               │                 │
               ▼                 ▼
┌──────────────────────┐ ┌──────────────────────────────────────┐
│  Deterministic       │ │  Local LLM Router (Ollama)           │
│  Rule Engine         │ │  - Prompt with Schema Context        │
└──────────────┬───────┘ └──────────────────┬───────────────────┘
               │                            │
               └──────────────┬─────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│          Tier-3 Query Validator & Auto-Healer                 │
│  - Syntax Check, Bridge Join Verification, Intent Repair      │
└─────────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│               MySQL Database Execution Engine                 │
│  - Safe Read Execution, Timing Metrics, Tabular Formatting     │
└───────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema (`inventory_management`)

The database models a comprehensive retail and inventory supply chain:

```
[category]
    ▲
    │ (Category_ID)
[products] ◄─── (Product_ID) ───► [inventory] ◄─── (Warehouse_ID) ───► [warehouse]
    ▲                                                                       ▲
    │                                                                       │
    │ (Product_ID)                                                          │ (Warehouse_ID)
[customer_order_details]                                           [supplier_order]
    │ (Order_ID)                                                            ▲
    ▼                                                                       │ (Supplier_ID)
[customer_order] ◄─── (Customer_ID) ─── [customer]                [supplier]
```

### Relational Join Bridge Rules
1. **Customer $\leftrightarrow$ Products**: Traverses `customer` $\to$ `customer_order` $\to$ `customer_order_details` $\to$ `products`.
2. **Supplier $\leftrightarrow$ Products**: Traverses `supplier` $\to$ `supplier_order` $\to$ `products`.
3. **Products $\leftrightarrow$ Warehouse**: Traverses `products` $\to$ `inventory` $\to$ `warehouse`.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── complexity_analyzer.py   # Classifies queries as SIMPLE or HARD
│   ├── condition_extractor.py   # Extracts comparison operators and targets
│   ├── database.py              # MySQL connector with environment configuration
│   ├── date_parser.py           # Relative and absolute date range parsing
│   ├── dictionary_loader.py     # Schema dictionary caching loader
│   ├── fuzzy_matcher.py         # RapidFuzz-based entity resolution
│   ├── llm_router.py            # Local Ollama bridge with auto-healing loop
│   ├── preprocess.py            # NLP tokenization & phrase collapsing
│   ├── query_builder.py         # Internal query representation builder
│   ├── query_metadata.py       # SQL AST and explanation generation
│   ├── query_validator.py       # Syntax, schema, and intent validator
│   ├── result_formatter.py      # Console result table formatter
│   ├── rule_engine.py           # Deterministic single-table SQL generator
│   ├── schema_linker.py         # Links tokens to DB tables and columns
│   ├── schema_prompt.py         # Dynamic prompt generator with schema rules
│   └── sql_executor.py          # Executes SQL with latency & error tracking
├── data/
│   ├── aggregates.json          # Aggregate phrase mappings (COUNT, SUM, AVG)
│   ├── columns.json             # Natural language synonyms for DB columns
│   ├── comparison.json         # Numerical and string comparator keywords
│   ├── joins.json               # Schema foreign key join graphs
│   ├── logical.json             # AND/OR/NOT logical connector keywords
│   ├── operations.json          # Action verb mappings (SHOW, LIST, FIND)
│   ├── sorting.json             # Sorting order terminology (ASC, DESC)
│   ├── tables.json              # Natural language synonyms for DB tables
│   └── values.json              # Entity value mappings (payment types, etc.)
├── database/
│   └── schema.sql               # Complete MySQL DDL & Seed Data script
├── docs/                        # Project documentation and assets
├── frontend/
│   └── app.py                   # Streamlit Web UI application
├── models/
│   └── Modelfile                # Ollama custom model definition for inventory-sql
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore patterns
├── main.py                      # Interactive CLI terminal interface
├── requirements.txt             # Python project dependencies
├── test_nl_queries.py           # Automated test harness for benchmark queries
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python**: 3.10 or higher
- **MySQL Server**: 8.0 or higher
- **Ollama**: [Download Ollama](https://ollama.ai/)
- **Git**

---

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/divyaypatil2007-gif/intelligent-nl-dbms.git
   cd intelligent-nl-dbms
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download the spaCy English NLP model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

---

### 3. Database Setup

1. Start your local MySQL service.
2. Import the schema and seed dataset:
   ```bash
   mysql -u root -p < database/schema.sql
   ```
3. Verify that the `inventory_management` database is created with tables and sample records.

---

### 4. Configure Environment Variables

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=inventory_management
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=inventory-sql
```

---

### 5. Ollama Local Model Setup

1. Start Ollama:
   ```bash
   ollama serve
   ```
2. Pull the base coding model:
   ```bash
   ollama pull qwen2.5-coder:3b
   ```
3. Build the specialized `inventory-sql` model using the project `Modelfile`:
   ```bash
   ollama create inventory-sql -f models/Modelfile
   ```

---

## 💻 Running the Application

### Option A: Streamlit Interactive Web Studio (Recommended)

Launch the web studio in your browser:
```bash
streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`. Features include:
- Interactive text and voice search input
- Live generated SQL code view
- Latency and engine breakdown (Rule Engine vs Local LLM)
- Auto-healing notification badge
- Full execution result table with CSV download

### Option B: Terminal Command-Line Interface

Run the interactive CLI session:
```bash
python main.py
```

### Option C: Run Benchmark Verification Suite

Execute the pre-configured test suite across sample queries:
```bash
python test_nl_queries.py
```

---

## 💬 Example Natural Language Queries

| Query Type | Natural Language Example | Handled By |
| :--- | :--- | :--- |
| **Simple Filter** | `Show products whose warranty is 24 months` | Rule Engine |
| **Sorting & Limit** | `List the 5 most recently placed orders` | Rule Engine |
| **Stock Check** | `Which products are out of stock?` | Rule Engine |
| **Multi-Table Join** | `Show customers who ordered laptops` | LLM Router (`inventory-sql`) |
| **Subquery / Aggregates**| `Display customer who placed the most expensive order` | LLM Router (`inventory-sql`) |
| **Anti-Join** | `Which products have never been ordered?` | LLM Router (`inventory-sql`) |
| **Group Aggregates** | `Show categories having more than 3 products` | LLM Router (`inventory-sql`) |
| **Payment Breakdown**| `What is the total revenue from UPI payments?` | LLM Router (`inventory-sql`) |

---

## 🔒 Security & Privacy

- **Read-Only Enforced Execution**: The SQL executor only executes safe `SELECT` statements and prevents data modification statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`).
- **No Cloud Exposure**: All Natural Language understanding and SQL generation happens entirely on-device via Ollama.
- **Configurable Credentials**: No database secrets are hardcoded in the codebase; credentials are read safely from the local environment.

---

## 👨‍💻 Author

**Divya Patil**  
GitHub: [@divyaypatil2007-gif](https://github.com/divyaypatil2007-gif)
