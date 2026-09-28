// Copyright (c) 2026, Josh Enterprises and contributors
// For license information, please see license.txt

frappe.ready(function () {
	if (frappe.session.user === "Guest") return;

	frappe.call({
		method: "josh_coaching.api.portal.get_my_dashboard",
		callback(r) {
			document.getElementById("portal-loading").style.display = "none";
			document.getElementById("portal-content").style.display = "";
			const data = r.message;
			render_students(data.students || []);
			render_sessions(data.sessions || []);
			render_invoices(data.invoices || []);
			render_qr_pass(data.students || []);
			render_makeup(data.makeup_credits || []);
			fill_feedback_form(data.students || [], data.sessions || []);
			render_progress(data.students || []);
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

	function render_makeup(credits) {
		const wrap = document.getElementById("makeup-list");
		if (!credits.length) {
			wrap.innerHTML = `<p class="text-muted">${__("No open makeup credits")}</p>`;
			return;
		}
		credits.forEach((c) => {
			wrap.appendChild(el(`
				<div class="card p-3 d-flex flex-row justify-content-between align-items-center">
					<div>
						<b>${frappe.utils.escape_html(c.student_name)}</b>
						<p class="mb-0 text-muted">${frappe.utils.escape_html(c.reason)} · expires ${c.expires_on}</p>
					</div>
					<span class="badge badge-success">${frappe.utils.escape_html(c.status)}</span>
				</div>
			`));
		});
	}

	function fill_feedback_form(students, sessions) {
		const sSel = document.getElementById("fb-student");
		students.forEach((s) => {
			const opt = document.createElement("option");
			opt.value = s.name;
			opt.textContent = s.student_name;
			sSel.appendChild(opt);
		});
		const sessSel = document.getElementById("fb-session");
		sessions.forEach((s) => {
			const opt = document.createElement("option");
			opt.value = s.name;
			opt.textContent = `${s.batch} — ${s.session_date}`;
			sessSel.appendChild(opt);
		});
		document.getElementById("fb-submit").addEventListener("click", () => {
			const result = document.getElementById("fb-result");
			frappe.call({
				method: "josh_coaching.api.portal.submit_session_feedback",
				args: {
					class_session: sessSel.value,
					student: sSel.value,
					rating: parseFloat(document.getElementById("fb-rating").value || 0),
					comments: document.getElementById("fb-comments").value,
				},
				callback() {
					result.textContent = __("Thank you for your feedback!");
					result.className = "ok";
				},
				error() {
					result.textContent = __("Could not submit feedback");
					result.className = "err";
				},
			});
		});
	}

	function render_progress(students) {
		const wrap = document.getElementById("progress-timeline");
		students.forEach((s) => {
			frappe.call({
				method: "josh_coaching.api.portal.get_progress_timeline",
				args: { student: s.name },
				callback(r) {
					const m = r.message;
					const items = [];
					(m.evaluations || []).forEach((e) =>
						items.push(`
							<div class="card p-3 mb-2">
								<b>${__("Skill Evaluation")}</b> — ${e.evaluation_date}
								<p class="mb-0 text-muted">${e.percentage}% · ${frappe.utils.escape_html(e.recommendation)}</p>
							</div>`)
					);
					(m.certificates || []).forEach((c) =>
						items.push(`
							<div class="card p-3 mb-2" style="border-left:4px solid #7B61FF;">
								<b>${__("Certificate")}</b> — ${c.issue_date}
								<p class="mb-0 text-muted">${frappe.utils.escape_html(c.certificate_type)} · ${frappe.utils.escape_html(c.level_title || "")}</p>
							</div>`)
					);
					(m.events || []).forEach((ev) =>
						items.push(`
							<div class="card p-3 mb-2" style="border-left:4px solid #ECAD4B;">
								<b>${frappe.utils.escape_html(ev.event)}</b>
								<p class="mb-0 text-muted">${frappe.utils.escape_html(ev.result)}</p>
							</div>`)
					);
					const block = el(`
						<div class="mb-4">
							<h5>${frappe.utils.escape_html(s.student_name)}</h5>
							${items.length ? items.join("") : `<p class="text-muted">${__("No milestones yet")}</p>`}
						</div>
					`);
					wrap.appendChild(block);
				},
			});
		});
	}
});
