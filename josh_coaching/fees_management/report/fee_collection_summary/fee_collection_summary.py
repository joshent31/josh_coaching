# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Mode", "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 130},
		{"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
		{"label": "Payments", "fieldname": "payment_count", "fieldtype": "Int", "width": 90},
		{"label": "Total Collected", "fieldname": "total_collected", "fieldtype": "Currency", "width": 140},
		{"label": "Gateway Payments", "fieldname": "gateway_count", "fieldtype": "Int", "width": 130},
		{"label": "Gateway Amount", "fieldname": "gateway_amount", "fieldtype": "Currency", "width": 140},
	]

	conditions = ["docstatus = 1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("mode_of_payment"):
		conditions.append("mode_of_payment = %(mode_of_payment)s")
		values["mode_of_payment"] = filters.mode_of_payment
	if filters.get("student"):
		conditions.append("student = %(student)s")
		values["student"] = filters.student

	data = frappe.db.sql(
		f"""
		SELECT mode_of_payment, currency,
			COUNT(*) AS payment_count,
			SUM(amount) AS total_collected,
			SUM(CASE WHEN gateway IN ('Razorpay', 'Stripe', 'PayU', 'Cashfree') THEN 1 ELSE 0 END) AS gateway_count,
			SUM(CASE WHEN gateway IN ('Razorpay', 'Stripe', 'PayU', 'Cashfree') THEN amount ELSE 0 END) AS gateway_amount
		FROM `tabFee Payment`
		WHERE {' AND '.join(conditions)}
		GROUP BY mode_of_payment, currency
		ORDER BY total_collected DESC
		""",
		values,
		as_dict=1,
	)
	return columns, data
