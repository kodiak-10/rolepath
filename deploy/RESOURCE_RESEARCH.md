# Live learning-resource research

RolePath accepts roles across industries. The fixed catalogue is an optional reference collection, not the boundary of AI recommendations. Role preparation no longer receives the catalogue as a constraint.

The live workflow uses the configured Qwen Responses API with `web_search` and `web_extractor`. The model interprets the role and skill names, searches public sources, reads concrete pages, then selects relevant material. It prioritizes appropriate domestic and Chinese resources: education and industry organizations, course platforms, Bilibili and Xiaohongshu, company material, and attributed practice or interview material. It does not assign a creator or popularity bonus.

## Evidence and limits

A recommendation URL must occur in actual search output and have independently associated page content. Qwen sometimes batches extraction URLs; the adapter strictly checks its per-URL Evidence/Summary envelope and never assumes array order. Unknown formats fail explicitly. The model chooses source and paragraph IDs; displayed quotes are copied from those exact paragraphs rather than regenerated. Model-written URLs are never accepted. Search hits without readable content do not become recommendations.

Each run allows up to four completed tool calls and four selected resources. A step-limit notice is shown when the run stops at that boundary. If interrupted, token totals may be unavailable; the ledger records that fact and the completed tool count. The final selection call's usage is also recorded. A bounded search timeout ends stalled requests with an explicit error; no automatic model retries or fabricated replacement resources are used. Publication or update information is shown only when directly supported by an excerpt; dates can remain unknown.

A page excerpt does not prove teaching quality, video playback availability or full course coverage. Access restrictions may be unknown. Company-labelled question material carries a directly quoted source claim and is attributed to its author/platform, not treated as company confirmation. The operator and user should inspect original sources when necessary.

## User choice and records

Users select material to include in their study plans. Selected live resources take priority over the existing collection for matching skills. Practice materials keep their provenance and original links. Study minutes are a session budget, not asserted video length. The planner keeps its existing total-time limit.

Managed-mode results are stored in the user's `rp_ai_runs` records with task type `resources`. RLS and the server reservation/settlement flow remain in force. Failures do not debit trial credits; active members have unlimited tasks. Only the role query and skill names are sent for research; private notes and the full JD are not included.

Apply `resource_research.sql` after the ledger migrations and run `check_resource_research.sql` transactionally. Both existing and new task types keep the same ownership policies.

Provider references: [web search](https://platform.qianwenai.com/docs/developer-guides/tool-calling/web-search), [web scraping](https://platform.qianwenai.com/docs/developer-guides/tool-calling/web-scraping), [Responses API](https://platform.qianwenai.com/docs/api-reference/chat/openai-responses).
