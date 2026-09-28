# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt


def before_install():
	make_custom_fields()


def after_uninstall():
	delete_custom_fields()


def make_custom_fields():
	"""Traceability links on ERPNext core doctypes.

	- Sales Invoice / Sales Invoice Item: link a fee invoice to the ERP
	  document that realizes revenue.
	- Customer: portal identity of the paying guardian for a student.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Sales Invoice": [
				{
					"fieldname": "coaching_fee_invoice",
					"label": "Coaching Fee Invoice",
					"fieldtype": "Link",
					"options": "Fee Invoice",
					"insert_after": "customer",
					"print_hide": 1,
					"no_copy": 1,
				}
			],
			"Sales Invoice Item": [
				{
					"fieldname": "coaching_fee_component",
					"label": "Coaching Fee Component",
					"fieldtype": "Link",
					"options": "Fee Component",
					"insert_after": "item_code",
					"print_hide": 1,
					"no_copy": 1,
				}
			],
			"Customer": [
				{
					"fieldname": "coaching_student",
					"label": "Coaching Student",
					"fieldtype": "Link",
					"options": "Student",
					"insert_after": "customer_group",
					"print_hide": 1,
					"no_copy": 1,
				}
			],
		},
		ignore_validate=True,
	)


def delete_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import delete_custom_fields

	delete_custom_fields(
		{
			"Sales Invoice": ["coaching_fee_invoice"],
			"Sales Invoice Item": ["coaching_fee_component"],
			"Customer": ["coaching_student"],
		}
	)
