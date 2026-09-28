# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, today


class Certificate(Document):
	pass


def maybe_issue_from_evaluation(evaluation) -> str | None:
	"""Auto-issue a certificate when a submitted evaluation clears the pass bar."""
	if not cint(frappe.db.get_single_value("Coaching Settings", "auto_issue_certificates")):
		return None
	pass_pct = flt(frappe.db.get_single_value("Coaching Settings", "certificate_pass_percentage") or 75)
	if flt(evaluation.percentage) < pass_pct:
		return None
	if frappe.db.exists("Certificate", {"evaluation": evaluation.name}):
		return None

	cert = frappe.new_doc("Certificate")
	cert.student = evaluation.student
	cert.program = evaluation.program
	cert.evaluation = evaluation.name
	cert.certificate_type = "Level Completion"
	cert.level_title = _program_level(evaluation.program)
	cert.issue_date = today()
	cert.signed_by = evaluation.evaluator
	cert.remarks = _("Scored {0}% in skill evaluation").format(evaluation.percentage)
	cert.insert(ignore_permissions=True)
	return cert.name


def _program_level(program: str) -> str | None:
	return frappe.db.get_value("Program", program, "level")
