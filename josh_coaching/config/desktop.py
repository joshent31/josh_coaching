from frappe import _


def get_data():
	return [
		{
			"module_name": "Academy Core",
			"color": "#7B61FF",
			"icon": "octicon octicon-organization",
			"type": "module",
			"label": _("Academy Core"),
		},
		{
			"module_name": "Student Management",
			"color": "#29CD42",
			"icon": "octicon octicon-people",
			"type": "module",
			"label": _("Student Management"),
		},
		{
			"module_name": "Scheduling",
			"color": "#ECAD4B",
			"icon": "octicon octicon-calendar",
			"type": "module",
			"label": _("Scheduling"),
		},
		{
			"module_name": "Staff Management",
			"color": "#EC8F4B",
			"icon": "octicon octicon-id-badge",
			"type": "module",
			"label": _("Staff Management"),
		},
		{
			"module_name": "Fees Management",
			"color": "#E44258",
			"icon": "octicon octicon-credit-card",
			"type": "module",
			"label": _("Fees Management"),
		},
	]
