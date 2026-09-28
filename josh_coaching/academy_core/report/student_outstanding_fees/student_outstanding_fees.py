# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 180},
		{"label": "Invoice", "fieldname": "name", "fieldtype": "Link", "options": "Fee Invoice", "width": 150},
		{"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": "Total", "fieldname": "total_amount", "fieldtype": "Currency", "width": 120},
		{"label": "Paid", "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
		{"label": "Outstanding", "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 130},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": "Days Overdue", "fieldname": "days_overdue", "fieldtype": "Int", "width": 110},
	]

	conditions = ["docstatus = 1", "status in ('Unpaid', 'Partially Paid', 'Overdue')"]
	values = {}
	if filters.get("student"):
		conditions.append("student = %(student)s")
		values["student"] = filters.student
	if filters.get("batch"):
		conditions.append("batch = %(batch)s")
		values["batch"] = filters.batch
	if filters.get("only_overdue"):
		conditions.append("due_date < %(today)s")
		values["today"] = today()

	data = frappe.db.sql(
		f"""
		SELECT name, student, student_name, due_date, total_amount, paid_amount,
			outstanding_amount, status,
			GREATEST(DATEDIFF(%(today)s, due_date), 0) AS days_overdue
		FROM `tabFee Invoice`
		WHERE {' AND '.join(conditions)}
		ORDER BY due_date ASC
		""",
		values,
		as_dict=1,
	)
	return columns, data
