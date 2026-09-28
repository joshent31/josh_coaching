// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Student Outstanding Fees"] = {
	filters: [
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
			default: "",
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			default: "",
		},
		{
			fieldname: "only_overdue",
			label: __("Only Overdue"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
