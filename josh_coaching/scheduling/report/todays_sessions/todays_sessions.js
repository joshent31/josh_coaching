// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Today's Sessions"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.today(),
		},
		{
			fieldname: "trainer",
			label: __("Trainer"),
			fieldtype: "Link",
			options: "Coach",
			default: "",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nScheduled\nIn Progress\nCompleted\nCancelled\nNo Show",
			default: "",
		},
	],
};
