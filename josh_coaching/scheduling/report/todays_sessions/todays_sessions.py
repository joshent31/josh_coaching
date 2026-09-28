# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Session", "fieldname": "name", "fieldtype": "Link", "options": "Class Session", "width": 150},
		{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 140},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 150},
		{"label": "Date", "fieldname": "session_date", "fieldtype": "Date", "width": 100},
		{"label": "Start", "fieldname": "start_time", "fieldtype": "Time", "width": 80},
		{"label": "End", "fieldname": "end_time", "fieldtype": "Time", "width": 80},
		{"label": "Trainer", "fieldname": "trainer", "fieldtype": "Link", "options": "Coach", "width": 140},
		{"label": "Venue", "fieldname": "venue", "fieldtype": "Data", "width": 120},
		{"label": "Attendance", "fieldname": "attendance_summary", "fieldtype": "Data", "width": 170},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
	]

	date = filters.date or today()
	conditions = ["session_date = %(date)s"]
	values = {"date": date}
	if filters.get("trainer"):
		conditions.append("trainer = %(trainer)s")
		values["trainer"] = filters.trainer
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.status

	data = frappe.db.sql(
		f"""
		SELECT name, batch, program, session_date, start_time, end_time,
			trainer, venue, attendance_summary, status
		FROM `tabClass Session`
		WHERE {' AND '.join(conditions)}
		ORDER BY start_time ASC
		""",
		values,
		as_dict=1,
	)
	return columns, data
