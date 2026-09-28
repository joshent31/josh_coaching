# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Single daily / hourly scheduler entry dispatching each area's job."""


def daily():
	from josh_coaching.fees_management.fee_invoice import daily_overdue_escalation
	from josh_coaching.setup import batches, sessions

	daily_overdue_escalation()
	batches.close_expired_batches()
	batches.notify_upcoming_birthdays()
	sessions.send_session_reminders()


def hourly():
	from josh_coaching.setup.sessions import auto_mark_noshow

	auto_mark_noshow()
