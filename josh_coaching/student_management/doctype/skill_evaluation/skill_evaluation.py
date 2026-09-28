# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class SkillEvaluation(Document):
	def validate(self):
		self.total_score = sum(flt(d.score) for d in self.criteria or [])
		self.max_score = sum(flt(d.max_score) for d in self.criteria or [])
		if self.max_score:
			self.percentage = flt(self.total_score / self.max_score * 100, 2)
		else:
			self.percentage = 0

	def on_submit(self):
		from josh_coaching.student_management.certificate import (
			maybe_issue_from_evaluation,
		)

		maybe_issue_from_evaluation(self)
