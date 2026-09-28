// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.query_reports["Fee Collection Summary"] = {
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
			fieldname: "mode_of_payment",
			label: __("Mode"),
			fieldtype: "Select",
			options: "\nCash\nCard\nBank Transfer\nUPI\nCheque\nOnline Gateway\nWallet",
			default: "",
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
			default: "",
		},
	],
};
