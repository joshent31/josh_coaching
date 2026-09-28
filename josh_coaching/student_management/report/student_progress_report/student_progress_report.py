# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Evaluation", "fieldname": "name", "fieldtype": "Link", "options": "Skill Evaluation", "width": 150},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 170},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 150},
		{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 130},
		{"label": "Date", "fieldname": "evaluation_date", "fieldtype": "Date", "width": 100},
		{"label": "Score", "fieldname": "total_score", "fieldtype": "Float", "width": 90},
		{"label": "Max", "fieldname": "max_score", "fieldtype": "Float", "width": 90},
		{"label": "Percentage", "fieldname": "percentage", "fieldtype": "Percent", "width": 100},
		{"label": "Recommendation", "fieldname": "recommendation", "fieldtype": "Data", "width": 170},
	]

	conditions = ["docstatus < 2"]
	values = {}
	if filters.get("student"):
		conditions.append("student = %(student)s")
		values["student"] = filters.student
	if filters.get("program"):
		conditions.append("program = %(program)s")
		values["program"] = filters.program
	if filters.get("from_date"):
		conditions.append("evaluation_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("evaluation_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT name, student, student_name, program, batch, evaluation_date,
			total_score, max_score, percentage, recommendation
		FROM `tabSkill Evaluation`
		WHERE {' AND '.join(conditions)}
		ORDER BY evaluation_date DESC
		""",
		values,
		as_dict=1,
	)
	return columns, data
