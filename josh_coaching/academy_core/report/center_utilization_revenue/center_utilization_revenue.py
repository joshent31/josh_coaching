# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Coaching Center", "fieldname": "center", "fieldtype": "Link", "options": "Coaching Center", "width": 170},
		{"label": "Active Batches", "fieldname": "active_batches", "fieldtype": "Int", "width": 110},
		{"label": "Active Students", "fieldname": "active_students", "fieldtype": "Int", "width": 110},
		{"label": "Seats", "fieldname": "total_seats", "fieldtype": "Int", "width": 80},
		{"label": "Utilization %", "fieldname": "utilization_pct", "fieldtype": "Percent", "width": 110},
		{"label": "Sessions (Period)", "fieldname": "sessions_held", "fieldtype": "Int", "width": 110},
		{"label": "Collected (Period)", "fieldname": "collected", "fieldtype": "Currency", "width": 140},
		{"label": "Outstanding", "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
	]

	from_date = filters.from_date or "2000-01-01"
	to_date = filters.to_date or today()

	data = frappe.db.sql(
		"""
		SELECT
			c.name AS center,
			(SELECT COUNT(*) FROM `tabBatch` b WHERE b.coaching_center = c.name AND b.status = 'Active') AS active_batches,
			(SELECT COUNT(*) FROM `tabEnrollment` e
				JOIN `tabBatch` b2 ON b2.name = e.batch
				WHERE b2.coaching_center = c.name AND e.status = 'Active' AND e.docstatus = 1) AS active_students,
			(SELECT COALESCE(SUM(b3.max_seats), 0) FROM `tabBatch` b3
				WHERE b3.coaching_center = c.name AND b3.status = 'Active') AS total_seats,
			(SELECT COUNT(*) FROM `tabClass Session` s
				WHERE s.coaching_center = c.name AND s.session_date BETWEEN %(from_date)s AND %(to_date)s
				AND s.status = 'Completed') AS sessions_held,
			(SELECT COALESCE(SUM(p.amount), 0) FROM `tabFee Payment` p
				JOIN `tabFee Invoice` i ON i.name = p.invoice
				JOIN `tabBatch` b4 ON b4.name = i.batch
				WHERE b4.coaching_center = c.name AND p.docstatus = 1
				AND p.posting_date BETWEEN %(from_date)s AND %(to_date)s) AS collected,
			(SELECT COALESCE(SUM(i2.outstanding_amount), 0) FROM `tabFee Invoice` i2
				JOIN `tabBatch` b5 ON b5.name = i2.batch
				WHERE b5.coaching_center = c.name AND i2.docstatus = 1
				AND i2.status IN ('Unpaid', 'Partially Paid', 'Overdue')) AS outstanding
		FROM `tabCoaching Center` c
		WHERE c.status = 'Active'
		ORDER BY collected DESC
		""",
		{"from_date": from_date, "to_date": to_date},
		as_dict=1,
	)
	for row in data:
		row.utilization_pct = (
			flt(row.active_students) * 100.0 / flt(row.total_seats) if row.total_seats else 0
		)
	return columns, data
