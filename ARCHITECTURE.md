# Architecture

Current implementation map. Read [AGENTS.md](AGENTS.md) for agent workflows and [CONTRIBUTING.md](CONTRIBUTING.md) for mandatory change policy; those requirements do not imply legacy code already complies.

## 1) Scope and startup

This is a Python application for developers and operators demonstrating GREEN-API WhatsApp messaging, localized menus, optional OpenAI chat, and incoming/outgoing AI calls. It is not a packaged library or provider-neutral framework. Python 3.11+ is documented. `requirements.txt` is UTF-16 and pins the runtime, including API client 0.0.55, chatbot 1.3.0 and ChatGPT integration 1.0.0. Models and FSM behavior are version-sensitive dependency contracts.

`bot.py` initializes environment, logging and configuration at import time, loads `config/data.yml` relative to the working directory, constructs provider clients, registers handlers and creates the optional coordinator. Treat import as potentially network-active. The main block starts the coordinator, runs `bot.run_forever()`, and stops calls in `finally`. Run from the repository root. Missing OpenAI credentials disable chat and calls; they do not disable basic messaging. Directly invoking `create_call_coordinator` without a key raises `ValueError`.

## 2) Component ownership

| Source | Responsibility and consumers | Consequence of changes |
| --- | --- | --- |
| `bot.py` | Framework handler predicates, menu responses, startup; receives notifications | Decorator order/state predicates affect which handler consumes text |
| `internal/utils.py` | `States`, language mapping, sender activity/reset helpers | Key changes affect YAML lookup, routing and inactivity |
| `internal/envs.py` | Pydantic environment defaults and debug validation | Invalid configuration can prevent import/startup |
| `internal/config.py` | `ServerConfig`, `init_config`; env or Spring Config conversion | Field/fallback changes affect credentials, endpoints and call deadlines |
| `internal/logger.py` | Application logger setup | Logs must remain useful without exposing credentials |
| `internal/calls/integration.py` | Concrete service factory, webhook adaptation, active-call filter and chat actions | Identity/deadline conversion controls admission; filter registration affects normal menus |
| `internal/calls/coordinator.py` | Registry, queue, transition lock, worker, timers, delivery scheduling | Changes cross thread, dialog and recording lifetimes |
| `internal/calls/models.py`, `state_machine.py` | Dependency model/FSM re-exports; local `EnqueueResult` | Upgrades can change enum/transition semantics without local implementation edits |
| `internal/calls/delivery.py` | Result policy, API adapters, recording cleanup | Failure/order changes affect user-visible output and file lifetime |
| `config/data.yml` | Localized content, prompts and links | Missing keys can terminate handlers before responses |

## 3) Configuration flow

`init_envs` → `init_config` → provider constructors → handler registration. Debug defaults enabled; its validators require account fields, valid URL schemes and demo links. Non-debug uses `SpringConfigClient.get_config()` and selected environment fallbacks; it is not an offline mode. `ServerConfig` strips trailing endpoint slashes. Configuration errors propagate during setup; there is no local startup retry loop. Keep environment names, server keys and example configuration aligned. `tests/test_call_envs.py` covers call configuration validation, not live Spring availability. Moving initialization into an import helper can still trigger service access and must not be treated as harmless test setup.

## 4) Localized message flow

Entry: framework notification → `initial_handler` → sender activity/state helper → language prompt. `set_language_handler` maps choices 1–5 through `AVAILABLE_LANGUAGES`, stores language, updates `States.MENU`, and sends the localized menu image/caption. Other menu handlers invoke GREEN-API methods directly.

The framework state manager owns message state; the application owns its key names, state values and inactivity policy. Missing expected translation/state keys are logged and handlers return in relevant paths. There is no general local send retry or rollback of state after a failed send. Consequently moving a state update across a send changes what the next message does after failure. Framework persistence, receipt acknowledgment and redelivery are not established by this application.

Keep language codes, YAML keys and predicates together when changing a menu. `test_call_activity.py` covers call-related inactivity, while focused menu tests must be added for changed routes; current call tests alone do not prove language selection works.

## 5) OpenAI chat flow

Entry: `main_menu_option_14_handler` checks activity and language, rejects unavailable OpenAI with a localized error, otherwise enters `CHAT_GPT` and sends the introduction. `chat_gpt_handler` checks inactivity, resolves language and matches exit keywords by substring, case-insensitively. An exit moves to `MENU` and invokes the menu handler; other messages call `gpt_bot.process_chat_sync`.

The client uses `gpt-4o`, history limit 10 and temperature 0.7. Conversation history, response generation and provider error handling belong to `whatsapp-chatgpt-python`. There is no local history cleanup on exit and no local `None` guard in the chat handler if that state is reached outside the guarded menu. Changing substring matching to exact matching changes visible exit behavior. `test_chat_gpt_compatibility.py` bypasses the network-active parent constructor and uses mock HTTP transport to exercise the installed processing method; it proves local compatibility, not live model availability or retries.

## 6) Call admission and dialog routing

