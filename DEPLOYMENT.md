# 🚢 Deploying josh_coaching

Production deployment guide for **josh_coaching** on Frappe v15 + ERPNext v15.
See the [README](README.md) for the full feature list; this document covers the
operational side only.

---

## 1. Server prerequisites

| Component | Version | Notes |
|---|---|---|
| OS | Ubuntu 22.04 / 24.04 LTS | Debian 12 also works |
| Python | 3.10 – 3.12 | v15 bench requirement |
| MariaDB | 10.6+ | `utf8mb4` charset, `READ COMMITTED` |
| Redis | 6.2+ | cache + queue + socketio instances |
| Node + yarn | 18 / 20 | only needed if you build assets |
| wkhtmltopdf | 0.12.6 (with patched Qt) | print formats / PDF receipts |

```bash
# example: MariaDB settings bench requires
sudo sed -i "s/character_set_client/character_set_server/g" /etc/mysql/mariadb.conf.d/50-server.cnf
# ensure my.cnf has: character-set-server=utf8mb4, collation-server=utf8mb4_unicode_ci
```

Install the bench the standard way ([frappe/bench](https://github.com/frappe/bench)):

```bash
pip install frappe-bench
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
bench setup add-domain yourdomain.com   # optional, for lets-encrypt later
```

---

## 2. Site + ERPNext

```bash
bench new-site coaching.example.com \
    --db-root-password <root-pw> \
    --admin-password <admin-pw> \
    --install-app erpnext
bench use coaching.example.com
```

`josh_coaching` requires ERPNext (`required_apps = ["frappe/erpnext"]`); the
Sales Invoice push, Item links and Customer mapping depend on it.

---

## 3. Install the app

```bash
bench get-app https://github.com/joshent31/josh_coaching.git
bench --site coaching.example.com install-app josh_coaching
bench --site coaching.example.com migrate
bench build
bench restart
```

Fixtures (roles, Fee Invoice workflow, notifications, print formats, number
cards, dashboard charts) are applied automatically during install/migrate.

Optional gateway SDKs:

```bash
bench pip install "josh_coaching[gateways]"   # razorpay + stripe
```

---

## 4. Coaching Settings checklist

Open **Coaching Settings** from the AwesomeBar and set:

### Core
- **Default Discipline / Default Currency** — used as fallbacks on new records.
- **QR Attendance Enabled** + **QR Token Validity Minutes** (default 15).
- **No-Show Grace Minutes** (default 30) for the hourly no-show job.
- **Overdue Escalation Days** (default 7).

### Billing
- **Auto Bill Days Ahead** (default 5) — recurring invoices are generated this
  many days before each enrollment's `next_billing_date`.
- **Late Fee Component + Late Fee Amount** — applied to Overdue invoices by
  the daily job. Leave empty to disable.
- **Sibling Discount Percent** (default 10) — applies when a linked sibling is
  also actively enrolled.

### Portal & Payments
- **Allow Portal Payments** — master toggle for the portal *Pay now* flow.

### Certificates / Makeup
- **Auto Issue Certificates** + pass percentage (default 75).
- **Auto Issue Makeup Credits** + validity days (default 60).

---

## 5. Payment gateways

### Razorpay

1. Dashboard → **Settings → API Keys → Generate Test/Live Key**.
2. Put **Key Id** and **Key Secret** in Coaching Settings.
3. Dashboard → **Settings → Webhooks** → add:
   - URL: `https://coaching.example.com/api/method/josh_coaching.payments.gateway_webhook`
   - Secret: same secret as in Coaching Settings.
   - Events: `payment.captured`, `order.paid`, `payment.failed`.
4. Verify with a ₹1 live/test transaction from the portal; a **Payment Gateway
   Log** entry should appear and the Fee Invoice should move to *Partially
   Paid / Paid* with an auto-generated **Fee Receipt**.

### Stripe

1. Developers → **API keys**: publishable + secret key into Coaching Settings.
2. Developers → **Webhooks** → *Add endpoint*:
   - URL: same webhook endpoint as above.
   - Events: `checkout.session.completed`, `payment_intent.payment_failed`.
3. Copy the **Signing secret** into Coaching Settings.

> The webhook endpoint is guest-accessible but signature-verified (HMAC for
> Razorpay, Stripe SDK signature check). Every callback is journalled in
> **Payment Gateway Log** — reconcile it daily against the gateways.

---

## 6. SMS / WhatsApp gateway

Outbound alerts (fee reminders, session reminders, absence alerts,
announcements) go through the generic gateway in `notifications.py`:

1. Choose a provider with a plain HTTP API (Twilio, MSG91, Gupshup, Meta
   WhatsApp Cloud API, or a local SMS box).
2. Add the endpoint + auth details to Coaching Settings (SMS/WhatsApp URL,
   headers, params template).
3. Use **Notification fixtures** (5 preloaded) or create new ones per event;
   channel can be Email, SMS, WhatsApp or a combination.
4. Test: send a fee-due notification to a test student with a real mobile
   number before going live.

---

## 7. Scheduler & workers

```bash
bench --site coaching.example.com enable-scheduler
bench setup procfile            # or configure systemd/supervisor
bench restart
```

Scheduled jobs (see `hooks.py` → `scheduler_events`):

| Cadence | Jobs |
|---|---|
| Daily | overdue escalation, auto-billing, batch expiry, birthdays, session reminders, lead/comm follow-ups, equipment overdue, makeup-credit & pack expiry, document expiry |
| Hourly | no-show marking |

Daily digest / alert emails go to users with the **Academy Manager** role.

---

## 8. QR & printing

- Student ID cards and session QR posters use the bundled print formats
  (`print_format_jinja_globals` exposes `{{ qr_image(doc) }}`).
- Print a test ID card: **Student → Print → Student ID Card**. The QR encodes
  `JC-STUDENT:<student_id>:<token>`.
- Rotate a session QR: open the Class Session → *Generate QR Token* (or call
  the portal endpoint). Posters auto-refresh each session.

---

## 9. Portal

- Portal page: `https://coaching.example.com/coaching_portal`
- Trainer check-in page: `https://coaching.example.com/coaching_checkin`
- Students sign in as **Website User** with the *Student (Portal)* role
  (auto-assigned when `student_user` is set on the Student record).

---

## 10. Production hardening

```bash
bench config dns_multitenant on
bench setup lets-encrypt coaching.example.com     # TLS
bench setup production <user>                     # nginx + supervisor
bench --site coaching.example.com set-config maintenance_mode 0
```

- **Backups**: `bench --site ... backup --with-files` via cron, or restic/S3.
  Verify a restore quarterly.
- **HTTPS only**: portal payments and webhooks must never run over plain HTTP.
- **Logs**: watch Payment Gateway Log + Error Log (frappe) for the first week.
- **Updates**:

```bash
cd frappe-bench/apps/josh_coaching && git pull origin main
bench update --patch   # or bench --site ... migrate after app pulls
bench build && bench restart
```

---

## 11. Smoke test before go-live

1. Create Discipline → Program → Batch (with schedule lines) → sessions appear.
2. Enroll a test student with a Fee Plan → run
   `bench execute josh_coaching.setup.billing.generate_recurring_invoices`
   → Fee Invoice is created, `next_billing_date` advanced.
3. Submit the invoice → take a portal payment (gateway test mode) → Fee
   Payment + Fee Receipt auto-created, invoice status updates.
4. Scan the student ID QR at `/coaching_checkin` → attendance books, session
   summary updates, pack decrements (if any).
5. Cancel an enrollment on a full batch with a waitlist → first waiter is
   auto-promoted.
6. Push one invoice to ERPNext (**Create Sales Invoice**) → customer + SI
   created and linked.

If all six pass, the deployment is functionally complete.
