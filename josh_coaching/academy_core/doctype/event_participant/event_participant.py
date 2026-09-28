# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, today


class EventParticipant(Document):
	def validate(self):
		self._validate_capacity()

	def _validate_capacity(self):
		event = frappe.get_doc("Coaching Event", self.event)
		if event.status not in ("Open for Registration", "Ongoing", "Draft"):
			frappe.throw(_("Event {0} is not open for registration").format(self.event))
		max_p = cint(event.max_participants)
		if max_p:
			count = frappe.db.count(
				"Event Participant",
				{"event": self.event, "status": ["!=", "Cancelled"], "name": ["!=", self.name]},
			)
			if count >= max_p:
				frappe.throw(_("Event {0} is full ({1}/{2})").format(self.event, count, max_p))

	@frappe.whitelist()
	def make_entry_invoice(self) -> str:
		"""Create a Fee Invoice for the event entry fee."""
		if self.invoice:
			return self.invoice
		event = frappe.get_doc("Coaching Event", self.event)
		if not flt(event.entry_fee):
			frappe.throw(_("Event has no entry fee configured"))

		invoice = frappe.new_doc("Fee Invoice")
		invoice.student = self.student
		invoice.posting_date = today()
		invoice.due_date = today()
		invoice.currency = event.currency
		invoice.billing_period = f"Event: {event.event_name}"
		invoice.append(
			"items",
			{
				"fee_component": event.fee_component,
				"fee_component_name": _("Entry Fee: {0}").format(event.event_name),
				"qty": 1,
				"amount": event.entry_fee,
			},
		)
		invoice.insert(ignore_permissions=True)
		self.db_set("invoice", invoice.name)
		return invoice.name
