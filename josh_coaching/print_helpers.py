# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""QR data helpers for print formats.

Standard ``frappe.get_print`` does not pass custom context, so the Student
ID Card / Session poster Jinja templates call these module-level helpers
directly (they are import-safe inside Jinja via ``frappe.utils.get_print``).
"""

from __future__ import annotations

import base64

import frappe

from josh_coaching.setup.qr import make_qr_png


def student_qr_data(student: str) -> str:
	"""Base64 QR data-URL for a student (used in print formats)."""
	try:
		doc = frappe.get_doc("Student", student)
		payload = doc.get_qr_payload()
	except Exception:  # noqa: BLE001 — print must not hard-fail on bad token
		return ""
	return _png_data_url(payload)


def session_qr_data(session: str) -> str:
	"""Base64 QR data-URL for a class session poster (print formats)."""
	try:
		doc = frappe.get_doc("Class Session", session)
		payload = f"JC-SESSION:{doc.name}:{doc.qr_token or ''}"
	except Exception:  # noqa: BLE001
		return ""
	return _png_data_url(payload)


def _png_data_url(data: str) -> str:
	b64 = base64.b64encode(make_qr_png(data)).decode()
	return f"data:image/png;base64,{b64}"
