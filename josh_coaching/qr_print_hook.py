# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Print-format Jinja globals.

Registered via hooks.print_format_jinja_globals so ``qr_image`` is
available inside the Student ID Card and Session Check-in Poster
templates regardless of how the print is triggered.
"""

from __future__ import annotations

import frappe


def get_qr_image(doc=None, method=None) -> str:
	"""Return a base64 PNG data-URL QR for the given doc (Student/Class Session)."""
	if doc is None:
		return ""
	try:
		if doc.doctype == "Student":
			from josh_coaching.print_helpers import student_qr_data

			return student_qr_data(doc.name)
		if doc.doctype == "Class Session":
			from josh_coaching.print_helpers import session_qr_data

			return session_qr_data(doc.name)
	except Exception:  # noqa: BLE001 — printing must not hard-fail
		frappe.log_error(title="QR print render failed", message=frappe.get_traceback())
	return ""
