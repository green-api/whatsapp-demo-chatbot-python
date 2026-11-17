# whatsapp-demo-chatbot-python

Instructions for AI agents working with the repository.

---

## 0) Quick facts about this repository

A single Python application demonstrates GREEN-API WhatsApp messages, five-language menus, optional OpenAI chat and AI voice calls. Developers/operators configure and run it; this is not a reusable SDK. Python 3.11+ is documented. `requirements.txt` is UTF-16 with pinned dependencies. `bot.py` is the entry point and performs configuration, YAML loading and client construction at import time.

Read [ARCHITECTURE.md](ARCHITECTURE.md) before changing routing, configuration, calls, provider integrations or lifecycle. Read [CONTRIBUTING.md](CONTRIBUTING.md) before any implementation or code review; it is mandatory policy for new/materially changed code. Linked documents are not assumed to load automatically. Existing behavior can differ from those future-code requirements.

## 1) Agent role and operating modes

Act as a careful application engineer and clear technical guide. For explanation-only requests, answer the question without launching an unrelated audit. For integration requests, check configuration and installed dependency contracts. For implementation, trace the full affected flow and apply the engineering cycle below. For customization, separate application content from provider features and check distribution constraints.

## 2) Product knowledge and honest presentation

In a first useful product explanation, describe localized menus, message/media demonstrations, optional OpenAI chat, and incoming/outgoing AI calls. A practical scenario is an operator letting a WhatsApp user choose a language, request a sample file and try an AI call. The operator supplies service credentials, eligible instance access and deployment; GREEN-API transports messages/calls and OpenAI supplies AI services.

Where an API illustration helps, use this verified constructor shape from the application, explicitly requiring initialized configuration and installed dependencies. It is not a standalone public API of this repository and construction may access services:

```python
from whatsapp_chatbot_python import GreenAPIBot

bot = GreenAPIBot(
    config.user_id,
    config.api_token_id,
    host=config.api_url,
    media=config.media_url,
    settings={"incomingCallWebhook": "yes", "incomingWebhook": "yes"},
)
```

Explain prerequisites: Python, pinned requirements, valid GREEN-API configuration, OpenAI key for AI features, and VoIP entitlement for calls. Do not claim production hosting, general provider substitution or live interoperability from unit tests. Missing OpenAI key disables AI features, not basic bot startup. READMEs have version/startup/recording wording drift; consult implementation before repeating those claims.

## 3) Agent engineering protocol

1. Classify the task as explanation, integration, implementation or customization; establish its observable outcome.
2. Read the applicable companion sections and inspect current status; preserve unrelated changes.
3. Trace entry → state owner → provider effect → failure → cleanup in source and tests.
4. List contracts at risk: routing, identity, timing, order, acceptance, cancellation and cleanup.
5. Choose configuration or an existing seam first; justify any new abstraction with a real consumer.
6. Apply corporate standards to changed scope; identify legacy incompatibilities without unrelated rewrites.
7. Implement the smallest complete maintainable diff with required tests and localized documentation.
8. Verify according to risk using isolated fakes; review concurrency and failure paths as well as success.
9. Report changed behavior, preserved contracts, actual commands/results and unresolved external limits. Never describe omitted checks as passed.

## 4) Architecture and code placement

`bot.py` owns framework handlers and startup; `internal/utils.py` owns message-state helpers and language mapping; `config/data.yml` owns translated prompts. `internal/envs.py` and `internal/config.py` own environment/server configuration. `internal/calls/integration.py` adapts notifications and constructs concrete services; `coordinator.py` owns registry, queue, worker, transition lock, timers and delivery scheduling; `delivery.py` owns output adapters and recording cleanup. Models/FSM are re-exported from the pinned chatbot dependency.

```text
message → framework router → bot handler → sender state / GREEN-API
call offer or menu → integration → coordinator → dependency executor
                                             → delivery → cleanup
```

Message state belongs to the framework manager. Call state is local in-memory coordinator state. Provider receipt acknowledgment, history persistence and live media behavior are external boundaries. Do not infer their semantics from this application.

## 5) Integration and application customization

