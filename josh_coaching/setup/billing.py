# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Auto-billing engine.

- Recurring invoices are generated from Active Enrollments a configurable
  number of days ahead of ``next_billing_date`` (idempotent — one invoice
  per enrollment per billing period).
- Late fees are auto-applied to Overdue invoices using the configured
  Late Fee Component + flat amount.

All functions are safe to run repeatedly from the scheduler.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate, today


# ---------------------------------------------------------------------
# Recurring invoice generation
# ---------------------------------------------------------------------
def generate_recurring_invoices(days_ahead: int | None = None) -> list[str]:
	"""Create Fee Invoices for enrollments whose next billing date is due.

	An invoice is only created if none exists for the same enrollment and
	billing period, making the daily job idempotent.
	"""
	settings = frappe.get_single("Coaching Settings")
	days_ahead = cint(days_ahead if days_ahead is not None else settings.auto_bill_days_ahead or 5)
	horizon = add_days(today(), days_ahead)

	enrollments = frappe.get_all(
		"Enrollment",
		filters={
			"status": "Active",
			"docstatus": 1,
			"fee_plan": ["is", "set"],
			"next_billing_date": ["<=", horizon],
			"freeze_status": ["is", "not set"],
		},
		fields=["name", "student", "batch", "fee_plan", "billing_cycle", "next_billing_date", "discount_percent"],
	)

	created = []
	for enr in enrollments:
		if _invoice_exists_for_period(enr.name, enr.next_billing_date):
			continue
		try:
			inv = _make_invoice_from_enrollment(enr)
			_advance_billing_date(enr.name, enr.billing_cycle, enr.next_billing_date)
			created.append(inv.name)
		except Exception:  # noqa: BLE001 — log and continue with remaining enrollments
			frappe.log_error(
				title=_("Auto-billing failed for enrollment {0}").format(enr.name),
				message=frappe.get_traceback(),
			)
	if created:
		frappe.db.commit()
	return created


def _invoice_exists_for_period(enrollment: str, billing_date: str) -> bool:
	period = _period_label(billing_date)
	return bool(
		frappe.db.exists(
			"Fee Invoice",
			{"enrollment": enrollment, "billing_period": period, "docstatus": ["<", 2]},
		)
	)


def _period_label(billing_date: str) -> str:
	return getdate(billing_date).strftime("%b %Y")


def _effective_discount(enr) -> float:
	"""Enrollment discount, bumped to the sibling discount when a sibling is also enrolled."""
	base = flt(enr.discount_percent)
	sibling_pct = flt(frappe.db.get_single_value("Coaching Settings", "sibling_discount_percent") or 0)
	if not sibling_pct:
		return base
	sibling = frappe.db.get_value("Student", enr.student, "sibling")
	if not sibling:
		return base
	sibling_enrolled = frappe.db.exists(
		"Enrollment",
		{"student": sibling, "status": "Active", "docstatus": 1},
	)
	return max(base, sibling_pct) if sibling_enrolled else base


def _make_invoice_from_enrollment(enr) -> object:
	plan = frappe.get_doc("Fee Plan", enr.fee_plan)
	invoice = frappe.new_doc("Fee Invoice")
	invoice.student = enr.student
	invoice.enrollment = enr.name
	invoice.batch = enr.batch
	invoice.posting_date = nowdate()
	invoice.due_date = enr.next_billing_date
	invoice.currency = plan.currency
	invoice.billing_period = _period_label(enr.next_billing_date)

	discount = _effective_discount(enr)
	for row in plan.components:
		amount = flt(row.amount)
		if discount:
			amount = flt(amount * (100 - discount) / 100, 2)
		invoice.append(
			"items",
			{
				"fee_component": row.fee_component,
				"fee_component_name": row.component_name,
				"qty": 1,
				"amount": amount,
			},
		)
	invoice.insert(ignore_permissions=True)
	return invoice


def _advance_billing_date(enrollment: str, cycle: str, current_date: str):
	"""Push next_billing_date one cycle forward."""
	from josh_coaching.student_management.enrollment import CYCLE_MONTHS

	months = CYCLE_MONTHS.get(cycle, 1)
	if not months:  # One-Time: stop billing
		frappe.db.set_value("Enrollment", enrollment, "next_billing_date", None)
		return
	frappe.db.set_value("Enrollment", enrollment, "next_billing_date", add_months(current_date, months))


def add_months(date_str: str, months: int) -> str:
	from frappe.utils import add_months as _add_months

	return _add_months(date_str, months)


# ---------------------------------------------------------------------
# Late fees
# ---------------------------------------------------------------------
def apply_late_fees() -> list[str]:
	"""Add the late-fee line to Overdue invoices that don't have it yet."""
	settings = frappe.get_single("Coaching Settings")
	component = settings.late_fee_component
	amount = flt(settings.late_fee_amount)
	if not component or amount <= 0:
		return []

	overdue = frappe.get_all(
		"Fee Invoice",
		filters={
			"docstatus": 1,
			"status": "Overdue",
			"outstanding_amount": [">", 0],
		},
		pluck="name",
	)
	updated = []
	for name in overdue:
		exists = frappe.db.exists(
			"Fee Invoice Item",
			{"parent": name, "parenttype": "Fee Invoice", "fee_component": component},
		)
		if exists:
			continue
		try:
			doc = frappe.get_doc("Fee Invoice", name)
			doc.append(
				"items",
				{
					"fee_component": component,
					"fee_component_name": _("Late Fee"),
					"qty": 1,
					"amount": amount,
				},
			)
			doc.calculate_totals()
			doc.outstanding_amount = flt(doc.total_amount) - flt(doc.paid_amount)
			from josh_coaching.utils import save_submitted

			save_submitted(doc)
			updated.append(name)
		except Exception:  # noqa: BLE001 — log and continue with remaining invoices
			frappe.log_error(
				title=_("Late fee failed on invoice {0}").format(name),
				message=frappe.get_traceback(),
			)
	if updated:
		frappe.db.commit()
	return updated
