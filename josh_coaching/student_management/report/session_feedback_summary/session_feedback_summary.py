# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Trainer", "fieldname": "trainer", "fieldtype": "Link", "options": "Coach", "width": 150},
		{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 140},
		{"label": "Feedback Count", "fieldname": "feedback_count", "fieldtype": "Int", "width": 120},
		{"label": "Avg Session Rating", "fieldname": "avg_session", "fieldtype": "Float", "width": 140},
		{"label": "Avg Trainer Rating", "fieldname": "avg_trainer", "fieldtype": "Float", "width": 140},
		{"label": "Promoters (5★)", "fieldname": "promoters", "fieldtype": "Int", "width": 110},
		{"label": "Detractors (≤2★)", "fieldname": "detractors", "fieldtype": "Int", "width": 120},
		{"label": "NPS-like %", "fieldname": "nps_pct", "fieldtype": "Percent", "width": 100},
	]

	conditions = ["1=1"]
	values = {}
	if filters.get("trainer"):
		conditions.append("trainer = %(trainer)s")
		values["trainer"] = filters.trainer
	if filters.get("batch"):
		conditions.append("batch = %(batch)s")
		values["batch"] = filters.batch
	if filters.get("from_date"):
		conditions.append("feedback_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("feedback_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT trainer, batch,
			COUNT(*) AS feedback_count,
			AVG(rating) AS avg_session,
			AVG(trainer_rating) AS avg_trainer,
			SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS promoters,
			SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS detractors,
			ROUND(
				(SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) - SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END))
				* 100.0 / NULLIF(COUNT(*), 0)
			, 2) AS nps_pct
		FROM `tabSession Feedback`
		WHERE {' AND '.join(conditions)}
		GROUP BY trainer, batch
		ORDER BY avg_session DESC
		""",
		values,
		as_dict=1,
	)
	for row in data:
		row.avg_session = flt(row.avg_session or 0, 2)
		row.avg_trainer = flt(row.avg_trainer or 0, 2)
		row.nps_pct = flt(row.nps_pct or 0)
	return columns, data
