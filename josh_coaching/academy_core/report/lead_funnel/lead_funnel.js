// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Lead Funnel"] = {
	filters: [
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
			fieldname: "source",
			label: __("Source"),
			fieldtype: "Select",
			options: "\nWalk-in\nPhone\nWebsite\nSocial Media\nReferral\nEvent\nOther",
			default: "",
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
			default: "",
		},
	],
};
