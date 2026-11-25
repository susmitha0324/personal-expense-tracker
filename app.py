
import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
from datetime import date

st.set_page_config(
    page_title="Personal Expense Tracker",
    page_icon="💰",
    layout="wide"
)

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


def load_data():
    response = (
        supabase.table("expenses")
        .select("*")
        .order("date", desc=True)
        .execute()
    )

    df = pd.DataFrame(
        response.data,
        columns=[
            "id", "type", "category",
            "amount", "date", "description"
        ]
    )

    df = df.rename(columns={
        "type": "transaction_type",
        "date": "transaction_date"
    })

    df["amount"] = pd.to_numeric(
        df["amount"], errors="coerce"
    ).fillna(0)

    return df


st.title("💰 Personal Expense Tracker")
st.caption("Track your income and expenses easily.")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Dashboard",
        "Add Transaction",
        "Transaction History",
        "Monthly Report"
    ]
)

try:
    df = load_data()
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()


# DASHBOARD

if page == "Dashboard":

    income = df[df["transaction_type"] == "Income"]["amount"].sum()
    expenses = df[df["transaction_type"] == "Expense"]["amount"].sum()
    balance = income - expenses

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Income", f"₹{income:,.2f}")
    col2.metric("Total Expenses", f"₹{expenses:,.2f}")
    col3.metric("Remaining Balance", f"₹{balance:,.2f}")

    st.divider()
    st.subheader("Expense Analysis")

    expense_df = df[df["transaction_type"] == "Expense"]

    if not expense_df.empty:

        category_data = expense_df.groupby(
            "category"
        )["amount"].sum().reset_index()

        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                category_data,
                names="category",
                values="amount",
                title="Category-wise Expenses",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                category_data,
                x="category",
                y="amount",
                title="Expense Comparison"
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No expenses added yet.")

    st.subheader("Recent Transactions")
    st.dataframe(df.head(5), use_container_width=True, hide_index=True)


# ADD TRANSACTION

elif page == "Add Transaction":

    st.subheader("Add New Transaction")

    if "message" in st.session_state:
        st.success(st.session_state.pop("message"))

    with st.form("transaction_form"):

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Income", "Expense"]
        )

        category = st.selectbox(
            "Category",
            [
                "Food", "Travel", "Shopping",
                "Education", "Bills", "Entertainment",
                "Health", "Salary", "Other"
            ]
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=1.0,
            step=100.0
        )

        transaction_date = st.date_input(
            "Date",
            value=date.today()
        )

        description = st.text_input("Description")

        submitted = st.form_submit_button("Save Transaction")

        if submitted:
            try:
                supabase.table("expenses").insert({
                    "type": transaction_type,
                    "category": category,
                    "amount": amount,
                    "date": str(transaction_date),
                    "description": description
                }).execute()

                st.session_state["message"] = (
                    "Transaction added successfully!"
                )
                st.rerun()

            except Exception as e:
                st.error(f"Unable to save transaction: {e}")


# TRANSACTION HISTORY

elif page == "Transaction History":

    st.subheader("Transaction History")

    if not df.empty:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        transaction_id = st.selectbox(
            "Select Transaction ID",
            df["id"].tolist()
        )

        if st.button("Delete Transaction"):
            try:
                supabase.table("expenses").delete().eq(
                    "id", transaction_id
                ).execute()

                st.success("Transaction deleted!")
                st.rerun()

            except Exception as e:
                st.error(f"Unable to delete transaction: {e}")

    else:
        st.info("No transactions available.")


# MONTHLY REPORT

elif page == "Monthly Report":

    st.subheader("📅 Monthly Expense Report")

    if not df.empty:

        df["month"] = pd.to_datetime(
            df["transaction_date"],
            errors="coerce"
        ).dt.strftime("%Y-%m")

        months = sorted(
            df["month"].dropna().unique().tolist(),
            reverse=True
        )

        current_month = date.today().strftime("%Y-%m")

        if current_month not in months:
            months.insert(0, current_month)

        selected_month = st.selectbox(
            "Select Month",
            months,
            format_func=lambda x: pd.to_datetime(
                x + "-01"
            ).strftime("%B %Y")
        )

        monthly_df = df[df["month"] == selected_month].copy()

        monthly_income = monthly_df[
            monthly_df["transaction_type"] == "Income"
        ]["amount"].sum()

        monthly_expenses = monthly_df[
            monthly_df["transaction_type"] == "Expense"
        ]["amount"].sum()

        monthly_balance = monthly_income - monthly_expenses

        col1, col2, col3 = st.columns(3)

        col1.metric("Monthly Income", f"₹{monthly_income:,.2f}")
        col2.metric("Monthly Expenses", f"₹{monthly_expenses:,.2f}")
        col3.metric("Monthly Balance", f"₹{monthly_balance:,.2f}")

        st.divider()
        st.subheader("Monthly Expense Analysis")

        monthly_expense_df = monthly_df[
            monthly_df["transaction_type"] == "Expense"
        ]

        if not monthly_expense_df.empty:

            category_data = monthly_expense_df.groupby(
                "category"
            )["amount"].sum().reset_index()

            fig = px.pie(
                category_data,
                names="category",
                values="amount",
                title="Category-wise Monthly Expenses",
                hole=0.4
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No expenses recorded for this month.")

        st.subheader("Monthly Transactions")

        if not monthly_df.empty:

            report_df = monthly_df.drop(columns=["month"])

            st.dataframe(
                report_df,
                use_container_width=True,
                hide_index=True
            )

            csv = report_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Download Monthly Report",
                data=csv,
                file_name="monthly_expense_report.csv",
                mime="text/csv"
            )

        else:
            st.info("No transactions available for this month.")

    else:
        st.info("Add transactions to view your monthly report.")


# SIDEBAR

st.sidebar.divider()
st.sidebar.caption("Personal Expense Tracker")


# STYLING

st.markdown("""
<style>
.stApp {
    background-color: #f7f8fc;
}

[data-testid="stMetric"] {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

h1 {
    color: #243b55;
}

h2, h3 {
    color: #334e68;
}

[data-testid="stSidebar"] {
    background-color: #edf2f7;
}
</style>
""", unsafe_allow_html=True)
