# Personal-Finance-ETL-BI-Dashboard
End-to-end Python ETL pipeline and interactive Streamlit BI dashboard for personal finance tracking. Built with Pandas, SQLite, and Docker.

## What is this?
This is an end-to-end Data Engineering and Business Intelligence project. I built a custom ETL pipeline that parses raw, messy CSV bank statements, automatically categorizes transactions using a self-learning rule engine, loads them into a relational database, and visualizes everything in an interactive web dashboard.

*(Note: The data shown in the screenshots is generated/mocked for demonstration purposes).*

## The Tech Stack
* **Language:** Python 3
* **ETL & Data Processing:** Pandas
* **Database:** SQLite (`sqlite3`)
* **Frontend & BI:** Streamlit, Plotly Express
* **Infrastructure:** Docker

## Key Features & Engineering Highlights

* **Robust Bank CSV Parsing:** The ETL script (`etl_processor.py`) dynamically handles different file encodings (UTF-8, CP1250) and messy string formats (quotes, currency strings, varying date formats) typical for banking exports.
* **Self-Learning Categorization Engine:** The script uses an interactive CLI to categorize unknown transactions. If the user saves a rule, it updates a `rules.json` file, allowing the system to automatically tag similar transactions in the future.
* **Idempotent Database Loading:** Uses an upsert-like logic to ensure that running the ETL multiple times on the same bank statements won't duplicate transactions in the database.
* **Interactive BI Dashboard:** Built with Streamlit, featuring:
  * Dynamic timeframe granularity (Day/Week/Month).
  * Moving Average smoothing algorithms for clearer macro trendlines.
  * Deep drill-down capabilities into specific expense categories.
  * Year-over-Year comparison tool with dynamic month-range selection.

<img width="1920" height="791" alt="image" src="https://github.com/user-attachments/assets/6944db27-7a44-4905-b441-5cd6ab63b24d" />

<img width="1497" height="616" alt="image" src="https://github.com/user-attachments/assets/839cc576-e7f7-4db2-a411-82ef5dce3c9a" />

<img width="1478" height="432" alt="image" src="https://github.com/user-attachments/assets/e1579608-6bfd-4458-8da4-8a97dc41d978" />

<img width="1476" height="718" alt="image" src="https://github.com/user-attachments/assets/b4747cfa-e48d-4337-9db2-f68c5d40ee37" />

<img width="1414" height="407" alt="image" src="https://github.com/user-attachments/assets/86c159f5-3ffe-4fe0-b83f-457aac5f994e" />

## How to Run This Project (via Docker)

You don't need to install Python or set up virtual environments. Just use Docker:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Wodoroscik/Personal-Finance-ETL-BI-Dashboard.git
   cd Personal-Finance-ETL-BI-Dashboard
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t budget-dashboard .
   ```

3. **Run the container:**
   ```bash
   docker run -p 8501:8501 budget-dashboard
   ```

4. **Access the dashboard:**
   Open your browser and go to `http://localhost:8501`
