# Contributing

Mandatory policy for humans and AI agents. [AGENTS.md](AGENTS.md) supplies operating instructions; [ARCHITECTURE.md](ARCHITECTURE.md) describes existing behavior. These standards apply to new and materially changed code, not a claim that all legacy code complies.

## 1) Goal and workflow

Deliver the smallest complete, safe, maintainable change, including necessary tests and documentation. Reuse configuration, standard library, current dependencies and existing seams first.

1. Define the user-visible result, affected paths and compatibility boundary.
2. Read the relevant architecture flow and existing tests; trace callers through failures and cleanup.
3. Identify state, resource and cancellation owners before choosing an implementation.
4. Prefer the existing extension level; justify any new interface with a real consumer or testing need.
5. Implement a focused diff. Improve materially touched legacy functions to policy without unrelated sweeps.
6. Verify positive, negative and boundary behavior plus transition, cancellation and cleanup cases where relevant.
7. Review source, examples, translations and dependency contracts together; report exact checks and remaining limits.

## 2) Function size, naming and contracts

**New and materially changed functions must have at most 50 nonblank, noncomment body lines; target about 30.** Count physical body lines, including docstrings and multiline expressions; exclude the signature, blank lines and comment-only lines. No configured linter currently enforces this; reviewers must inspect it. Giant lambdas, deep nesting and meaningless forwarding wrappers do not satisfy decomposition. Every function needs one concrete responsibility. A newcomer should understand inputs, effects, output, errors, state and ownership within roughly five minutes.

Use plain English, concrete domain names and Python `snake_case`. Boolean predicates use `has_`/`is_`; error-raising checks use `validate_`. Signatures, types and documentation expose exceptions, side effects and cancellation. Comments explain reasons. Do not rename an external API just for style. Exceptions to mandatory rules require explicit reviewer approval with narrow scope and rationale; agents cannot approve their own exceptions.

### Synthetic example: validation and naming

Bad — conflates validation and I/O and hides failure behind a boolean-looking name:

```python
def is_ok(value, api):
    if value and value.strip():
        api.send(value)
    else:
        raise ValueError("bad")
```

Good — standalone application example, not a repository API:

```python
from collections.abc import Callable

def validate_chat_id(chat_id: str) -> None:
    """Raise ValueError before any send when the destination is blank."""
    if not chat_id.strip():
        raise ValueError("chat_id must not be blank")

def send_notice(chat_id: str, send: Callable[[str, str], None]) -> None:
    """Send once; validation and sender exceptions propagate."""
    validate_chat_id(chat_id)
    send(chat_id, "Your call is queued")
```

Why: callers can distinguish invalid input from transport failure; validation is independently testable. Tests: valid destination sends once, empty/whitespace destinations send zero times, sender failure propagates. Review: reject vague names, hidden retries or validation after a side effect. Real provider address validation must follow the integration contract, not this simplified blank check.

## 3) Dependency direction and injection

High-level orchestration must not know unnecessary provider payload, transport or storage details. Put small contracts near consumers at actual seams; inject concrete adapters and test a fake. Keep fixed local details concrete. Do not add interfaces for every class, speculative factories or layers without consumers. Delivery protocols in `internal/calls/delivery.py` are an existing seam; dependency FSM/model re-exports are not local implementations to rewrite casually.

### Synthetic example: consumer contract and fake

Bad — policy constructs provider transport:

```python
def announce(api_factory, chat_id):
    api_factory().sending.sendMessage(chat_id, "Ready")
```

Good — standalone example; production adapters must own their client cleanup:

```python
from typing import Protocol

class TextSender(Protocol):
    def send(self, chat_id: str, text: str) -> None:
        """Return on acceptance; raise on failure."""
        ...

class ReadyNotice:
    def __init__(self, sender: TextSender) -> None:
        self._sender = sender

    def announce(self, chat_id: str) -> None:
        self._sender.send(chat_id, "Ready")

class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, chat_id: str, text: str) -> None:
        self.sent.append((chat_id, text))

fake = FakeSender()
ReadyNotice(fake).announce("demo")
assert fake.sent == [("demo", "Ready")]
```

Why: policy needs accepted text delivery, not SDK internals. Tests: exact destination/text once; failing fake propagates; adapter rejects missing acceptance ID and closes on exceptions. Review: reject provider construction in orchestration, silent acceptance failure or an interface with no real consumer. This synchronous example promises no cancellation; do not invent it in an adapter contract.

## 4) Explicit state discipline

For correctness dependent on allowed states/events, require a centralized FSM or equivalent explicit transition model, one mutation owner and documented invalid, repeated and terminal semantics. Separate planning from I/O where feasible. Do not impose FSMs on trivial flags. In calls, preserve coordinator locking and dependency `CallStateMachine` behavior; intentional migration requires transition tests.

### Synthetic example: transition planning

Bad — callers can resurrect terminal work:

```python
def start(session):
    session.state = "running"
```

Good — pure planner; a real concurrent owner must apply it under its lock:

```python
from enum import Enum

class Stage(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"

def next_stage(stage: Stage, event: str) -> Stage:
    """Repeated finish is idempotent; every other invalid pair raises."""
    transitions = {
        (Stage.QUEUED, "start"): Stage.RUNNING,
        (Stage.RUNNING, "finish"): Stage.DONE,
        (Stage.DONE, "finish"): Stage.DONE,
    }
    try:
        return transitions[stage, event]
    except KeyError as error:
        raise ValueError("invalid stage/event pair") from error
```

Why: allowed and repeated behavior can be reviewed independently of I/O. This is illustrative, not the upstream call transition table. Tests: every allowed edge, repeated finish, repeated start, finish while queued, start after done and unknown event; assert rejected events do not mutate owner state. Review: reject scattered state writes or terminal resurrection, and require race coverage if ownership crosses threads.

