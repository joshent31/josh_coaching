# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Program(Document):
	def autoname(self):
		discipline = self.discipline or "GEN"
		abbr = "".join(w[0] for w in discipline.split()[:3]).upper()
		name = f"{abbr}-{(self.program_name or '').strip()}"
		if frappe.db.exists("Program", name):
			frappe.throw(f"Program {name} already exists")
		self.name = name
