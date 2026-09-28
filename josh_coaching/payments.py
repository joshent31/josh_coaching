# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Payment gateway integration.

Supports Razorpay and Stripe out of the box (keys configured in
Coaching Settings), plus a Manual flow for cash/cheque at the desk.
Every gateway interaction is journaled into Payment Gateway Log.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_url

SUPPORTED_GATEWAYS = ("Razorpay", "Stripe", "Manual")


# ---------------------------------------------------------------------
# Public API used by the portal / desk
# ---------------------------------------------------------------------
def create_payment_order(invoice: str, gateway: str = "Razorpay") -> dict:
	"""Start a gateway payment for a Fee Invoice.

	Returns the payload the portal needs to open the checkout.
	"""
	settings = frappe.get_single("Coaching Settings")
	if not cint(settings.allow_portal_payments):
		frappe.throw(_("Portal payments are disabled in Coaching Settings"))

	doc = frappe.get_doc("Fee Invoice", invoice)
	if doc.docstatus != 1:
		frappe.throw(_("Fee Invoice {0} is not submitted").format(invoice))
	outstanding = flt(doc.total_amount) - flt(doc.paid_amount)
	if outstanding <= 0:
		frappe.throw(_("Fee Invoice {0} has no outstanding amount").format(invoice))

	log = frappe.new_doc("Payment Gateway Log")
	log.gateway = gateway
	log.invoice = doc.name
	log.student = doc.student
	log.amount = outstanding
	log.currency = doc.currency
	log.status = "Initiated"
	log.insert(ignore_permissions=True)

	if gateway == "Razorpay":
		order = _razorpay_create_order(doc, outstanding, log)
	elif gateway == "Stripe":
		order = _stripe_create_session(doc, outstanding, log)
	else:
		frappe.throw(_("Choose Razorpay or Stripe for online payments"))

	return {
		"gateway_log": log.name,
		"invoice": doc.name,
		"amount": outstanding,
		"currency": doc.currency,
		**order,
	}


def verify_and_book_payment(payload: dict) -> dict:
	"""Verify a gateway callback and book the Fee Payment.

	Razorpay: ``razorpay_order_id``/``razorpay_payment_id``/``razorpay_signature``
	Stripe:   ``gateway_log`` + ``session_id`` (verified server-side).
	"""
	gateway = payload.get("gateway") or "Razorpay"
	if gateway == "Razorpay":
		return _razorpay_verify(payload)
	if gateway == "Stripe":
		return _stripe_verify(payload)
	frappe.throw(_("Unsupported gateway {0}").format(gateway))


# ---------------------------------------------------------------------
# Razorpay
# ---------------------------------------------------------------------
def _razorpay_client():
	key_id = frappe.db.get_single_value("Coaching Settings", "razorpay_key_id")
	key_secret = frappe.db.get_single_value("Coaching Settings", "razorpay_key_secret")
	if not key_id or not key_secret:
		frappe.throw(_("Razorpay credentials are not configured in Coaching Settings"))
	try:
		import razorpay
	except ImportError:
		frappe.throw(_("Please install the 'razorpay' package on the bench"))
	return razorpay.Client(auth=(key_id, key_secret))


def _razorpay_create_order(doc, amount: float, log) -> dict:
	client = _razorpay_client()
	paise = int(flt(amount) * 100)
	order = client.order.create(
		{
			"amount": paise,
			"currency": doc.currency or "INR",
			"receipt": doc.name,
			"notes": {"student": doc.student or "", "invoice": doc.name},
		}
	)
	log.db_set(
		{
			"order_id": order["id"],
			"response_payload": json.dumps(order, default=str)[:100000],
		}
	)
	return {"order_id": order["id"], "key_id": frappe.db.get_single_value("Coaching Settings", "razorpay_key_id")}


def _razorpay_verify(payload: dict) -> dict:
	import hashlib
	import hmac

	order_id = payload.get("razorpay_order_id")
	payment_id = payload.get("razorpay_payment_id")
	signature = payload.get("razorpay_signature")
	if not (order_id and payment_id and signature):
		frappe.throw(_("Incomplete Razorpay callback"))

	secret = frappe.db.get_single_value("Coaching Settings", "razorpay_key_secret") or ""
	expected = hmac.new(
		secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
	).hexdigest()
	if not hmac.compare_digest(expected, signature):
		frappe.throw(_("Razorpay signature verification failed"))

	log_name = frappe.db.get_value("Payment Gateway Log", {"order_id": order_id})
	log = frappe.get_doc("Payment Gateway Log", log_name) if log_name else frappe.new_doc("Payment Gateway Log")
	log.gateway = "Razorpay"
	log.order_id = order_id
	log.gateway_reference = payment_id
	log.status = "Captured"
	if not log.invoice:
		log.invoice = payload.get("invoice")
	if not log.student:
		log.student = frappe.db.get_value("Fee Invoice", log.invoice, "student")
	log.response_payload = json.dumps(payload, default=str)[:100000]
	log.save(ignore_permissions=True) if log.name else log.insert(ignore_permissions=True)

	return _book_payment_from_log(log.name)


