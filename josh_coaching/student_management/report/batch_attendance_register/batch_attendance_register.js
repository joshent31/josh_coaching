// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Batch Attendance Register"] = {
	filters: [
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			default: "",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.today(),
		},
		{
			fieldname: "status",
			label: __("Attendance Status"),
			fieldtype: "Select",
			options: "\nPresent\nAbsent\nLate\nExcused",
			default: "",
		},
	],
};
