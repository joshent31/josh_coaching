# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Whitelisted HTTP APIs powering the mobile portal and QR check-in.

All student-scoped endpoints resolve the caller's Student records via
the portal user link, so Website Users only ever see their own data.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, today

from josh_coaching.setup.qr import (
	check_in_student,
	make_session_qr_data_url,
	make_student_qr_data_url,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _current_students(user: str | None = None) -> list[str]:
	user = user or frappe.session.user
	return frappe.get_all("Student", filters={"student_user": user}, pluck="name")


def _require_student_access(student: str):
	students = _current_students()
	if student not in students and not frappe.has_role("System Manager"):
		frappe.throw(_("Not permitted to access this student"), frappe.PermissionError)
	return student


# ---------------------------------------------------------------------
# Student portal
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_my_dashboard() -> dict:
	"""Mobile dashboard payload for the logged-in portal user."""
	students = _current_students()
	out = {"students": [], "invoices": [], "sessions": []}
	for student in students:
		enrollments = frappe.get_all(
			"Enrollment",
			filters={"student": student, "status": "Active", "docstatus": 0},
			fields=["name", "program", "batch", "billing_cycle", "next_billing_date"],
		)
		attendance_pct = _attendance_percentage(student)
		out["students"].append(
			{
				"name": student,
				"student_name": frappe.db.get_value("Student", student, "student_name"),
				"photo": frappe.db.get_value("Student", student, "image"),
				"enrollments": enrollments,
				"attendance_percentage": attendance_pct,
			}
		)
		out["invoices"] += frappe.get_all(
			"Fee Invoice",
			filters={"student": student, "docstatus": 1},
			fields=[
				"name", "student", "student_name", "total_amount", "paid_amount",
				"outstanding_amount", "due_date", "status", "currency",
			],
			order_by="posting_date desc",
			limit=10,
		)
		out["sessions"] += frappe.get_all(
			"Class Session",
			filters={"session_date": [">=", today()], "status": ["in", ["Scheduled", "In Progress"]]},
			fields=["name", "batch", "session_date", "start_time", "end_time", "venue", "status"],
			order_by="session_date asc, start_time asc",
			limit=10,
		)
	return out


def _attendance_percentage(student: str) -> float:
	row = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN present IN ('Present', 'Late') THEN 1 ELSE 0 END) / COUNT(*)
		FROM `tabStudent Attendance`
		WHERE student = %(student)s""",
		{"student": student},
	)
	value = row[0][0] if row and row[0][0] is not None else 0
	return flt(value * 100, 2)


@frappe.whitelist()
def get_my_invoices() -> list[dict]:
	students = _current_students()
	return frappe.get_all(
		"Fee Invoice",
		filters={"student": ["in", students or [""]], "docstatus": 1},
		fields=[
			"name", "student", "student_name", "total_amount", "paid_amount",
			"outstanding_amount", "due_date", "status", "currency",
		],
		order_by="posting_date desc",
	)


@frappe.whitelist()
def get_my_qr_pass(student: str) -> dict:
	"""QR pass (data URL) for the student ID card."""
	_require_student_access(student)
	return {"student": student, "qr": make_student_qr_data_url(student)}


# ---------------------------------------------------------------------
# QR check-in
# ---------------------------------------------------------------------
@frappe.whitelist()
def scan_and_checkin(payload: str, session: str | None = None) -> dict:
	"""QR check-in endpoint used by the trainer app / front desk scanner."""
	if not frappe.has_role(("Academy Manager", "Academy User", "Trainer", "System Manager")):
		frappe.throw(_("Not permitted to mark QR attendance"), frappe.PermissionError)
	return check_in_student(payload, session=session)


@frappe.whitelist()
def get_session_qr(session: str) -> dict:
	"""Session poster QR (data URL) with a rotating token."""
	if not frappe.has_role(("Academy Manager", "Academy User", "Trainer", "System Manager")):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return {"session": session, "qr": make_session_qr_data_url(session)}


# ---------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------
@frappe.whitelist()
def start_payment(invoice: str, gateway: str = "Razorpay") -> dict:
	"""Create a gateway order for an outstanding invoice (portal user)."""
	students = _current_students()
	invoice_student = frappe.db.get_value("Fee Invoice", invoice, "student")
	if invoice_student not in students and not frappe.has_role("System Manager"):
		frappe.throw(_("Not permitted to pay this invoice"), frappe.PermissionError)

	from josh_coaching.payments import create_payment_order

	return create_payment_order(invoice, gateway)


@frappe.whitelist()
def confirm_payment(data: str) -> dict:
	"""Verify gateway callback and book payment + receipt."""
	from josh_coaching.payments import verify_and_book_payment

	payload = frappe.parse_json(data) if isinstance(data, str) else data
	return verify_and_book_payment(payload)


# ---------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_receipt_print(receipt: str) -> dict:
	student = frappe.db.get_value("Fee Receipt", receipt, "student")
	_require_student_access(student)
	html = frappe.get_print("Fee Receipt", receipt)
	return {"html": html}


# ---------------------------------------------------------------------
# ERPNext integration
# ---------------------------------------------------------------------
@frappe.whitelist()
def invoice_to_sales_invoice(invoice: str, submit: int = 0) -> dict:
	"""Create the ERPNext Sales Invoice for a fee invoice (desk users)."""
	if not frappe.has_role(("Academy Manager", "Accounts User", "System Manager")):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	doc = frappe.get_doc("Fee Invoice", invoice)
	name = doc.make_sales_invoice(submit=bool(cint(submit)))
	return {"name": name}