# ---------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------
def _stripe_create_session(doc, amount: float, log) -> dict:
	import stripe

	secret = frappe.db.get_single_value("Coaching Settings", "stripe_secret_key")
	if not secret:
		frappe.throw(_("Stripe secret key is not configured in Coaching Settings"))
	stripe.api_key = secret

	session = stripe.checkout.Session.create(
		mode="payment",
		success_url=get_url(f"/coaching-pay-success?invoice={doc.name}&session_id={{CHECKOUT_SESSION_ID}}"),
		cancel_url=get_url(f"/fee-invoice?name={doc.name}"),
		line_items=[
			{
				"price_data": {
					"currency": (doc.currency or "INR").lower(),
					"product_data": {"name": f"Coaching fees - {doc.name}"},
					"unit_amount": int(flt(amount) * 100),
				},
				"quantity": 1,
			}
		],
		metadata={"invoice": doc.name, "gateway_log": log.name},
	)
	log.db_set(
		{
			"order_id": session.id,
			"response_payload": json.dumps(session, default=str)[:100000],
		}
	)
	return {"checkout_url": session.url, "session_id": session.id}


def _stripe_verify(payload: dict) -> dict:
	import stripe

	secret = frappe.db.get_single_value("Coaching Settings", "stripe_secret_key")
	stripe.api_key = secret
	session_id = payload.get("session_id")
	if not session_id:
		frappe.throw(_("Missing Stripe session id"))
	session = stripe.checkout.Session.retrieve(session_id)
	if session.payment_status != "paid":
		frappe.throw(_("Stripe payment is not completed yet"))

	log_name = session.metadata.get("gateway_log") or frappe.db.get_value(
		"Payment Gateway Log", {"order_id": session_id}
	)
	log = frappe.get_doc("Payment Gateway Log", log_name)
	log.gateway = "Stripe"
	log.gateway_reference = session.payment_intent
	log.status = "Captured"
	log.response_payload = json.dumps(json.loads(str(session)), default=str)[:100000]
	log.save(ignore_permissions=True)
	return _book_payment_from_log(log.name)


# ---------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------
def _book_payment_from_log(log_name: str) -> dict:
	"""Create the Fee Payment (and receipt) from a captured gateway log."""
	log = frappe.get_doc("Payment Gateway Log", log_name)
	if log.fee_payment:
		payment = frappe.get_doc("Fee Payment", log.fee_payment)
		return {
			"status": "ok",
			"payment": payment.name,
			"receipt": payment.fee_receipt,
			"message": _("Payment already booked"),
		}

	payment = frappe.new_doc("Fee Payment")
	payment.student = log.student
	payment.invoice = log.invoice
	payment.amount = log.amount
	payment.currency = log.currency
	payment.mode_of_payment = "Online Gateway"
	payment.gateway = log.gateway
	payment.gateway_reference = log.gateway_reference
	payment.gateway_log = log.name
	payment.reference_no = log.gateway_reference
	payment.insert(ignore_permissions=True)
	payment.submit()
	log.db_set("fee_payment", payment.name)
	return {
		"status": "ok",
		"payment": payment.name,
		"receipt": payment.fee_receipt,
		"message": _("Payment received and receipt issued"),
	}


@frappe.whitelist(allow_guest=True)
def gateway_webhook(gateway: str = "Razorpay"):
	"""Webhook endpoint for gateway server-side confirmation."""
	body = frappe.request.data if frappe.request else b""
	if gateway == "Razorpay":
		secret = frappe.db.get_single_value("Coaching Settings", "razorpay_webhook_secret") or ""
		signature = frappe.get_request_header("X-Razorpay-Signature") or ""
		if secret:
			import hashlib
			import hmac

			expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
			if not hmac.compare_digest(expected, signature):
				frappe.throw(_("Webhook signature mismatch"))
	event = frappe.parse_json(body.decode() if isinstance(body, bytes) else body) or {}
	payment_entity = (event.get("payload") or {}).get("payment", {}).get("entity", {})
	order_id = payment_entity.get("order_id")
	if order_id and payment_entity.get("status") == "captured":
		log_name = frappe.db.get_value("Payment Gateway Log", {"order_id": order_id})
		if log_name:
			_book_payment_from_log(log_name)
	return {"ok": 1}
