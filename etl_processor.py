import pandas as pd
import json
import os
import glob
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
DB_FILE = 'budget.db'
RULES_FILE = 'rules.json'

CATEGORIES_MENU = {
    '1': ('Hygiene', 'Hairdresser'),
    '2': ('Hygiene', 'Cosmetics'),
    '3': ('Investing', 'Stock Market'),
    '4': ('Investing', 'Bonds'),
    '5': ('Investments (income)', 'Bank interest'),
    '6': ('Investments (income)', 'Stock market income'),
    '7': ('Investments (income)', 'Bond profit'),
    '8': ('Dining out', 'Dining out'),
    '9': ('Housing', 'Other'),
    '10': ('Housing', 'Fixed fee'),
    '11': ('Healthcare', 'Medical tests'),
    '12': ('Healthcare', 'Other'),
    '13': ('Healthcare', 'Medicine'),
    '14': ('Healthcare', 'Doctor'),
    '15': ('Healthcare', 'Supplements'),
    '16': ('Gifts', 'Gifts'),
    '17': ('Loan income', 'Loan installment'),
    '18': ('Entertainment', 'Escape Room'),
    '19': ('Entertainment', 'Gaming'),
    '20': ('Entertainment', 'Other'),
    '21': ('Entertainment', 'Travel'),
    '22': ('Telecommunications', 'Internet'),
    '23': ('Telecommunications', 'Phone'),
    '24': ('Transport', 'Other'),
    '25': ('Transport', 'Public transport'),
    '26': ('Transport', 'Trains'),
    '27': ('Transport', 'Uber'),
    '28': ('Clothing', 'Shoes'),
    '29': ('Clothing', 'Other'),
    '30': ('Clothing', 'Clothing'),
    '31': ('Household', 'Household'),
    '32': ('Salary', 'Bonus'),
    '33': ('Salary', 'Salary'),
    '34': ('Other income', 'Other income'),
    '35': ('Other income', 'Sales'),
    '36': ('Other expenses', 'Education'),
    '37': ('Other expenses', 'Other'),
    '38': ('Other expenses', 'Software'),
    '0': ('SKIP', 'SKIP')
}

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_rules(rules):
    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=4, ensure_ascii=False)

def get_category_interactive(desc, amount, rules):
    desc_upper = str(desc).upper()
    
    # 1. Check if rule exists in learning dictionary
    for keyword, cat_data in rules.items():
        if keyword in desc_upper:
            return cat_data['Grupa'], cat_data['Kategoria'], True

    # 2. Interactive Mode for unknown transactions
    print("\n" + "="*60)
    print(f"NEW TRANSACTION: {amount} PLN")
    print(f"DESCRIPTION: {desc}")
    print("-" * 60)
    
    sorted_keys = sorted(CATEGORIES_MENU.keys(), key=lambda x: int(x))
    for k in sorted_keys:
        grp, cat = CATEGORIES_MENU[k]
        print(f"[{k:>2}] {grp} - {cat}")
    
    while True:
        choice = input(f"\nSelect category (or type custom 'Group/Category'): ")
        
        selected_grp, selected_cat = None, None
        
        if choice in CATEGORIES_MENU:
            if choice == '0': return None, None, False 
            selected_grp, selected_cat = CATEGORIES_MENU[choice]
            break
        elif '/' in choice:
            parts = choice.split('/')
            if len(parts) == 2:
                selected_grp, selected_cat = parts[0].strip(), parts[1].strip()
                break
        
        print("Invalid choice. Try again.")

    # 3. Learning step
    print(f"\nSelected: {selected_grp} / {selected_cat}")
    save_decision = input("Save this rule for the future? [y/N]: ").lower()
    
    if save_decision == 'y':
        default_keyword = desc_upper[:20] 
        keyword_input = input(f"Enter keyword to trigger this rule (Enter = '{default_keyword}'): ").upper()
        final_keyword = keyword_input if keyword_input.strip() else default_keyword
        
        rules[final_keyword] = {'Grupa': selected_grp, 'Kategoria': selected_cat}
        save_rules(rules)
        print(f"-> RULE SAVED: '{final_keyword}' -> {selected_grp}")
    else:
        print("-> Assigned for this transaction only.")

    return selected_grp, selected_cat, False

