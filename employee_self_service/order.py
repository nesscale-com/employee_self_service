import random
import time
from datetime import datetime, timedelta

import frappe


def create_random_sales_orders(number_of_orders):
    try:
        # List of predefined customers
        customers = [
            "Digital World Ltd.",
            "Future Tech Enterprises",
            "Advanced Computing Corp.",
            "Innovate IT Services",
        ]

        # Fetch all item codes
        item_codes = [
            item.name
            for item in frappe.get_all(
                "Item", filters={"is_sales_item": 1, "disabled": 0}, fields=["name"]
            )
        ]

        for _ in range(number_of_orders):
            customer = random.choice(customers)  # Randomly select a customer
            sales_order = frappe.new_doc("Sales Order")
            sales_order.customer = customer

            # Random delivery date within the next 30 days
            delivery_date = datetime.today() + timedelta(days=random.randint(0, 30))
            sales_order.delivery_date = delivery_date.strftime("%Y-%m-%d")

            sales_order.company = "Nesscale ESS"
            sales_order.set_warehouse = "Stores - NE"
            num_items = random.randint(1, 5)  # Random number of items in each order

            for _ in range(num_items):
                item_code = random.choice(item_codes)
                qty = random.randint(1, 10)  # Random quantity
                rate = random.uniform(10.0, 500.0)  # Random rate

                sales_order.append(
                    "items",
                    {
                        "item_code": item_code,
                        "qty": qty,
                        "rate": rate,
                    },
                )

            sales_order.save()
            sales_order.submit()
            frappe.db.commit()

        print(f"{number_of_orders} random sales orders created.")

    except Exception as e:
        frappe.log_error(title="error", message=frappe.get_traceback())
        print(f"Error occurred: {e}")
        time.sleep(10)  # Wait for 10 seconds before retrying
        enqueue_task(number_of_orders)  # Re-enqueue the task


def enqueue_task(number_of_orders):
    frappe.enqueue(create_random_sales_orders, number_of_orders=number_of_orders)


def schedule_random_sales_orders():
    number_of_orders = 5000  # Number of random sales orders to create
    enqueue_task(number_of_orders)
