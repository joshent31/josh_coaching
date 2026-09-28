// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Student Progress Report"] = {
	filters: [
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
			default: "",
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
			default: "",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: "",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: "",
		},
	],
};
