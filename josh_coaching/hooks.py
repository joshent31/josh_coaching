# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

app_name = "josh_coaching"
app_title = "Josh Coaching"
app_publisher = "Josh Enterprises"
app_description = "Coaching & Training Center suite for Frappe v15 + ERPNext v15: students, staff, batches, sessions, QR attendance, fee collection with gateway payments and receipts."
app_email = "admin@example.com"
app_license = "mit"
required_apps = ["frappe/erpnext"]

# Client bundles
# --------------
app_include_js = ["josh_coaching.bundle.js"]

# Fixtures
# --------
fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Academy Manager", "Academy User", "Trainer", "Student (Portal)"]]]},
	{"dt": "Notification", "filters": [["module", "in", ["Academy Core", "Student Management", "Scheduling", "Staff Management", "Fees Management"]]]},
	{"dt": "Workflow", "filters": [["document_type", "in", ["Fee Invoice"]]]},
	{"dt": "Print Format", "filters": [["module", "in", ["Academy Core", "Student Management", "Scheduling", "Staff Management", "Fees Management"]]]},
	{"dt": "Number Card", "filters": [["name", "in", ["Active Students", "Sessions Today", "Outstanding Fees", "Fees Collected This Month"]]]},
	{"dt": "Dashboard Chart", "filters": [["name", "in", ["Monthly Fee Collections", "Session Bookings by Status", "Students by Program"]]]},
]

# Installation
# ------------
before_install = "josh_coaching.install.before_install"
after_uninstall = "josh_coaching.install.after_uninstall"

# Document Events
# ----------------
doc_events = {
	"Student": {
		"on_update": "josh_coaching.utils.sync_workflow_status",
	},
	"Batch": {
		"on_update": "josh_coaching.utils.sync_workflow_status",
	},
}

# Scheduled Tasks
# ----------------
scheduler_events = {
	"daily": [
		"josh_coaching.tasks.daily",
	],
	"hourly": [
		"josh_coaching.tasks.hourly",
	],
}