## 5) Ownership and cancellation

Name an owner and end-of-life path for connections, threads/tasks, queues, timers, streams and recordings. The owner handles partial acquisition, cancellation, cleanup and error reporting. Higher layers call a simple `stop`/`close` rather than manipulating internals. Specify repeat-call behavior and cleanup failure. No unowned background work, hidden infinite queues or unbounded concurrency may be introduced. The existing call queue is not an admission-capacity guarantee; do not mistake delivery slots for one.

### Synthetic example: owned session

Bad — operation failure leaks the resource:

```python
def run(open_session, operate):
    session = open_session()
    operate(session)
    session.close()
```

Good — standalone ownership example:

```python
from collections.abc import Callable
from threading import Event
from typing import Protocol

class Session(Protocol):
    def close(self) -> None: ...

class WorkCancelled(Exception):
    pass

def run_owned_session(
    acquire: Callable[[], Session],
    operate: Callable[[Session, Event], None],
    stop: Event,
) -> None:
    """Own one acquired session; propagate work and cleanup failures."""
    if stop.is_set():
        raise WorkCancelled()
    session = acquire()
    try:
        if stop.is_set():
            raise WorkCancelled()
        operate(session, stop)
    finally:
        session.close()
```

Why: ownership transfers after successful acquisition; `finally` covers operation error and cooperative cancellation. Acquisition must clean up its own partial failure. `operate` must poll the event or use bounded waits; this does not interrupt arbitrary blocking code. Close is attempted once per invocation, not guaranteed idempotent. If close fails during work failure, Python propagates the close exception with the original in context; preserve both in reporting. Multiple resources should use context managers/`ExitStack` with explicit ownership.

Tests: pre-cancel acquires nothing; acquisition failure does not call operation; cancellation after acquire closes once; success and operation failure close once; cleanup failure propagates with original context; invoke twice with fresh resources to confirm no sharing. Review: reject claims of forced cancellation, retrying an unsafe close or losing the primary failure without diagnostic context.

## 6) Errors, retries, concurrency and debt

Preserve exception classes, acceptance criteria, timeout meanings, message order and observability unless an intentional migration is approved. Retry only with a bounded policy, explicit owner and duplicate-side-effect analysis; message send acceptance is not safe retry evidence by itself. Keep I/O out of locked state planning where feasible and test deadline/dequeue and cancellation races with deterministic synchronization rather than arbitrary sleeps.

Reject duplicated logic, hidden globals added for convenience, swallowed errors, vague methods, unclear ownership, provider internals leaking upward, speculative abstractions and unbounded work. A temporary workaround needs scope, reason and removal conditions; those do not waive mandatory rules. Existing global initialization is legacy reality, not a pattern to expand.

## 7) Compatibility and application customization

Protect routing predicates, YAML language keys, sender activity shape, one-session admission, call IDs, deadline clocks, terminal behavior, text-before-recording ordering and cleanup. Dependency upgrades require inspecting installed APIs and compatibility tests; preserve UTF-16 requirements encoding unless intentionally migrating it. Branding belongs in application content/configuration, not generic dependency internals.

Use configuration → application code → existing injection → narrow reusable interface/option → core change → fork. Check factory constructor requirements, global filter effects and `stop()` ownership. This repository does not promise a White Label distribution license. Read `LICENCE` and applicable dependency/provider terms before distribution claims. Never publish credentials, private endpoints, personal message payloads or local IDE shelves. Intentional breaks require explicit migration plans and reviewer approval.

## 8) Setup and verification

Use Python 3.11+ and a virtual environment. Install the pinned dependencies with `python -m pip install -r requirements.txt`. Installation requires network and is not itself a test. Use `config/.env.example` only as a template, with private credentials outside commits. `python bot.py` starts live services; it is not an ordinary smoke test. Do not import `bot.py` for syntax checks.

From the root, with dependencies installed:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest discover -s tests -p 'test_incoming_calls.py'
python -m unittest discover -s tests -p 'test_call_coordinator.py'
```

Use the same discovery pattern for `test_call_state_machine.py`, `test_call_delivery.py`, `test_recording_uploader.py`, `test_call_envs.py`, `test_call_activity.py`, `test_call_filter_routing.py` and `test_chat_gpt_compatibility.py` as affected. Review mocks before running new tests: constructors may perform network I/O. Routine verification must use fake executors, notification/API doubles and mock transport. Live checks need explicit scope, isolated accounts and authorization; local tests do not prove provider interoperability.

For menu/chat changes add focused tests for state entry, missing key/translation behavior and exits. For calls cover FIFO/duplicates, stale offers, terminal-before-offer, deadline races, queued cancellation, stop and failed delivery cleanup. For configuration test both sources and fallback boundaries without fetching Spring configuration. Documentation-only changes need link/fence/example checks and `git diff --check`, not live startup. There is no repository CI/lint/typecheck command to claim as passed.

## 9) Mandatory review decision

A change fails review for any mandatory policy violation, unapproved compatibility break, avoidable technical debt, unclear ownership, sensitive data exposure, unverifiable correctness or missing risk-appropriate tests. In particular reject direct call-state mutation outside its owner, removed deadline rechecks, early dialog release, changed acceptance checks without migration, and recording paths without cleanup on failure.

Reviewers must check function sizes and responsibility, contracts and names, real need for abstractions, error/cancellation paths, translation consistency, bounded concurrency, tests and truthful validation evidence. Only explicit reviewers may grant narrowly documented exceptions. Do not broaden unrelated legacy cleanup to meet an idealized architecture. Completion reports must distinguish checks executed, checks omitted and provider behavior not verified.