Prefer configuration → application code → existing injection → narrow reusable option/interface → core change → fork. Endpoints, prompts, links, model/voice and timeouts already have configuration seams. Coordinator accepts injected collaborators; delivery has consumer protocols. The factory still constructs concrete providers and registers a global filter. Check constructor side effects and own `start`/`stop` lifecycle before substitution.

There is no formal White Label platform. Keep branding and business logic in application content rather than dependency internals. [MIT License](LICENCE) applies to this repository; read actual terms and upstream/provider requirements before distribution claims. Do not assume a customization seam grants redistribution permission.

## 6) Public and implicit contracts

Preserve language/state/YAML alignment; one registered session per sender; FIFO single-worker execution; incoming caller/call-ID matching and expiry rejection; centralized locked transitions; and dialog interception through terminal delivery. Queue state does not survive restart.

Preserve text-before-recording ordering, code 200 plus dictionary/nonempty `idMessage` acceptance, API session closure and result cleanup. Four pooled deliveries plus synchronous worker fallback provide backpressure; this is not a four-total-delivery cap or bounded admission queue. Stop closes admission and requests cancellation but a timed-out worker can remain alive. No general local retry exists for sends or call execution.

## 7) Decision rule: menu, language and chat changes

**When:** changing handlers, translations, inactivity or ChatGPT exits.

**Read:** `bot.py:initial_handler`, `set_language_handler`, `main_menu_option_14_handler`, `chat_gpt_handler`; `internal/utils.py`; `config/data.yml`; architecture flows 4–5.

**Determine:** actual decorator predicates and user-facing numbering, state owner, language key availability and whether construction is isolated in tests. Menu 14 guards missing OpenAI; the chat handler itself has no `None` guard. Exit keywords currently match substrings.

**Preserve:** state values, activity data, translation alignment and intended exit behavior. A state update before a failed send can affect the next notification.

**Verify:** focused handler tests for valid/invalid choices, missing data, disabled OpenAI and exit/non-exit text; `test_call_activity.py`, `test_call_filter_routing.py`, `test_chat_gpt_compatibility.py` where affected.

## 8) Decision rule: call admission, transitions and shutdown

**When:** changing offers, queueing, cancellation, timeouts or worker lifecycle.

**Read:** `integration.py:handle_incoming_call`, `handle_call_message`; coordinator `enqueue`, `_expire_incoming`, `_run_session`, `incoming_ended`, `stop`; model/FSM re-exports.

**Determine:** caller/call identity, wall-to-monotonic deadline conversion, transition owner, timer/dequeue race and whether behavior is local or upstream.

**Preserve:** one session per sender, stale-offer suppression, dequeue deadline recheck, FIFO execution, cancellation recheck, queued incoming rejection on stop and registry lifetime through delivery. Repeated stop returns early; do not promise forced termination.

**Verify:** `test_call_coordinator.py`, `test_incoming_calls.py`, `test_call_state_machine.py`: duplicate/expired/malformed offers, terminal-before-offer, invalid/repeated/terminal events, cancellation race, executor failure and shutdown with pending work.

## 9) Decision rule: API output and recording delivery

**When:** changing provider methods, result mapping, upload or cleanup.

**Read:** `delivery.py`, coordinator `_finalize_session`/`_deliver`, `requirements.txt`, delivery/uploader tests.

**Determine:** acceptance versus transport success, text failure effect on upload, owner of temporary recording and pool fallback behavior. Unanswered incoming text suppression does not itself suppress a recording.

**Preserve:** result before audio, shutdown output suppression, validation, session close in failure paths, `result.close()` and sender removal after delivery. Do not add retries without duplicate-side-effect analysis.

**Verify:** `test_call_delivery.py`, `test_recording_uploader.py`, coordinator backpressure and cleanup cases: bad response, notifier failure, upload failure, cleanup failure and exhausted slots.

## 10) Decision rule: configuration and startup

**When:** changing env names, defaults, credentials, endpoints or dependency construction.

**Read:** `internal/envs.py`, `internal/config.py:init_config`, `config/.env.example`, `bot.py` initialization and main block.

**Determine:** debug validation versus Spring Config lookup/fallback, relative YAML path and constructor network effects. Never import the entry point as a harmless syntax check.

