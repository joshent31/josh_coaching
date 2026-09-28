# Josh Coaching — Coaching & Training Center Suite for Frappe v15 + ERPNext v15

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](license.txt)
![Frappe](https://img.shields.io/badge/Frappe-v15%2B-blue)
![ERPNext](https://img.shields.io/badge/ERPNext-v15%2B-orange)

A single, installable **Frappe v15+ / ERPNext v15+** app that runs a coaching
or training business end-to-end — **sports academies, dance schools,
gymnastics, martial arts, aquatics, music, yoga and academic tutoring**.

It covers the full advanced methodology expected at current market standard:
students & batches, QR-code attendance, trainer/staff management, fee
collection with online payment gateways, printable receipts, and a mobile
portal for students and guardians.

---

## ✨ Features

### 👥 Students & Programs
- Student master with guardian details, photo, portal user login and printable **QR ID pass**
- Programs (Beginner → Intermediate → Advanced → Competitive) grouped by **Sports Discipline**
- Batches with weekly schedule lines, venue, capacity/seat control
- Enrollments with billing cycles (Monthly → One-Time) and seat validation
- **Skill Evaluations** — criteria-based scoring → percentage → promotion recommendation

### 📅 Scheduling & QR Attendance
- Auto-generation of **Class Sessions** from weekly batch schedules (14-day rolling window)
- **QR check-in**: rotating session QR posters + student ID card scan
- One-tap *Mark Batch Present* from the session form
- Attendance duplicate guards, live session attendance summaries
- Hourly **no-show auto-flagging** with a configurable grace window

### 🧑‍🏫 Staff
- Trainer master linked to ERPNext **Employee** (payroll-ready) with payment models (Monthly / Per Session / Hourly / Revenue Share)
- **Staff Shifts** with overlap validation and swap tracking

### 💳 Fees & Payments (market-standard)
- Fee Plans → Fee Invoices (draft → approval workflow → submit)
- **Razorpay and Stripe checkout** with server-side signature verification
- Inbound **webhooks** for gateway server-side confirmation
- Every gateway call journaled into **Payment Gateway Log**
- Automatic **Fee Receipt** on payment (printable), partial payments supported
- One-click ERPNext **Sales Invoice** realization with automatic Student→Customer mapping
- Daily overdue flagging + manager escalation notifications

### 📱 Mobile / Portal
- Responsive portal page **`/coaching_portal`** — dashboard, upcoming sessions,
  invoices, **pay online**, personal QR pass (mobile-screen friendly)
- Trainer check-in page **`/coaching_checkin`** — scan payloads, session QR poster,
  rotate tokens

### 📊 Dashboard & Reports
- Public workspace with number cards (Active Students, Sessions Today,
  Outstanding Fees, Collections this month) and dashboard charts
- Reports:

| Report | What it shows |
|---|---|
| Batch Attendance Register | Day-wise attendance per batch, check-in time & method |
| Attendance Percentage | Present/absent/late % per student per batch |
| Student Outstanding Fees | Unpaid/overdue invoices with days overdue |
| Student Progress Report | Skill evaluation scores and recommendations |
| Today's Sessions | Today's timetable with trainer, venue, attendance summary |
| Fee Collection Summary | Collections grouped by payment mode, gateway split |

---

## 🧩 DocType Map

```
Academy Core        Coaching Settings (singleton) · Sports Discipline · Coaching Center
Student Management  Student · Program · Batch · Enrollment · Student Attendance
                    Skill Evaluation (+ Skill Evaluation Line)
Scheduling          Class Session · Batch Schedule Line
Staff Management    Coach (Trainer) · Staff Shift
Fees Management     Fee Plan (+ Component) · Fee Component · Fee Invoice (+ Item)
                    Fee Payment · Fee Receipt · Payment Gateway Log
```

## 🚀 Install

Requires a **Frappe v15+ bench** with **ERPNext v15+** installed on the site.

```bash
cd frappe-bench
bench get-app https://github.com/joshent31/josh_coaching.git
bench --site your-site.local install-app josh_coaching
bench --site your-site.local migrate
bench restart
```

Optional Python deps for full functionality (install into the bench env):

```bash
# QR code generation (required for QR passes / posters)
bench pip install "qrcode[pil]"
# Gateway SDKs (only if using those gateways)
bench pip install razorpay stripe
```

## ⚙️ After install

1. **Roles** — fixtures create `Academy Manager`, `Academy User`, `Trainer`,
   `Student (Portal)`. Assign them to your users (System Manager sees everything).
2. **Coaching Settings** — open from the AwesomeBar: default discipline & venue,
   QR validity minutes, no-show grace, portal payments toggle, gateway keys,
   overdue escalation days, late-fee component.
3. **Masters** — Sports Disciplines → Programs → Batches (add weekly schedule
   lines) → Fee Plans (components + amounts).
4. **Portal user** — set `student_user` on a Student; the guardian gets a
   Website User account and portal access.
5. **Scheduler** — `bench --site your-site.local enable-scheduler` so session
   generation, reminders, no-show marking and overdue escalation run.
6. **Webhooks** — point Razorpay/Stripe webhooks at:
   `/api/method/josh_coaching.payments.gateway_webhook`

## 🔌 API Endpoints (whitelisted)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `josh_coaching.api.portal.get_my_dashboard` | Mobile dashboard payload (students, sessions, invoices) |
| `POST` | `josh_coaching.api.portal.get_my_qr_pass` | Student QR pass (base64 data URL) |
| `POST` | `josh_coaching.api.portal.scan_and_checkin` | QR check-in booking |
| `POST` | `josh_coaching.api.portal.get_session_qr` | Rotating session QR poster |
| `POST` | `josh_coaching.api.portal.start_payment` | Create gateway order (Razorpay/Stripe) |
| `POST` | `josh_coaching.api.portal.confirm_payment` | Verify callback → book payment + receipt |
| `POST` | `josh_coaching.api.portal.invoice_to_sales_invoice` | Push fee invoice to ERPNext Sales Invoice |
| `POST` | `josh_coaching.payments.gateway_webhook` | Gateway webhook (guest, signature-verified) |

## 🔄 Daily operations flow

1. Create a **Batch** with weekly schedule lines → sessions auto-generate for
   the next 14 days (or run `josh_coaching.setup.batches.generate_sessions_for_batch`).
2. Trainer opens **`/coaching_checkin`**, shows the session QR poster; students
   scan their ID QR — attendance books itself with check-in time & method.
3. **Fees** flow from Enrollment (Fee Plan + billing cycle); invoices pass the
   approval workflow and are submitted.
4. Guardians **pay from the portal** → gateway verifies → Fee Payment +
   receipt are booked automatically → optional ERPNext Sales Invoice realizes revenue.
5. Daily jobs flag **overdue** invoices and escalate to managers;
   hourly jobs mark **no-shows**.

## 🛠️ Development

```bash
# lint + checks
pip install ruff
ruff check .
python -m compileall -q josh_coaching

# run tests (on a bench with the app installed)
bench --site your-site.local run-tests --app josh_coaching
```

## 📄 License

MIT — see [license.txt](license.txt).
