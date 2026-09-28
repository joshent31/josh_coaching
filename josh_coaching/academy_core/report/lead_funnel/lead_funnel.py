# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": "Trial Status", "fieldname": "trial_status", "fieldtype": "Data", "width": 110},
		{"label": "Leads", "fieldname": "lead_count", "fieldtype": "Int", "width": 90},
		{"label": "Trials Attended", "fieldname": "trials_attended", "fieldtype": "Int", "width": 120},
		{"label": "Converted", "fieldname": "converted", "fieldtype": "Int", "width": 100},
		{"label": "Conversion %", "fieldname": "conversion_pct", "fieldtype": "Percent", "width": 110},
	]

	conditions = ["1=1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("creation >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("creation <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("source"):
		conditions.append("source = %(source)s")
		values["source"] = filters.source
	if filters.get("program"):
		conditions.append("interested_program = %(program)s")
		values["program"] = filters.program

	data = frappe.db.sql(
		f"""
		SELECT status, trial_status,
			COUNT(*) AS lead_count,
			SUM(CASE WHEN trial_status = 'Attended' THEN 1 ELSE 0 END) AS trials_attended,
			SUM(CASE WHEN status = 'Converted' THEN 1 ELSE 0 END) AS converted,
			ROUND(SUM(CASE WHEN status = 'Converted' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2)
				AS conversion_pct
		FROM `tabLead Inquiry`
		WHERE {' AND '.join(conditions)}
		GROUP BY status, trial_status
		ORDER BY lead_count DESC
		""",
		values,
		as_dict=1,
	)
	return columns, data