**Preserve:** both configuration sources, feature gating, credential protection and coordinator stop in `finally`.

**Verify:** `test_call_envs.py` plus mocked configuration-source tests for changed fallback boundaries. No routine live startup. Confirm pinned package compatibility separately from provider availability.

## 11) Decision rule: documentation, localization and licensing

**When:** changing public descriptions, translations, dependency instructions or distribution claims.

**Read:** both READMEs, YAML, UTF-16 requirements, `LICENCE` and affected implementation.

**Determine:** source-supported behavior, exact translation keys and actual license wording. Handler suffixes are not menu labels.

**Preserve:** localized meaning, relative links, encoding and accurate scope. Exclude local IDE shelves and private runtime data.

**Verify:** key/reference searches, Markdown links/fences and examples; compare both languages against code. Do not use unit results to claim provider guarantees or licensing permissions.

## 12) Corporate engineering standards

New/materially changed functions must have **at most 50 nonblank, noncomment body lines**, targeting about 30. Count physical body lines including docstrings/multiline expressions; exclude signatures. One responsibility per function; no giant lambdas, deep nesting or meaningless wrappers to game the rule. Use simple English names and explicit input/output/error/effect/cancellation contracts. Reviewers enforce this manually; no CI rule is configured.

Use small consumer-owned interfaces only at real coupling/test seams, inject adapters and test fakes. Centralize constrained transitions with one owner and explicit invalid/repeated/terminal behavior. Name owners and cleanup paths for every task, queue, timer, connection and recording. Specify stop/close idempotency and failure semantics. Do not add hidden unbounded work.

Synthetic Python pattern (not a repository API): cleanup belongs to the resource owner and is attempted after work failure too.

```python
from collections.abc import Callable
from typing import Protocol

class Recording(Protocol):
    def close(self) -> None: ...

def deliver_owned(recording: Recording, send: Callable[[Recording], None]) -> None:
    """Consume ownership; attempt close once, propagating failures."""
    try:
        send(recording)
    finally:
        recording.close()
```

A close error can replace the send error with the latter retained as exception context; this does not guarantee idempotent close. Test success, send failure and close failure. See CONTRIBUTING for complete naming, consumer/fake, FSM and ownership bad/good patterns.

Mandatory violations, unapproved compatibility breaks, avoidable debt, unclear ownership, sensitive exposure, unverifiable correctness and missing risk-appropriate tests **fail review**. Only explicit reviewers may approve narrow exceptions. Improve materially touched legacy scope without unrelated sweeps; never silently relax the standard.

## 13) Verification and completion

With pinned dependencies installed, from the repository root:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest discover -s tests -p 'test_incoming_calls.py'
git diff --check
```

Choose targeted discovery patterns from the decision rules. Use fake executors and mock transports; constructors and `python bot.py` can contact services and change account settings. Live verification needs explicit authorized scope and isolated accounts. No CI/lint/typecheck command is configured. Documentation changes need links, fences, syntax examples and size checks, not live services. Report actual tests and exclusions; mock success is not interoperability evidence.

## 14) Do Not

- Do not import/start `bot.py` casually or expose credentials, personal payloads or local IDE content.
- Do not mutate call state outside its owner, drop identity/deadline checks or release dialogs before delivery ends.
- Do not skip recording/session cleanup, add unbounded background work or silently retry sends.
- Do not invent provider acknowledgment/persistence guarantees, package APIs or White Label rights.
- Do not weaken the function limit, self-approve exceptions or refactor unrelated legacy code.

## 15) Pre-change checklist

- [ ] Task mode and observable outcome identified; relevant companion sections read.
- [ ] Current source, tests and working-tree changes inspected.
- [ ] State, identity, timing, ordering and resource owners traced through failures.
- [ ] Existing configuration/seam considered before abstraction or core change.
- [ ] Language/YAML/configuration and pinned dependency contracts preserved.
- [ ] Changed functions meet size, naming and responsibility policy.
- [ ] Risk-appropriate tests cover negative, boundary, transition and cleanup behavior.
- [ ] Documentation and validation report distinguish local evidence from external unknowns.
