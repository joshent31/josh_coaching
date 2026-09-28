# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""WhatsApp / SMS notifications.

Configure a generic SMS/WhatsApp gateway in Coaching Settings (URL +
params template) or use ERPNext's built-in SMS gateway. Events:
fee due / overdue, absence, session reminder. Templates are plain-text
with ``{{ student_name }}`` style placeholders (safe render).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

EVENTS = ("fee_due", "absence", "session_reminder")


def _gateway_enabled() -> bool:
	return bool(
		frappe.db.get_single_value("Coaching Settings", "sms_gateway_url")
		or frappe.db.get_single_value("Coaching Settings", "whatsapp_gateway_url")
	)


def send_sms(to_number: str, message: str, event: str | None = None) -> bool:
	url = frappe.db.get_single_value("Coaching Settings", "sms_gateway_url")
	return _dispatch(url, to_number, message, event)


def send_whatsapp(to_number: str, message: str, event: str | None = None) -> bool:
	url = frappe.db.get_single_value("Coaching Settings", "whatsapp_gateway_url")
	return _dispatch(url, to_number, message, event)


def _dispatch(url: str | None, to_number: str, message: str, event: str | None) -> bool:
	if not url or not to_number:
		return False
	import requests

	params_tpl = frappe.db.get_single_value("Coaching Settings", "sms_gateway_params") or ""
	try:
		rendered = frappe.render_template(params_tpl, {"to": to_number, "message": message, "event": event})
		requests.post(url, data=rendered.encode() if isinstance(rendered, str) else rendered, timeout=10)
		frappe.logger().info(f"josh_coaching: {event or 'sms'} sent to {to_number}")
		return True
	except Exception:  # noqa: BLE001 — notifications must never break flows
		frappe.log_error(
			title=_("Gateway notification failed"),
			message=frappe.get_traceback(),
		)
		return False


# ---------------------------------------------------------------------
# Event senders
# ---------------------------------------------------------------------
def notify_absence(student: str, attendance_date: str):
	"""Absence alert to guardian."""
	if not cint(frappe.db.get_single_value("Coaching Settings", "notify_absence_enabled")):
		return
	student_doc = frappe.get_doc("Student", student)
	message = _render(
		"absence",
		{
			"student_name": student_doc.student_name,
			"date": attendance_date,
			"academy": frappe.db.get_single_value("Coaching Settings", "academy_name") or "the academy",
		},
	)
	_send_to_guardian(student_doc, message, event="absence")


def notify_fee_due(invoice):
	"""Fee due / overdue alert to guardian."""
	if not cint(frappe.db.get_single_value("Coaching Settings", "notify_fee_enabled")):
		return
	student_doc = frappe.get_doc("Student", invoice.student)
	message = _render(
		"fee_due",
		{
			"student_name": student_doc.student_name,
			"amount": frappe.utils.fmt_money(invoice.outstanding_amount, currency=invoice.currency),
			"due_date": invoice.due_date,
			"invoice": invoice.name,
		},
	)
	_send_to_guardian(student_doc, message, event="fee_due")


def notify_session_reminder(session, student_list: list[str]):
	"""Session reminder to each enrolled student's guardian."""
	if not cint(frappe.db.get_single_value("Coaching Settings", "notify_session_enabled")):
		return
	for student in student_list:
		student_doc = frappe.get_doc("Student", student)
		message = _render(
			"session_reminder",
			{
				"student_name": student_doc.student_name,
				"batch": session.batch,
				"date": session.session_date,
				"start_time": session.start_time,
				"venue": session.venue or "the usual venue",
			},
		)
		_send_to_guardian(student_doc, message, event="session_reminder")


def _send_to_guardian(student_doc, message: str, event: str):
	for number in filter(None, [student_doc.guardian_mobile, student_doc.student_mobile]):
		if frappe.db.get_single_value("Coaching Settings", "whatsapp_gateway_url"):
			send_whatsapp(number, message, event=event)
		else:
			send_sms(number, message, event=event)


def _render(event: str, context: dict) -> str:
	defaults = {
		"absence": _("Dear parent, {{ student_name }} was marked absent on {{ date }}. — {{ academy }}"),
		"fee_due": _(
			"Dear parent, fees of {{ amount }} for {{ student_name }} are due on {{ due_date }} ({{ invoice }})."
		),
		"session_reminder": _(
			"Reminder: {{ student_name }}'s {{ batch }} session on {{ date }} at {{ start_time }}, {{ venue }}."
		),
	}
	tpl = frappe.db.get_single_value("Coaching Settings", f"sms_template_{event}") or defaults.get(event, "")
	try:
		return frappe.render_template(tpl, context)
	except Exception:  # noqa: BLE001
		return tpl
