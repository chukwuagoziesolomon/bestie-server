<!-- 294d224c-4a2a-49ae-8c71-e680fd32747d 76e8beef-2a15-4279-baac-4bc34a2338fb -->
# Paystack Bulk Transfer Refactor

> **Summary:**
> All payouts to vendors and couriers are now performed through Paystack single or bulk transfer API (using transfer recipients), triggered after the respective OTP codes (pickup/delivery) are validated. All logic using split payments at checkout or subaccounts for payout distribution has been fully removed. Platform commissions are retained directly; only net payouts are sent to vendors/couriers. Webhook handling now updates transfer status on a per-payout basis.

## Goals

- Remove all Paystack split payment logic from order placement and checkout (no subaccount split at payment time).
- Implement payout logic so vendors and couriers are paid exact amounts via Paystack Bulk (or single) Transfers, but only after their OTP codes are confirmed.
- Platform always receives the commission (retained on platform; only net payouts sent to vendors/couriers).
- Ensure bulk transfer status events are handled and reflected in DB.
- Clarify/rename any misleading percentage-based terms in code.
- Document the new post-checkout payout and transfer flow for developers/ops.

## Actions

1. Audit and remove all split payment usage at order payment/checkout (split in PaystackSDK, subaccount logic in transaction, etc); confirm via code search and refactor.
2. Implement payout logic via Bulk (or single) Transfer API, triggered only by vendor/courier OTP confirmation event:

- On vendor OTP completion, batch/initiate payout to vendor;
- On courier OTP completion, batch/initiate payout to courier.
- Create recipient codes as needed if missing.

3. Ensure webhook event handlers properly update status for each transfer (success/failure/reversed).
4. Audit and update code/comments for any `percentage_charge` parameters/variables/fields;
clarify as "fixed payout" where needed.
5. Document the new flow in a markdown or in-code doc for future maintainers.

## Todos
- audit-remove-split-init: Audit and remove all code performing Paystack split payment at order placement/checkout (initialize_transaction with subaccount etc)
- implement-vendor-courier-transfer: Implement vendor/courier payout using Paystack Bulk/Single Transfer API, triggered only by OTP confirmation.
- webhook-payout-updates: Update Transfer status in DB on webhook event per transfer (success/failure/reversed).
- comments-update: Update misleading percentage-based code/comments.
- payout-readme: Add code/markdown doc for the refactored payout process.

---

### To-dos legacy
- [ ] Audit all payment initialization code (vendor, courier, platform commission) to identify flat fee split usage and potential problems.
- [ ] Correct Paystack transaction initialization to always use flat amount split (set transaction_charge param and remove all percentage logic).
- [ ] Update code comments/variable terminology to clarify that percentage_charge on SubAccount stores a fixed payout, not a percentage.
- [ ] Add a code comment/short markdown doc explaining flat-amount split rationale.

---

*Note: All legacy references to split/subaccount logic and variable names are being phased out. Remember to run a database migration for the SubAccount model field change (`percentage_charge` to `fixed_payout_amount`) if not already done.*

































