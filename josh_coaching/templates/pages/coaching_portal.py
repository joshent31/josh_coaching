# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Please log in to view your coaching portal"), frappe.PermissionError)
	context.students = frappe.get_all("Student", filters={"student_user": frappe.session.user})
	return context
