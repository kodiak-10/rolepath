<div align="center">

# RolePath

### From career curiosity to a clear next step.

An AI-assisted career exploration and learning workspace for students preparing for their first internship.

**Understand the role · Find relevant resources · Build a plan · Learn with evidence**

[Launch RolePath](https://rolepath-kodiak.streamlit.app/) · [简体中文](README.zh-CN.md) · [Capabilities](#product-capabilities) · [Architecture](#architecture) · [Deployment](#deployment)

**Status:** actively developed MVP · **Interface:** English / 简体中文 · **AI access:** bring your own API key

</div>

---

## Overview

A job description tells a student what an employer expects. It rarely explains where to begin, which learning resources are relevant, or what a useful first project should demonstrate.

RolePath connects those steps in one workspace. Users can explore example roles, analyze a real job description, review source-linked courses and practice material, create a time-budgeted learning plan, and keep notes and progress records. A note assistant accepts natural-language instructions to summarize, explain, compare or ask questions about selected learning materials.

The product is designed primarily for first-time internship applicants and first- and second-year university students. Its intended scope spans job families rather than a single employer or specialist role. The current resource catalog is finite: accepting a job description does **not** mean every requirement has a matching course.

RolePath separates three things that are easy to confuse: **what a role asks for, what a learner has evidence of, and what the learner has marked complete.** A checked task is a progress record, not a certification of competence.

## The learning journey

| Stage | User action | Result |
| --- | --- | --- |
| Explore | Review example roles or bring a real vacancy | A starting direction grounded in actual work |
| Understand | Paste or upload the job description | Requirements with source evidence and eligibility constraints |
| Find resources | Review matched lessons and practice sources | Relevant material, provenance and visible coverage gaps |
| Plan | Describe prior experience and choose a time budget | A saved sequence of learning, review and practice tasks |
| Learn | Complete tasks, record study time and upload notes | Check-ins, reflections and accumulated learning material |
| Reflect | Give the note assistant a specific instruction | A saved response linked to the selected source passages |
| Return | Search saved history and reopen a plan | Continuity across learning sessions within the same account |

## Product capabilities

### Job analysis with traceable evidence

Users can paste a job description or upload a supported document or image. AI-assisted extraction identifies explicit requirements and connects them to the source text. The interface separates skill requirements from conditions such as education or internship availability, and supports manual additions grounded in an exact source excerpt.

Without an API key, a limited keyword scan is available. It is explicitly presented as an incomplete first pass, not a substitute for semantic analysis. The three home-page role examples are demonstrations, not live recruitment listings.

### Courses and practice with identifiable sources

Course matching uses the requirements extracted from the job description and the metadata of resources already in the catalog. Where available, recommendations point to specific chapters and provide creator, publication, study-time and verification information.

Bilibili can be preferred when relevance is equal. Creators do not receive a universal ranking bonus. Practice materials distinguish original question sources, public interview recollections and learning exercises. An interview recollection is not represented as an official or current company exam.

The catalog is not a live search engine. Missing matches are shown as gaps; the planner does not invent course URLs to fill them. Catalog and provenance checks also do not imply that every lesson has received an independent quality review.

### Learning plans constrained by available time

Users provide weekly study hours, a preparation period and optional evidence of prior work. The planner orders requirements, selects available learning material and allocates tasks across days within the total time budget. Longer tasks can span multiple daily sessions.

The current scheduling logic is rule-based. It uses self-reported experience and mentions in submitted material as evidence indicators, without treating either as proof of mastery. Plans show scheduled work, missing resources and skills that do not fit the available budget.

### Notes as an interactive learning workspace

Users can select one or several saved notes and ask the assistant to:

- Summarize a topic or compare multiple notes.
- Explain an unfamiliar concept in simpler language.
- Generate clearly labeled practice questions from the material.
- Review an interpretation and identify points that need checking.
- Ask a follow-up question when the available material is insufficient.

Responses use references to supplied passages. The application validates reference identifiers and attaches the corresponding original text; it rejects invalid structured output rather than saving it as a verified result. This validates citation structure, **not the factual correctness of every model interpretation**.

Documents and images are converted to text before analysis. The current assistant does not directly interpret the original images. Handwriting, formulas and diagrams therefore require particular care. A separate **Ask materials** page retrieves relevant passages for focused questions.

### Personal history and bilingual presentation

Saved plans, check-ins, note text and accepted note analyses are available through the user's account. The History page supports searching and resuming a selected plan. Unsaved drafts, standalone job analyses and a complete persistent chat transcript are not automatically included in history.

The interface opens in English and provides a **Language / 语言** selector for Simplified Chinese. Language switching preserves the current page and inputs. Original job descriptions, notes, course titles and quotations retain their source language. AI responses are not automatically translated merely because the interface language changes.

## What the AI does—and what the application does

| Responsibility | Current implementation |
| --- | --- |
| Interpret explicit job requirements | LLM extraction with source-reference validation; limited keyword mode without AI |
| Explain and organize selected notes | Instruction-driven LLM responses grounded in supplied text |
| Answer questions about documents | Passage retrieval followed by an optional LLM answer |
| Select courses and practice | Catalog matching and relevance rules |
| Allocate study time | Deterministic scheduling within a user-defined budget |
| Store progress and enforce ownership | Application storage and database access policies |
| Verify proficiency or automatically replan | Not implemented |

This division keeps model-generated interpretation separate from storage, resource provenance and scheduling. The current release is an assisted learning workflow; it is not an autonomous career adviser that can verify skills or guarantee hiring outcomes.

## Architecture

```text
Streamlit workspace
  ├── English / Chinese presentation
  ├── Email-code sign-in → Supabase Auth
  ├── Job analysis → keyword parser / user-configured LLM
  ├── Resource catalog → matching → time-budgeted planner
  ├── Document ingestion → text extraction / OCR → passage retrieval
  └── Note assistant → source-reference validation → saved report

Persistence
  ├── Local personal use: SQLite
  └── Hosted multi-user use: Supabase + row-level access policies
```

| Layer | Main components |
| --- | --- |
| Interface | Streamlit, custom CSS, explicit translation catalog |
| Model integration | OpenAI-compatible client for supported Alibaba Cloud Model Studio endpoints |
| Retrieval | Keyword retrieval; optional BGE / Chroma integration in the codebase |
| Documents | PDF text extraction and image OCR |
| Image processing | macOS Vision locally; Tesseract with Chinese / English language packages on Linux |
| Authentication | Supabase email OTP and server-side session verification |
| Storage | SQLite locally; authenticated Supabase storage for the hosted application |

The base dependency file covers the standard keyword-retrieval path. Optional dense retrieval requires its additional packages and model assets; it is not a prerequisite for the default experience.

## Data, accounts and AI credentials

Cloud mode requires authentication before private workspace data is loaded. The Supabase schema uses user ownership and row-level access policies. Application-level filtering is not a replacement for those policies, and a new deployment should verify isolation with two separate accounts.

The browser can retain Supabase session credentials for up to seven days. Restored sessions are verified on the server. Browser storage restrictions, private browsing and different browsers can affect continuity; credentials are not shared across browsers or devices.

AI access follows a **bring-your-own-key** model:

- Each user supplies their own supported Model Studio endpoint, API key and model name.
- API usage is charged to that user's provider account.
- The key remains in the current application session; it is not written to the application database or browser's persistent session storage.
- A new session may require entering the key again.
- When an AI operation is requested, the relevant selected text and context are sent to the configured provider.

Do not commit `.env`, session tokens, private keys, local databases or personal documents. A Supabase publishable/anon key is used with authentication and access policies; an administrator or service-role key must not be used in the visitor client. This repository does not claim an independent security audit.

## Run locally

Use a Python environment compatible with the pinned dependency ranges. Local development has been exercised with Python 3.13.

```bash
git clone https://github.com/kodiak-10/rolepath.git
cd rolepath
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The local entry point stores records in `.rolepath.sqlite3` in the working directory and is intended for personal use. It does not provide cloud account isolation.

For optional local AI access, create an untracked `.env` file:

```dotenv
LLM_API_KEY=your-own-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_ENABLE_THINKING=false
```

Use an endpoint and model available to your own provider account. These example values do not provision a model or supply credits. On macOS, image OCR requires the Swift / Vision runtime; on Linux, install the system OCR packages listed in `packages.txt`.

## Deployment

The hosted entry point is **`cloud_app.py`**, which enables cloud mode before loading the application.

1. Create a Supabase project for your deployment and apply [`deploy/supabase.sql`](deploy/supabase.sql).
2. Replace the project URL and publishable/anon key in `deploy/public_config.json` with your project's public configuration. Do not reuse another deployment's backend.
3. Configure email delivery and the email OTP template in Supabase. The email must include the numeric token (`{{ .Token }}`) used by the application's verification form. Set the appropriate site URL.
4. Deploy the repository to Streamlit Community Cloud with `cloud_app.py` as the entry point. Keep `requirements.txt` and `packages.txt` available at the repository root.
5. Verify email-code delivery, sign-in, sign-out, session restoration, two-account data isolation and saved-history access before inviting users.
6. Users connect their own AI service from **Account & settings → AI settings**. Local `.env` credentials are not automatically shared with hosted users.

Free hosting does not make model usage free, and hosting availability should not be treated as a production service guarantee.

## Repository guide

| Path | Purpose |
| --- | --- |
| `app.py` / `cloud_app.py` | Personal and authenticated cloud entry points |
| `rolepath/ui.py`, `i18n.py`, `translations.json` | Workspace presentation and interface languages |
| `rolepath/cloud_auth.py`, `browser_session.py` | Email sign-in and browser session restoration |
| `rolepath/cloud_store.py`, `db.py` | Hosted and local persistence |
| `rolepath/jd.py`, `llm.py`, `evidence.py` | Requirement extraction, model requests and evidence indicators |
| `rolepath/matching.py`, `planner.py` | Resource selection and daily task allocation |
| `rolepath/knowledge.py`, `image_text.py` | Ingestion, passage retrieval and OCR |
| `rolepath/notes.py`, `notes_ui.py` | Instruction-driven note analysis and saved reports |
| `data/` | Role examples, course metadata and practice sources |
| `deploy/` | Database schema and public backend configuration |

## Current limitations and development direction

RolePath is an actively developed MVP. The following are deliberate boundaries of the current implementation, not completed capabilities:

- Resource coverage is limited and requires continued editorial work across job families.
- Source-reference checks cannot eliminate unsupported model interpretations or OCR errors.
- Course matching and planning are not yet an adaptive LLM-driven learning policy.
- Check-ins and completion are self-reported; automated assessment of code, answers or portfolio work is not available.
- The note assistant has bounded input and conversation lengths. Larger collections require smaller selections.
- English interface support does not translate the underlying Chinese catalog or all model outputs.
- Actual mobile and embedded-browser behavior needs deployment-specific verification.

Future work should strengthen resource quality, evidence-based feedback and learning continuity before expanding claims about automation. Neither career suitability nor interview readiness should be inferred from task completion alone.

## Feedback

Use the repository's [Issues](https://github.com/kodiak-10/rolepath/issues) to report a reproducible problem or a resource mismatch. Include the affected page, expected behavior and a sanitized example. Never include API keys, verification codes, session tokens or private notes.

---

<div align="center">

**RolePath** — Understand the work. Build the evidence. Take the next step.

[Open the workspace](https://rolepath-kodiak.streamlit.app/) · [阅读中文版](README.zh-CN.md)

</div>
