import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os

st.set_page_config(page_title="Financial Analytics", layout="wide")
st.title("Personal Budget Dashboard")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'budget.db')

@st.cache_data 
def load_data():
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
    if cursor.fetchone() is None:
        conn.close()
        return None
        
    # Table exists, load the data
    df = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()
    
    if df.empty:
        return None
        
    # DATA CLEANING
    df = df.dropna(subset=['Year'])
    df['Year'] = df['Year'].astype(int)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    return df

df = load_data()

if df is None or df.empty:
    st.error(f"No data found in database at:\n{DB_PATH}\n\nPlease run 'python etl_processor.py' first to generate the database.")
    st.stop()

# FILTERS & SETTINGS
st.sidebar.header("Global Filters")
all_years = sorted(df['Year'].unique())
selected_year = st.sidebar.multiselect(
    "Select Year (for Main Dashboard)",
    options=all_years,
    default=all_years
)

if not selected_year:
    st.warning("Please select at least one year from the sidebar.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.header("Chart Settings")

granularity = st.sidebar.select_slider(
    "Time Granularity (X-Axis)",
    options=["Month", "Week", "Day"],
    value="Month",
    help="Select 'Day' or 'Week' for deeper insights."
)

smooth_window = st.sidebar.slider(
    "Smoothing (Moving Average)",
    min_value=0,
    max_value=60,
    value=0,
    help="0 = Raw data. Increase to smooth out the trendline."
)

df_filtered = df[df['Year'].isin(selected_year)].copy()

freq_mapping = {'Month': 'MS', 'Week': 'W-MON', 'Day': 'D'}
current_freq = freq_mapping[granularity]

if granularity == "Month":
    df_filtered['Period'] = df_filtered['Date'].dt.to_period('M').dt.to_timestamp()
elif granularity == "Week":
    df_filtered['Period'] = df_filtered['Date'].dt.to_period('W').dt.to_timestamp()
else:
    df_filtered['Period'] = df_filtered['Date']

df_expenses = df_filtered[df_filtered['Type'] == 'Expense']
df_income = df_filtered[df_filtered['Type'] == 'Income']

def get_trend_data(source_df, group_col, value_col='Amount'):
    if source_df.empty:
        return pd.DataFrame(columns=['Period', group_col, value_col])

    grouped = source_df.groupby(['Period', group_col])[value_col].sum().reset_index()
    
    if smooth_window > 0:
        pivoted = grouped.pivot(index='Period', columns=group_col, values=value_col).fillna(0)
        if not pivoted.empty:
            full_idx = pd.date_range(pivoted.index.min(), pivoted.index.max(), freq=current_freq)
            pivoted = pivoted.reindex(full_idx, fill_value=0)
            pivoted = pivoted.rolling(window=smooth_window, min_periods=1).mean()
            grouped = pivoted.reset_index().melt(id_vars='index', var_name=group_col, value_name=value_col)
            grouped = grouped.rename(columns={'index': 'Period'})
    
    return grouped


tab1, tab2 = st.tabs(["📊 Main Dashboard", "⚖️ Year-over-Year Comparison"])

with tab1:
    total_income = df_income['Amount'].sum()
    total_expense = df_expenses['Amount'].sum()
    savings = total_income - total_expense
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Income", f"{total_income:,.2f} PLN")
    col2.metric("Total Expenses", f"{total_expense:,.2f} PLN")
    col3.metric("Savings (Cash Flow)", f"{savings:,.2f} PLN", delta_color="normal")
    col4.metric("Savings Rate", f"{savings_rate:.1f}%")

    st.markdown("---")

    st.subheader("📈 Macro Trend: Income vs Expenses")
    macro_trend = get_trend_data(df_filtered, 'Type')
    title_suffix = f"(Smoothed: {smooth_window} days)" if smooth_window > 0 else "(Raw Data)"
    
    fig_macro = px.line(
        macro_trend, x='Period', y='Amount', color='Type',
        markers=True if (granularity == 'Month' or smooth_window == 0) else False,
        color_discrete_map={'Income': '#2ECC71', 'Expense': '#E74C3C'},
        title=f"Financial Cash Flow - {granularity} {title_suffix}"
    )
    fig_macro.update_layout(xaxis_title="Date", yaxis_title="Amount (PLN)")
    st.plotly_chart(fig_macro, use_container_width=True)

    st.markdown("---")

    st.subheader("📊 Expense Structure & Category Trends")
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("**Category Share in Total Expenses**")
        category_stats = df_expenses.groupby('Group')['Amount'].sum().reset_index()
        category_stats['% Share'] = (category_stats['Amount'] / total_expense * 100) if total_expense > 0 else 0
        category_stats = category_stats.sort_values('Amount', ascending=False)
        
        st.dataframe(
            category_stats.style.format({'Amount': '{:,.2f}', '% Share': '{:.1f}%'})
            .background_gradient(subset=['Amount'], cmap='Reds'),
            hide_index=True, use_container_width=True
        )

    with col_right:
        st.markdown("**Trend Comparison**")
        top_5_categories = category_stats.head(5)['Group'].tolist()
        selected_trend_groups = st.multiselect(
            "Select categories to compare:",
            options=sorted(df_expenses['Group'].unique() if not df_expenses.empty else []),
            default=top_5_categories
        )
        
        if selected_trend_groups:
            trend_data_subset = df_expenses[df_expenses['Group'].isin(selected_trend_groups)]
            trend_data_grouped = get_trend_data(trend_data_subset, 'Group')
            
            fig_trend = px.line(
                trend_data_grouped, x='Period', y='Amount', color='Group',
                markers=True if (granularity == 'Month' or smooth_window == 0) else False,
                title=f"Expense Dynamics ({granularity})", render_mode="svg"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Select categories from the list above.")

    st.markdown("---")

    st.header("🔍 Category Drill-down")
    st.markdown("Deep dive into sub-categories of a specific group.")

    all_groups = sorted(df_filtered['Group'].unique() if 'Group' in df_filtered.columns else [])
    target_group = st.selectbox("Select Group to Analyze:", options=all_groups)

    if target_group:
        subset = df_filtered[df_filtered['Group'] == target_group]
        subset_trend = get_trend_data(subset, 'Category')
        
        fig_sub = px.line(
            subset_trend, x='Period', y='Amount', color='Category',
            markers=True if (granularity == 'Month' or smooth_window == 0) else False,
            title=f"Sub-category Trend for: {target_group} ({granularity})"
        )
        st.plotly_chart(fig_sub, use_container_width=True)
        
        st.markdown(f"**Summary for: {target_group}**")
        sub_stats = subset.groupby('Category')['Amount'].sum().reset_index()
        total_sub = sub_stats['Amount'].sum()
        sub_stats['% of Group'] = (sub_stats['Amount'] / total_sub * 100) if total_sub > 0 else 0
        sub_stats = sub_stats.sort_values('Amount', ascending=False)
        
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(
                sub_stats.style.format({'Amount': '{:,.2f}', '% of Group': '{:.1f}%'}),
                hide_index=True, use_container_width=True
            )
        with c2:
            fig_pie = px.pie(sub_stats, values='Amount', names='Category', title=f"Value Distribution: {target_group}")
            st.plotly_chart(fig_pie, use_container_width=True)


with tab2:
    st.header("⚖️ Year-over-Year Comparison (Month Range)")
    
    months_dict = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    months_names = list(months_dict.values())
    
    st.markdown("### ⚙️ Comparison Configuration")
    col_yoy1, col_yoy2 = st.columns(2)
    
    with col_yoy1:
        month_range = st.select_slider(
            "Select month range:",
            options=months_names,
            value=("January", "March") 
        )
        start_month_name, end_month_name = month_range
        start_month_num = [k for k, v in months_dict.items() if v == start_month_name][0]
        end_month_num = [k for k, v in months_dict.items() if v == end_month_name][0]
        
    with col_yoy2:
        selected_years_yoy = st.multiselect(
            "Select years to compare:", 
            options=all_years, 
            default=all_years[-2:] if len(all_years) >= 2 else all_years
        )
        
    if len(selected_years_yoy) > 0:
        df_yoy = df.copy()
        df_yoy['Month_Num'] = df_yoy['Date'].dt.month
        
        df_yoy_filtered = df_yoy[
            (df_yoy['Month_Num'] >= start_month_num) & 
            (df_yoy['Month_Num'] <= end_month_num) & 
            (df_yoy['Year'].isin(selected_years_yoy))
        ]
        
        if not df_yoy_filtered.empty:
            st.markdown("---")
            
            range_title = f"{start_month_name} - {end_month_name}" if start_month_name != end_month_name else start_month_name
            
            yoy_general = df_yoy_filtered.groupby(['Year', 'Type'])['Amount'].sum().reset_index()
            yoy_general['Year'] = yoy_general['Year'].astype(str)
            
            fig_yoy_bar = px.bar(
                yoy_general, x='Year', y='Amount', color='Type', barmode='group', text_auto='.2s',
                color_discrete_map={'Income': '#2ECC71', 'Expense': '#E74C3C'},
                title=f"Total Income and Expenses: {range_title}"
            )
            fig_yoy_bar.update_layout(xaxis_title="Year", yaxis_title="Amount (PLN)")
            st.plotly_chart(fig_yoy_bar, use_container_width=True)
            
            st.markdown(f"### Detailed Expenses (Groups) for period: {range_title}")
            df_yoy_expenses = df_yoy_filtered[df_yoy_filtered['Type'] == 'Expense']
            
            if not df_yoy_expenses.empty:
                table_yoy = df_yoy_expenses.groupby(['Group', 'Year'])['Amount'].sum().unstack(fill_value=0)
                
                if len(selected_years_yoy) >= 2:
                    table_yoy['Difference (Max - Min year)'] = table_yoy.max(axis=1) - table_yoy.min(axis=1)
                
                st.dataframe(
                    table_yoy.style.format("{:,.2f} PLN").background_gradient(cmap='Oranges', axis=None),
                    use_container_width=True
                )
            else:
                st.info(f"No expenses found in {range_title} for selected years.")
                
        else:
            st.info(f"No data available for {start_month_name} - {end_month_name} in selected years.")
    else:
        st.warning("Please select at least one year to compare.")