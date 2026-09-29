# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import os

import frappe


def get_app_path():
	return os.path.dirname(os.path.abspath(__file__))


def save_submitted(doc: "frappe.Document") -> None:
	"""Persist parent + child changes to a submitted document.

	Regular ``doc.save()`` on a submitted doc raises UpdateAfterSubmitError
	unless every changed field allows on-submit updates. Our back-office
	flows (payment booking, refunds, late fees, freeze) mutate read-only
	currency/status fields and append child rows, so they bypass the
	update-after-submit validation with direct db writes.
	"""
	doc.set_parent_in_children()
	skip = {"name", "doctype", "docstatus", "modified", "modified_by", "owner", "creation", "idx"}
	meta = frappe.get_meta(doc.doctype)
	updates = {}
	for fieldname, value in doc.as_dict().items():
		if fieldname in skip or isinstance(value, (list, tuple, dict)):
			continue
		df = meta.get_field(fieldname)
		if df is None or getattr(df, "is_virtual", False):
			continue
		updates[fieldname] = value
	if updates:
		frappe.db.set_value(doc.doctype, doc.name, updates, update_modified=False)
	for row in doc.get_all_children():
		if getattr(row, "__islocal", False) or not row.name:
			row.db_insert()
		else:
			row.db_update()


def sync_workflow_status(doc, method=None):
	"""Keep workflow_state and status fields aligned after workflow transitions.

	Workflows write to ``workflow_state``; list views and reports read
	``status``. Mapping tables live in each module's controller.
	"""
	try:
		status_map = doc.STATUS_WORKFLOW_MAP  # type: ignore[attr-defined]
	except AttributeError:
		return

	new_status = status_map.get(doc.workflow_state)
	if new_status and doc.status != new_status:
		doc.db_set("status", new_status, notify=True)
