# Managed AI deployment

RolePath can reserve one credit for an AI task on the server, store the validated
result with its usage record, and return the credit when generation or validation
fails. A verified Supabase user receives one credit on the first reservation.
New self-hosted deployments default to BYOK until the operator explicitly switches modes.
The RolePath hosted deployment has been configured for managed mode and restarted.
Its ledger passed nine database assertions with rolled-back synthetic fixtures.
The signed-in browser trial verified the first credit, a successful synthetic JD,
a zero balance, blocked repeat use, saved result history, and login restoration
after refresh. Payment collection is disabled.

## Before enabling

1. Back up the database and apply `managed_ai.sql` once after the existing schema. It adds credit objects
   without replacing existing policies; rerunning an existing migration fails rather
   than silently replacing its access rules.
2. Apply `account_entitlements.sql` after `managed_ai.sql`. It adds server-controlled unlimited entitlements and a per-run charged flag. Assign entitlements only to a verified account using a private operator query; never store operator email addresses or account IDs in the public repository. Ordinary users have read-only access to their own entitlement. Unlimited tasks are logged but do not deduct credits, trigger hourly/daily quotas or add credits when they fail. Existing charged reservations still refund correctly after an entitlement change.
Run `check_account_entitlements.sql` after the entitlement migration to verify unlimited access, ordinary-account charging, refunds across entitlement changes and restricted mutation permissions. Its synthetic rows are rolled back.

3. Run [the transactional ledger checks](check_managed_ai.sql) in the SQL editor.
   Its synthetic identities and ledger rows are rolled back after the checks.
   Also verify the browser flow with two real test identities: each can read only its own
   wallet/results, neither can modify a balance or invoke accounting functions.
   Concurrent reservations must allow only one pending operation per account.
3. Add the following to **Streamlit Secrets**, not the GitHub repository:

```toml
ROLEPATH_AI_MODE = "managed"
LLM_BASE_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
LLM_MODEL = "qwen3.7-plus"
LLM_API_KEY = "YOUR_SERVER_KEY"
LLM_ENABLE_THINKING = "false"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVER_ONLY_SERVICE_ROLE_KEY"
AI_DAILY_REQUEST_LIMIT = "50"
```

The service role key is privileged: it is used only in server-side accounting.
All ordinary document and learning-data access continues to use the user's JWT.
Never put this key in public_config.json or a browser component.

4. Run public/synthetic JD and note fixtures against Qwen. Measure input/output
   tokens, latency, validation failures and retry costs. Do not use private notes
   for a benchmark without specific permission. Two synthetic live tasks (JD extraction and note assistance) passed with
   `qwen3.7-plus` on Qianwen AI Platform. They consumed 812 input and 673 output
   tokens in total; this small functional check is not a pricing benchmark.
   **The approved monthly price is CNY 12.90 with unlimited AI tasks; this is not a measured cost guarantee**.
5. Check the English and Chinese UI and an end-to-end free trial before activation.

## Semantics and limits

- One verified **account**, not one proven human, receives a free credit.
- Without an active membership, each AI JD analysis, note instruction or document answer uses one trial credit. Active monthly members have unlimited tasks until expiry.
- User input is bounded. The model adapter rejects combined prompts exceeding
  50,000 characters, and existing task-specific limits remain in force.
- Successful results and reported provider token usage are stored per user.
  Failed validation preserves provider usage but refunds the user's credit.
- Pending reservations prevent concurrent requests per user. Ordinary accounts have
  at most five new attempts/hour; the global daily request cap includes their failures. Active monthly members and permanent unlimited accounts do not consume those quotas.
  This is a request cap, **not a measured yuan spending limit**.
- If the server crashes or settlement is uncertain, the reservation stays pending.
  Do not blindly retry generation or refund it: first inspect the run and provider
  logs, then settle/refund using the server-only function. Automatic crash
  reconciliation is not implemented. This is an activation limitation.
- Replayed settlement is idempotent. Saved results can be downloaded from Usage.
- Account deletion also deletes its ledger. This trial model is not sufficient
  protection against deliberate multi-account abuse; a global cap limits exposure.

## Monthly access and manual WeChat collection

Apply `memberships.sql` after the existing ledger migrations. A personal QR code has no payment callback. Users submit payment details and an explicitly authorized reviewer confirms the actual CNY 12.90 receipt in WeChat. The database then grants one calendar month of unlimited access. Repeated approval is idempotent; renewals extend the current expiry. There is no automatic renewal.

The reviewer registry is separate from unlimited AI access. Ordinary accounts cannot read it, review orders, edit prices or change membership expiry. Order visibility is limited to its owner. The server verifies the logged-in reviewer before using service-role RPCs. Run `check_memberships.sql`; all synthetic fixtures roll back. See [membership operations](MEMBERSHIPS.md).

## Verified provider configuration

The Qianwen AI Platform pay-as-you-go endpoint is
`https://maas.qianwenaiapi.com/compatible-mode/v1`. Its API keys and endpoints
must stay paired; do not substitute a DashScope URL for a Qianwen Platform key.

Sources: [Qianwen Platform API key guide](https://platform.qianwenai.com/docs/api-reference/preparation/api-key)
and [Qwen Code authentication guide](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/).
The application accepts this exact host in addition to the existing Bailian hosts.
