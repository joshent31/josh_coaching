// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

// Form-side UX helpers bundled with the app.

frappe.ui.form.on("Class Session", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("QR Poster"), function () {
			frappe.call({
				method: "josh_coaching.api.portal.get_session_qr",
				args: { session: frm.doc.name },
				callback(r) {
					const d = new frappe.ui.Dialog({
						title: __("Session Check-in QR"),
						size: "small",
					});
					d.$body.html(`<div class="text-center"><img src="${r.message.qr}" style="max-width:260px;" /></div>`);
					d.show();
				},
			});
		});
		frm.add_custom_button(__("Mark Batch Present"), function () {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Enrollment",
					filters: { batch: frm.doc.batch, status: "Active", docstatus: 0 },
					fields: ["student", "student_name"],
					limit_page_length: 0,
				},
				callback(r) {
					(r.message || []).forEach((row) => {
						frappe.call({
							method: "frappe.client.insert",
							args: {
								doc: JSON.stringify({
									doctype: "Student Attendance",
									student: row.student,
									class_session: frm.doc.name,
									attendance_date: frm.doc.session_date,
									present: "Present",
									checkin_method: "Manual",
								}),
							},
							error() {
								// duplicate or validation error — skip silently
							},
						});
					});
					frappe.show_alert({ message: __("Marked batch present"), indicator: "green" });
				},
			});
		});
	},
});

frappe.ui.form.on("Student", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("QR Pass"), function () {
			frappe.call({
				method: "josh_coaching.api.portal.get_my_qr_pass",
				args: { student: frm.doc.name },
				callback(r) {
					const d = new frappe.ui.Dialog({
						title: __("Student QR Pass"),
						size: "small",
					});
					d.$body.html(`<div class="text-center"><img src="${r.message.qr}" style="max-width:240px;" /></div>`);
					d.show();
				},
			});
		});
	},
});

frappe.ui.form.on("Fee Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0 && !frm.doc.sales_invoice) {
			frm.add_custom_button(__("Create Sales Invoice"), function () {
				frappe.call({
					method: "josh_coaching.api.portal.invoice_to_sales_invoice",
					args: { invoice: frm.doc.name },
					callback(r) {
						frappe.show_alert({
							message: __("Sales Invoice {0} created", [r.message.name]),
							indicator: "green",
						});
					},
				});
			});
		}
	},
});