Outgoing: `main_menu_option_19_handler` → `CallCoordinator.enqueue`. Handler suffix is not a reliable user-facing menu number: inspect its regex and YAML before changing numbering.

Incoming: `incoming_call_handler` → `handle_incoming_call`. Sender must end in `@c.us` or `@lid`; call ID must be a nonempty string. Terminal statuses `declined`, `missed`, `hungUp` invoke `incoming_ended`; other non-offer statuses are ignored. Offers without timestamps or with no remaining time are rejected. Wall-clock age is converted to a monotonic deadline; chat ID falls back to sender ID and language to English. Future timestamps do not extend the configured full wait interval.

Coordinator admission preserves one registered session per sender and FIFO execution through one worker. Incoming timers expire queued offers; dequeue also checks expiry under the lock, so timer cancellation alone is not the deadline guarantee. Earlier terminal events are remembered to suppress stale offers. Sender and call ID matching prevents an old event from ending a different call. Rejection errors are logged; call execution is not automatically retried.

`register_call_filters` installs a framework filter based on registry membership. During a queued call, `0` cancels; if cancellation loses a race, the adapter re-reads status. Active calls report progress; terminal calls still delivering report processing. Removing registry membership early would allow menu routing before recording delivery finishes. Evidence: `test_incoming_calls.py`, `test_call_filter_routing.py`, `test_call_coordinator.py`; preserve malformed offers, terminal-before-offer, duplicate admission, cancellation/dequeue and deadline races.

## 7) Execution, transitions and shutdown

`start` launches the call worker. `_worker_loop` gets queued sessions; `_run_session` checks registry identity/state/stop/deadline before marking active and applying `DEQUEUED`. It runs the async dependency executor using `asyncio.run`. The dependency owns media and realtime transport; coordinator `transition` serializes FSM application. `_transition_unlocked` delegates to `CallStateMachine.apply` and logs changed transitions. Do not substitute direct state writes: invalid/repeated/terminal behavior comes from the pinned FSM and is covered in `test_call_state_machine.py`.

Executor exceptions become `INTERNAL_ERROR` and an empty result. Returning without terminal state also becomes internal error. This permits finalization rather than leaving a dialog active indefinitely. Local state is in memory and does not survive process restart.

`stop` closes admission once, sets the stop event, transitions/removes queued sessions, cancels timers, requests executor stop, rejects queued incoming calls, and sends a sentinel to wake an idle worker. It joins up to the supplied timeout. If the worker remains alive it logs a warning; delivery shutdown waits only when the worker stopped. Repeated stop returns immediately. The timeout is not proof that every task has stopped, nor a universal wall-clock bound on cleanup. Tests in coordinator/incoming suites cover queue and shutdown behavior; live transport cancellation remains external.

## 8) Result and recording delivery

`_finalize_session` clears active execution, remembers incoming identity and cancels timers. Four delivery slots feed a thread pool. When slots are full, the worker performs delivery synchronously: there can be four pool jobs plus that delivery, and new call execution waits. Submission failure also falls back synchronously. This bounds queued recording work, not the call admission queue itself.

`CallDeliveryService.deliver` suppresses shutdown output; otherwise it calls notifier before uploader. The notifier suppresses text for unanswered incoming calls; that alone does not suppress an independently present recording. Message failure skips upload because both share a try block. Both adapters close their API session in `finally` and require response code 200, dictionary data and nonempty `idMessage`. Upload uses `sendFileByUpload` with `call-recording.mp3`. There is no local retry.

Delivery logs failures and always attempts `CallExecutionResult.close()`; cleanup `OSError` is logged. `_deliver` finally removes the same session from the registry, records finish activity and releases any acquired slot. Thus dialog ownership lasts through delivery, even after terminal FSM state. Changing cleanup ownership can leak recordings; releasing the sender earlier can reorder visible conversations. Verify `test_call_delivery.py`, `test_recording_uploader.py` and coordinator cleanup/backpressure cases, including notification failure and upload failure.

## 9) Extension and compatibility boundaries

Configuration supports endpoints, credentials, links, timeouts, model/voice and localized prompts. Coordinator accepts injected executor/notifier/store/uploader; delivery defines consumer protocols. The factory still constructs concrete GREEN-API/OpenAI components and installs a global filter. Alternate providers require explicit adapter/factory work; constructor compatibility and network behavior are not guaranteed by signatures alone.

Customization order is configuration → application code → existing seam → narrow reusable option → core change → fork. This is an application customization path, not a shipped White Label platform. [MIT License](LICENCE) applies to this repository; inspect its terms, upstream licenses and provider conditions before making distribution claims. No blanket permission to redistribute modified branding is asserted here.

The READMEs contain drift: chatbot 1.1.0 versus pinned 1.3.0, missing-key startup claims versus feature disabling, and download-link wording versus current upload adapter. Source and tests govern current behavior. No CI, formatter, lint or typecheck configuration is present. See [CONTRIBUTING.md](CONTRIBUTING.md) for local commands. Provider acknowledgment, live interoperability, state-manager persistence and all external constructor effects remain unverified; unit tests do not establish them.
