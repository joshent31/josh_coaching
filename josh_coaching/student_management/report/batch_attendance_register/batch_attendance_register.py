# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 100},
		{"label": "Session", "fieldname": "class_session", "fieldtype": "Link", "options": "Class Session", "width": 160},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 170},
		{"label": "Status", "fieldname": "present", "fieldtype": "Data", "width": 90},
		{"label": "Check-in", "fieldname": "checkin_time", "fieldtype": "Datetime", "width": 140},
		{"label": "Method", "fieldname": "checkin_method", "fieldtype": "Data", "width": 90},
		{"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 160},
	]

	conditions = ["1=1"]
	values = {}
	if filters.get("batch"):
		conditions.append("batch = %(batch)s")
		values["batch"] = filters.batch
	if filters.get("from_date"):
		conditions.append("attendance_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("attendance_date <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("status"):
		conditions.append("present = %(status)s")
		values["status"] = filters.status

	data = frappe.db.sql(
		f"""
		SELECT attendance_date, class_session, student, student_name, present,
			checkin_time, checkin_method, remarks
		FROM `tabStudent Attendance`
		WHERE {' AND '.join(conditions)}
		ORDER BY attendance_date DESC, student_name ASC
		""",
		values,
		as_dict=1,
	)
	return columns, data
