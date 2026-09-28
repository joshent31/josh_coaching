// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.ready(function () {
	if (frappe.session.user === "Guest") return;

	frappe.call({
		method: "josh_coaching.api.portal.get_my_dashboard",
		callback(r) {
			document.getElementById("portal-loading").style.display = "none";
			document.getElementById("portal-content").style.display = "";
			render_students(r.message.students || []);
			render_sessions(r.message.sessions || []);
			render_invoices(r.message.invoices || []);
			render_qr_pass(r.message.students || []);
		},
	});

	function el(html) {
		const d = document.createElement("div");
		d.innerHTML = html.trim();
		return d.firstChild;
	}

	function render_students(students) {
		const wrap = document.getElementById("student-cards");
		students.forEach((s) => {
			wrap.appendChild(el(`
				<div class="card p-3">
					<div class="d-flex justify-content-between align-items-center">
						<h5 class="mb-0">${frappe.utils.escape_html(s.student_name)}</h5>
						<span class="badge badge-info">${s.attendance_percentage}% attendance</span>
					</div>
					${(s.enrollments || [])
						.map(
							(e) =>
								`<p class="mb-1 mt-2 text-muted">${frappe.utils.escape_html(
									e.program
								)} · ${frappe.utils.escape_html(e.batch)}</p>`
						)
						.join("")}
				</div>
			`));
		});
	}

	function render_sessions(sessions) {
		const wrap = document.getElementById("sessions-list");
		if (!sessions.length) {
			wrap.innerHTML = `<p class="text-muted">${__("No upcoming sessions")}</p>`;
			return;
		}
		sessions.forEach((s) => {
			wrap.appendChild(el(`
				<div class="card p-3 d-flex flex-row justify-content-between align-items-center">
					<div>
						<b>${frappe.utils.escape_html(s.batch)}</b>
						<p class="mb-0 text-muted">${s.session_date} · ${s.start_time} - ${s.end_time}</p>
					</div>
					<span class="badge badge-primary">${frappe.utils.escape_html(s.status)}</span>
				</div>
			`));
		});
	}

	function render_invoices(invoices) {
		const wrap = document.getElementById("invoices-list");
		if (!invoices.length) {
			wrap.innerHTML = `<p class="text-muted">${__("No invoices")}</p>`;
			return;
		}
		invoices.forEach((inv) => {
			const badge =
				inv.status === "Paid" ? "badge-paid" : inv.status === "Overdue" ? "badge-overdue" : "badge-partially";
			const payBtn =
				inv.outstanding_amount > 0
					? `<button class="btn btn-sm btn-primary pay-btn" data-invoice="${inv.name}">${__("Pay")} ${inv.currency} ${inv.outstanding_amount}</button>`
					: "";
			wrap.appendChild(el(`
				<div class="card p-3">
					<div class="d-flex justify-content-between align-items-center">
						<div>
							<b>${inv.name}</b>
							<p class="mb-0 text-muted">Due ${inv.due_date} · ${inv.currency} ${inv.outstanding_amount} outstanding</p>
						</div>
						<span class="badge ${badge}">${frappe.utils.escape_html(inv.status)}</span>
					</div>
					<div class="mt-2">${payBtn}</div>
				</div>
			`));
		});
		wrap.querySelectorAll(".pay-btn").forEach((btn) => {
			btn.addEventListener("click", () => start_payment(btn.dataset.invoice));
		});
	}

	function start_payment(invoice) {
		frappe.call({
			method: "josh_coaching.api.portal.start_payment",
			args: { invoice, gateway: "Razorpay" },
			callback(r) {
				const d = r.message;
				if (d.checkout_url) {
					window.location.href = d.checkout_url;
				} else if (d.order_id && window.Razorpay) {
					const rzp = new window.Razorpay({
						key: d.key_id,
						order_id: d.order_id,
						amount: Math.round(d.amount * 100),
						currency: d.currency,
						name: "Coaching Fees",
						description: invoice,
						handler(resp) {
							frappe.call({
								method: "josh_coaching.api.portal.confirm_payment",
								args: { data: JSON.stringify({ ...resp, gateway: "Razorpay" }) },
								callback(rr) {
									frappe.msgprint(rr.message.message);
								},
							});
						},
					});
					rzp.open();
				}
			},
		});
	}

	function render_qr_pass(students) {
		const wrap = document.getElementById("qr-pass");
		students.forEach((s) => {
			frappe.call({
				method: "josh_coaching.api.portal.get_my_qr_pass",
				args: { student: s.name },
				callback(r) {
					const block = el(`
						<div class="card p-3 text-center">
							<h5>${frappe.utils.escape_html(s.student_name)}</h5>
							<img src="${r.message.qr}" style="max-width:220px;margin:8px auto;" />
							<p class="text-muted mb-0">${__("Show this pass at the front desk")}</p>
						</div>
					`);
					wrap.appendChild(block);
				},
			});
		});
	}
});
