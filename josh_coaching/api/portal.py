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
	out = {"students": [], "invoices": [], "sessions": [], "makeup_credits": []}
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
	out["makeup_credits"] = get_my_makeup_credits()
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
# Makeup credits
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_my_makeup_credits() -> list[dict]:
	"""Open makeup credits for the portal user's students."""
	students = _current_students()
	return frappe.get_all(
		"Makeup Credit",
		filters={"student": ["in", students or [""]], "status": "Open"},
		fields=["name", "student", "student_name", "reason", "issued_on", "expires_on", "status"],
		order_by="expires_on asc",
	)


@frappe.whitelist()
def redeem_makeup_credit(credit: str, session: str) -> dict:
	"""Redeem a makeup credit for a session (portal user owns the student)."""
	doc = frappe.get_doc("Makeup Credit", credit)
	_require_student_access(doc.student)
	doc.redeem(session)
	return {"status": "ok", "credit": doc.name}


# ---------------------------------------------------------------------
# Session feedback
# ---------------------------------------------------------------------
@frappe.whitelist()
def submit_session_feedback(
	class_session: str, student: str, rating: float, trainer_rating: float | None = None, comments: str | None = None
) -> dict:
	"""Submit session feedback as a portal user (rating fields 1-5)."""
	_require_student_access(student)

	feedback = frappe.new_doc("Session Feedback")
	feedback.class_session = class_session
	feedback.student = student
	feedback.rating = rating
	feedback.trainer_rating = trainer_rating
	feedback.comments = comments
	feedback.feedback_date = today()
	feedback.insert(ignore_permissions=True)
	return {"status": "ok", "feedback": feedback.name}


@frappe.whitelist()
def get_session_feedback_summary(trainer: str | None = None) -> dict:
	"""Average session/trainer ratings, optionally scoped to a trainer."""
	conditions = ["1=1"]
	values: dict = {}
	if trainer:
		conditions.append("trainer = %(trainer)s")
		values["trainer"] = trainer

	row = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS total,
			AVG(rating) AS avg_session,
			AVG(trainer_rating) AS avg_trainer
		FROM `tabSession Feedback`
		WHERE {' AND '.join(conditions)}
		""",
		values,
		as_dict=1,
	)[0]
	return {
		"total": cint(row.total or 0),
		"avg_session_rating": flt(row.avg_session or 0, 2),
		"avg_trainer_rating": flt(row.avg_trainer or 0, 2),
	}


# ---------------------------------------------------------------------
# Progress timeline (B14)
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_progress_timeline(student: str) -> dict:
	"""Milestone feed: evaluations, certificates, events results — newest first."""
	_require_student_access(student)

	evaluations = frappe.get_all(
		"Skill Evaluation",
		filters={"student": student, "docstatus": 1},
		fields=["name", "evaluation_date", "percentage", "recommendation", "remarks", "program"],
		order_by="evaluation_date desc",
		limit=20,
	)
	certificates = frappe.get_all(
		"Certificate",
		filters={"student": student},
		fields=["name", "issue_date", "certificate_type", "level_title", "program"],
		order_by="issue_date desc",
		limit=20,
	)
	event_results = frappe.get_all(
		"Event Participant",
		filters={"student": student, "result": ["is", "set"]},
		fields=["name", "event", "result", "score_notes"],
		order_by="creation desc",
		limit=20,
	)
	return {"evaluations": evaluations, "certificates": certificates, "events": event_results}


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
