# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 180},
		{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 140},
		{"label": "Sessions Held", "fieldname": "total", "fieldtype": "Int", "width": 110},
		{"label": "Present", "fieldname": "present_count", "fieldtype": "Int", "width": 90},
		{"label": "Absent", "fieldname": "absent_count", "fieldtype": "Int", "width": 90},
		{"label": "Late", "fieldname": "late_count", "fieldtype": "Int", "width": 90},
		{"label": "Attendance %", "fieldname": "attendance_pct", "fieldtype": "Percent", "width": 120},
	]

	conditions = ["1=1"]
	values = {"from_date": filters.from_date or "2000-01-01", "to_date": filters.to_date or today()}
	if filters.get("batch"):
		conditions.append("batch = %(batch)s")
		values["batch"] = filters.batch
	if filters.get("student"):
		conditions.append("student = %(student)s")
		values["student"] = filters.student

	data = frappe.db.sql(
		f"""
		SELECT student, student_name, batch,
			COUNT(*) AS total,
			SUM(CASE WHEN present = 'Present' THEN 1 ELSE 0 END) AS present_count,
			SUM(CASE WHEN present = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
			SUM(CASE WHEN present = 'Late' THEN 1 ELSE 0 END) AS late_count,
			ROUND(
				SUM(CASE WHEN present IN ('Present', 'Late') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)
			, 2) AS attendance_pct
		FROM `tabStudent Attendance`
		WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s AND {' AND '.join(conditions)}
		GROUP BY student, student_name, batch
		ORDER BY attendance_pct ASC
		""",
		values,
		as_dict=1,
	)
	for row in data:
		row.attendance_pct = flt(row.attendance_pct or 0)
	return columns, data
