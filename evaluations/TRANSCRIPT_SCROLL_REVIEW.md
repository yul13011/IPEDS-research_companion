# Conversation scrolling — October 21, 2026

The conversation container previously had a key containing the completed-exchange revision and a pending suffix. Submission and completion therefore replaced the scroll viewport. The newly mounted viewport started at its initial position; Streamlit's animated follow behavior could subsequently move it to the bottom. Native following also intentionally suspends after scrolling upward, so forcing a fresh container was an unreliable way to resume it for a new question.

## Implemented behavior

- One stable `conversation_messages` container throughout submission, status updates, answer completion and ordinary widget reruns. Exchange revision still identifies unrelated UI controls, not the viewport.
- One scroll owner: native animated auto-scroll is disabled for this container. Application-owned JavaScript follows content/layout changes with instant positioning before paint, without scrolling the whole page.
- A request serial increments once when a new pending request is first rendered. A new request resumes following even if the user had been reading older messages. Pending-to-completed rerenders reuse that serial and the same viewport.
- Wheel/touch scrolling upward or dragging the scrollbar pauses following. Returning to the bottom resumes it. Answer growth while paused does not force the user down. Formatting pauses following; unrelated menu/sidebar reruns do not create a new request.
- Late content/layout changes are observed without animation. The JavaScript is static local application code; only an integer request serial and boolean editing flag are interpolated. Questions, model text, source data and credentials are never put into executable HTML. No iframe parent access, external scripts or dependency changes.

Files: `prototype/transcript_scroll.py`, `prototype/transcript_scroll.js`, `prototype/ui.py`.

## Evidence

**11 Python/AppTest checks passed in 22.117 seconds** (`transcript_scroll_ui_tests.log`): pending and completed renders use the same container identity; native scrolling stays disabled; one request gets one serial; menu/sidebar reruns preserve it; questions remain in history; new submissions advance it; clear conversation and existing tools/memory behavior work. User input is absent from the script HTML.

**3 production-JavaScript controller checks passed** (`transcript_scroll_controller_tests.log`): following pending/answer growth; manual reading during an in-flight answer; later chart resize; scrollbar/return-to-bottom behavior; menu resizing and formatting. These run the actual asset with deterministic event/layout doubles, not a real browser.

**Real browser check** on isolated port 8517, using the production UI/controller and eight long fixture exchanges with a delayed local answer. No model calls or statistical source changes:

| Check | Browser measurement |
|---|---|
| Initial long conversation | 232 px viewport, 2470 px content, scroll top 2237.78 px (bottom within 1 px) |
| Manually read oldest exchange, collapse menu | Scroll top stays 0; viewport grows to 394 px |
| Submit from oldest exchange | Pending question visible; bottom gap about 0.22 px |
| Completed answer | Bottom gap about 0.11 px; latest answer present |
| Read oldest exchange and collapse Tools | Scroll top stays 0 |
| Submit again after sidebar layout change | Latest answer present, 349 px viewport, 3095 px content, bottom gap about 0.22 px; outer page scroll stays 0 |

Fixture: `prototype/tests/scroll_browser_fixture.py`. The browser measurements verify positions across real interactions; they are not a frame-by-frame animation recording. Manual reading specifically during answer arrival is covered deterministically by the controller tests. The fixture deliberately substitutes a delayed text answer and is not a numerical/model benchmark. The main app was restarted on port 8516 after verification; the isolated fixture was stopped.
