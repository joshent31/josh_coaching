# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""QR code engine.

Two QR surfaces are supported:

1. **Student ID QR** — static payload ``JC-STUDENT:<student_id>:<token>``
   printed on the ID card. Scanning it identifies the student.
2. **Session check-in QR** — rotating token on a Class Session. Students
   scan it (or the trainer scans student cards) and attendance is booked
   within the configured validity window.
"""

from __future__ import annotations

import io

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

STUDENT_PREFIX = "JC-STUDENT"
SESSION_PREFIX = "JC-SESSION"


# ---------------------------------------------------------------------
# QR image generation
# ---------------------------------------------------------------------
def make_qr_png(data: str, box_size: int = 8) -> bytes:
	"""Render a QR code PNG for arbitrary payload data."""
	try:
		import qrcode
	except ImportError:
		frappe.throw(_("Please install the 'qrcode' package to generate QR codes"))

	img = qrcode.make(data, box_size=cint(box_size) or 8)
	buffered = io.BytesIO()
	img.save(buffered, format="PNG")
	return buffered.getvalue()


def make_student_qr_data_url(student: str) -> str:
	"""Data-URL QR for a student ID card (used in portal and print formats)."""
	import base64

	student_doc = frappe.get_doc("Student", student)
	payload = student_doc.get_qr_payload()
	b64 = base64.b64encode(make_qr_png(payload)).decode()
	return f"data:image/png;base64,{b64}"


def make_session_qr_data_url(session: str) -> str:
	"""Data-URL QR for a class session check-in poster."""
	import base64

	session_doc = frappe.get_doc("Class Session", session)
	if not session_doc.qr_token:
		session_doc.generate_qr_token()
		session_doc.save(ignore_permissions=True)
	payload = f"{SESSION_PREFIX}:{session}:{session_doc.qr_token}"
	b64 = base64.b64encode(make_qr_png(payload)).decode()
	return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------
# Check-in logic
# ---------------------------------------------------------------------
def check_in_student(payload: str, session: str | None = None, method: str = "QR Code") -> dict:
	"""Book attendance for a scanned student QR payload.

	- ``payload``: decoded QR text (``JC-STUDENT:<id>:<token>``) or a raw
	  Student ID / name.
	- ``session``: Class Session the student is checking into. When None,
	  the student's next session today is used.
	"""
	student = _resolve_student(payload)
	if not student:
		frappe.throw(_("Could not identify a student from the QR payload"))

	session_name = session or _find_current_session(student)
	if not session_name:
		frappe.throw(_("No active session found for this student right now"))

	session_doc = frappe.get_doc("Class Session", session_name)
	if session_doc.status in ("Cancelled", "Completed"):
		frappe.throw(_("Session {0} is {1}").format(session_name, session_doc.status))

	_validate_window(session_doc)

	# duplicate check
	existing = frappe.db.exists(
		"Student Attendance",
		{"student": student, "class_session": session_name},
	)
	if existing:
		return {
			"status": "duplicate",
			"message": _("Attendance was already marked for {0}").format(student),
			"attendance": existing,
		}

	attendance = frappe.new_doc("Student Attendance")
	attendance.student = student
	attendance.class_session = session_name
	attendance.attendance_date = session_doc.session_date
	attendance.present = "Present"
	attendance.checkin_time = now_datetime()
	attendance.checkin_method = method
	attendance.marked_by = frappe.session.user
	attendance.insert(ignore_permissions=True)

	_pack_consume(student)

	return {
		"status": "ok",
		"message": _("Welcome, {0}! Checked in to {1}").format(
			frappe.db.get_value("Student", student, "student_name"), session_name
		),
		"attendance": attendance.name,
	}


def _pack_consume(student: str):
	"""If the student holds an active Session Pack, consume one session."""
	pack = frappe.get_all(
		"Session Pack",
		filters={"student": student, "status": "Active"},
		order_by="expires_on asc",
		limit=1,
		pluck="name",
	)
	if pack:
		try:
			frappe.get_doc("Session Pack", pack[0]).consume()
		except Exception:  # noqa: BLE001 — pack issues must not block check-in
			frappe.log_error(message=frappe.get_traceback(), title="Pack consume failed")


def _resolve_student(payload: str) -> str | None:
	payload = (payload or "").strip()
	if payload.startswith(STUDENT_PREFIX):
		parts = payload.split(":")
		if len(parts) >= 3:
			student_id, token = parts[1], parts[2]
			token_owner = frappe.db.get_value(
				"Student", {"student_id": student_id, "qr_token": token}, "name"
			)
			return token_owner
		return None
	# Fallbacks: raw student_id or Student name
	return frappe.db.get_value("Student", {"student_id": payload}, "name") or frappe.db.get_value(
		"Student", {"name": payload}, "name"
	)


def _find_current_session(student: str) -> str | None:
	"""Session today for a batch the student is actively enrolled in."""
	batches = frappe.get_all(
		"Enrollment",
		filters={"student": student, "status": "Active", "docstatus": ["<", 2]},
		pluck="batch",
	)
	if not batches:
		return None
	return frappe.db.get_value(
		"Class Session",
		{
			"batch": ["in", batches],
			"session_date": now_datetime().date(),
			"status": ["in", ["Scheduled", "In Progress"]],
		},
		"name",
		order_by="start_time asc",
	)


def _validate_window(session_doc):
	window = cint(session_doc.checkin_window_minutes or 15)
	validity = cint(
		frappe.db.get_single_value("Coaching Settings", "qr_token_validity_minutes") or 15
	)
	generated = get_datetime(session_doc.qr_generated_at) if session_doc.qr_generated_at else None
	if generated and (now_datetime() - generated).total_seconds() / 60 > max(window, validity):
		frappe.throw(
			_("QR code for session {0} has expired; generate a fresh one").format(session_doc.name)
		)