def parse_bank_csv_robust(file_path):
    """Robust parser for bank CSV files with encoding detection."""
    encodings = ['cp1250', 'utf-8', 'iso-8859-2']
    lines = []
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
            
    if not lines:
        return []

    rows = []
    start = False
    for line in lines:
        if 'Data operacji' in line and 'Kwota' in line:
            start = True
            continue
        if not start: continue
        
        parts = line.strip().split(',')
        if len(parts) < 4: continue
        
        try:
            dt_str = parts[0].strip().replace('"', '').replace("'", "")
            
            try:
                dt = pd.to_datetime(dt_str, format='%Y-%m-%d') 
            except:
                try:
                    dt = pd.to_datetime(dt_str, format='%m-%d-%y') 
                except:
                    dt = pd.to_datetime(dt_str, format='%d.%m.%Y') 
                
            amt_str = parts[3].strip().replace('"', '').replace('PLN', '').replace(' ', '').replace(',', '.')
            amt = float(amt_str)
            desc = " ".join(parts[5:]).replace('"', '').replace("'", "")
            
            rows.append({
                'DateObj': dt,
                'Amount': amt,
                'Description': desc
            })
        except Exception as e:
            continue
    return rows

def main():
    rules = load_rules()
    print(f"Loaded {len(rules)} categorization rules.")

    # Database connection (SQLite)
    conn = sqlite3.connect(DB_FILE)
    
# Check if table exists, then load or create empty dataframe
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
    if cursor.fetchone():
        df_master = pd.read_sql("SELECT * FROM transactions", conn)
    else:
        df_master = pd.DataFrame(columns=['Date', 'Year', 'Month', 'Type', 'Group', 'Category', 'Amount'])

    bank_files = glob.glob("Zestawienie*.csv")
    if not bank_files:
        print("No 'Zestawienie*.csv' files found in the directory.")
        return

    new_entries = []

    for b_file in bank_files:
        print(f"\nProcessing file: {b_file}")
        raw_rows = parse_bank_csv_robust(b_file)
        
        for row in raw_rows:
            date_str = row['DateObj'].strftime('%Y-%m-%d')
            
            # Duplicate check based on exact date and absolute amount
            if not df_master.empty:
                is_duplicate = ((df_master['Date'] == date_str) & 
                               (df_master['Amount'].abs() == abs(row['Amount']))).any()
                
                if is_duplicate:
                    continue

            grp, cat, is_auto = get_category_interactive(row['Description'], row['Amount'], rules)
            if grp is None: continue 

            if is_auto:
                print(f"AUTO: {row['Description'][:30]}... -> {grp} ({cat})")

            tx_type = 'Income' if row['Amount'] > 0 else 'Expense'
            new_entries.append({
                'Date': date_str,
                'Year': row['DateObj'].year,
                'Month': row['DateObj'].month,
                'Type': tx_type,
                'Group': grp,
                'Category': cat,
                'Amount': abs(row['Amount'])
            })

    if new_entries:
        df_new = pd.DataFrame(new_entries)
        df_final = pd.concat([df_master, df_new], ignore_index=True)
        
        df_final = df_final.sort_values('Date', ascending=False)
        df_final.to_sql('transactions', conn, if_exists='replace', index=False)
        
        print("\n" + "="*60)
        print(f"SUCCESS! Added {len(new_entries)} new transactions.")
        print(f"Updated SQLite database: {DB_FILE}")
    else:
        print("\nNo new transactions found to process.")
        
    conn.close()

if __name__ == "__main__":
    main()