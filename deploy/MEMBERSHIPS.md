# RolePath Plus

RolePath Plus costs CNY 12.90 per calendar month with unlimited AI tasks. Membership starts when an authorized reviewer confirms the actual WeChat receipt. Renewals extend the existing expiry. Calendar-month arithmetic uses Asia/Shanghai, including month-end clamping. There are no automatic charges or renewals. Existing saved learning records remain available after expiry.

## Manual collection

The personal QR code cannot report payment status to RolePath. A user creates an order, pays CNY 12.90 in WeChat with the order number as a note, then submits the payment time and a note or transaction suffix. This submission never activates access. The designated reviewer checks the actual WeChat receipt and confirms the exact amount. Repeated approval does not extend access twice. Support: xxxnew1168@yeah.net.

## Deployment

Apply `memberships.sql` after `managed_ai.sql` and `account_entitlements.sql`. Run `check_memberships.sql` transactionally; all fixtures roll back. Designate the verified operator separately in `rp_membership_admins`. Never embed operator identifiers, service keys or user records in the repository.

Keep `deploy/membership.json` `sales_enabled` false until the database, review access and UI checks pass. The service role stays on the server. User clients may only read their own orders and call the create/submit RPCs. Order prices, reviews and membership expiry are database-controlled; RLS and grants prevent client edits.

Active members and permanent operator accounts are not subject to per-credit, free-trial hourly or free-trial daily caps. Only one AI task may run per account at a time. AI task failures do not debit trial credits. Payment review cannot read user notes or learning materials; it only exposes order information and the applicant email to the designated reviewer.
