# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import os


def get_app_path():
	return os.path.dirname(os.path.abspath(__file__))


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
