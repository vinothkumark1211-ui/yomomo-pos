import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="YO MOMO POS", layout="wide")

conn = sqlite3.connect("momoshop_v4.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS menu(
id INTEGER PRIMARY KEY AUTOINCREMENT,
category TEXT,
item_name TEXT,
price REAL)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
order_no TEXT,
source TEXT,
is_completed INTEGER DEFAULT 0,
total_amount REAL,
created_at TEXT,
completed_at TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items(
id INTEGER PRIMARY KEY AUTOINCREMENT,
order_no TEXT,
item_name TEXT,
qty INTEGER,
price REAL)
""")
conn.commit()

cursor.execute("SELECT COUNT(*) FROM menu")
if cursor.fetchone()[0] == 0:
    menu_items = [
        ("Steamed","Mixed Veg Momo",75),
        ("Steamed","Paneer Momo",85),
        ("Steamed","Mushroom Momo",85),
        ("Steamed","Cheese Corn Momo",85),
        ("Steamed","Classic Chicken Momo",85),
        ("Steamed","Schezwan Chicken Momo",90),
        ("Steamed","Chicken Cheese Momo",95),
        ("Fried","Mixed Veg Momo",85),
        ("Fried","Paneer Momo",95),
        ("Fried","Mushroom Momo",95),
        ("Fried","Cheese Corn Momo",95),
        ("Fried","Classic Chicken Momo",95),
        ("Fried","Schezwan Chicken Momo",100),
        ("Fried","Chicken Cheese Momo",105),
        ("Kurkure","Mixed Veg Kurkure Momo",100),
        ("Kurkure","Paneer Kurkure Momo",109),
        ("Kurkure","Cheese Corn Kurkure Momo",109),
        ("Kurkure","Chicken Kurkure Momo",109),
    ]
    cursor.executemany("INSERT INTO menu(category,item_name,price) VALUES (?,?,?)", menu_items)
    conn.commit()

order_count = pd.read_sql_query("SELECT COUNT(*) c FROM orders", conn)["c"][0]
next_order_no = f"YM{order_count+1:03d}"

st.title("🍜 YO MOMO POS")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["New Order","Active Orders","Completed Orders","Reports","Menu"]
)

with tab1:
    st.subheader(f"New Order - {next_order_no}")
    source = st.selectbox("Order Source",["Walk-In","Takeaway","Swiggy","Zomato"])
    menu_df = pd.read_sql_query("SELECT * FROM menu ORDER BY category,item_name", conn)

    selected_items = []
    total_amount = 0

    for category in menu_df["category"].unique():
        st.markdown(f"### {category}")
        cat = menu_df[menu_df["category"] == category]

        for _, row in cat.iterrows():
            c1, c2 = st.columns([4,1])

            with c1:
                checked = st.checkbox(
                    f"{row['item_name']} (₹{row['price']})",
                    key=f"item_{row['id']}"
                )

            with c2:
                qty = st.number_input(
                    "Qty",
                    min_value=1,
                    value=1,
                    key=f"qty_{row['id']}"
                )

            if checked:
                total_amount += row["price"] * qty
                selected_items.append({
                    "item": row["item_name"],
                    "qty": qty,
                    "price": row["price"]
                })

    st.metric("Total Amount", f"₹{total_amount:.0f}")

    if st.button("Create Order"):
        if not selected_items:
            st.error("Please select at least one item")
        else:
            cursor.execute(
                "INSERT INTO orders(order_no,source,total_amount,created_at) VALUES (?,?,?,?)",
                (next_order_no, source, total_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

            for item in selected_items:
                cursor.execute(
                    "INSERT INTO order_items(order_no,item_name,qty,price) VALUES (?,?,?,?)",
                    (next_order_no, item["item"], item["qty"], item["price"])
                )

            conn.commit()
            st.success(f"Order {next_order_no} Created Successfully")

with tab2:
    st.subheader("Active Orders")

    active = pd.read_sql_query(
        "SELECT * FROM orders WHERE is_completed=0 ORDER BY id ASC", conn
    )

    if active.empty:
        st.info("No active orders")

    for _, order in active.iterrows():
        st.markdown("---")
        st.subheader(order["order_no"])
        st.write(f"Source: {order['source']}")
        st.write(f"Total: ₹{order['total_amount']}")

        items = pd.read_sql_query(
            f"SELECT * FROM order_items WHERE order_no='{order['order_no']}'",
            conn
        )

        st.write("Items:")
        for _, item in items.iterrows():
            st.write(f"• {item['item_name']} x {item['qty']}")

        confirm = st.checkbox(
            f"Confirm completion {order['order_no']}",
            key=f"confirm_{order['order_no']}"
        )

        if confirm and st.button(
            f"Complete {order['order_no']}",
            key=f"complete_{order['order_no']}"
        ):
            cursor.execute(
                "UPDATE orders SET is_completed=1, completed_at=? WHERE order_no=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order["order_no"])
            )
            conn.commit()
            st.rerun()

with tab3:
    st.subheader("Completed Orders")

    completed = pd.read_sql_query(
        "SELECT * FROM orders WHERE is_completed=1 ORDER BY completed_at DESC",
        conn
    )

    if completed.empty:
        st.info("No completed orders")

    for _, order in completed.iterrows():
        st.markdown("---")
        st.subheader(order["order_no"])
        st.write(f"Completed: {order['completed_at']}")
        st.write(f"Total: ₹{order['total_amount']}")

        items = pd.read_sql_query(
            f"SELECT * FROM order_items WHERE order_no='{order['order_no']}'",
            conn
        )

        st.write("Items:")
        for _, item in items.iterrows():
            st.write(f"• {item['item_name']} x {item['qty']}")

with tab4:
    st.subheader("Reports")

    orders_df = pd.read_sql_query("SELECT * FROM orders", conn)

    st.metric("Total Orders", len(orders_df))
    st.metric(
        "Total Sales",
        f"₹{orders_df['total_amount'].sum():.0f}" if not orders_df.empty else "₹0"
    )

    if not orders_df.empty:
        source_sales = orders_df.groupby("source")["total_amount"].sum().reset_index()
        st.subheader("Source Wise Sales")
        st.dataframe(source_sales, hide_index=True, use_container_width=True)

        orders_df["sale_date"] = pd.to_datetime(orders_df["created_at"])
        orders_df["month_year"] = orders_df["sale_date"].dt.strftime("%B %Y")

        month_list = sorted(orders_df["month_year"].unique(), reverse=True)

        selected_month = st.selectbox("Select Month", month_list)

        month_df = orders_df[orders_df["month_year"] == selected_month]

        daily_sales = (
            month_df.groupby(month_df["sale_date"].dt.date)
            .agg(Orders=("order_no", "count"),
                 Sales=("total_amount", "sum"))
            .reset_index()
        )

        daily_sales.columns = ["Date", "Orders", "Sales"]

        st.subheader("Monthly Date Wise Sales")
        st.dataframe(daily_sales, hide_index=True, use_container_width=True)

        st.metric(
            f"{selected_month} Total Sales",
            f"₹{daily_sales['Sales'].sum():.0f}"
        )

        items_df = pd.read_sql_query("""
            SELECT item_name, SUM(qty) qty_sold
            FROM order_items
            GROUP BY item_name
            ORDER BY qty_sold DESC
        """, conn)

        st.subheader("Top Selling Items")
        st.dataframe(items_df, hide_index=True, use_container_width=True)

with tab5:
    st.subheader("Menu")
    menu_df = pd.read_sql_query(
        "SELECT category,item_name,price FROM menu ORDER BY category,item_name",
        conn
    )
    st.dataframe(menu_df, hide_index=True, use_container_width=True)
