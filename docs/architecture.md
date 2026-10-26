# Architecture

This document describes several architectural decisions used in Presence.

For a general overview of the project and the meeting flow, see the main [`README`](../README.md).

## Domain rules and database constraints

Services check whether an operation is allowed and return meaningful domain errors when it is not.

Rules that describe states that should never exist are also enforced with database constraints.

Operations that change several related objects are performed inside database transactions. For example, accepting a Response changes the Response and Invitation states, closes other pending Responses, and creates the Moment and both Presence records as one operation.

Where concurrent requests could act on the same state, the relevant rows are locked while the operation is being performed.

## API and domain logic

HTTP views do not decide whether an operation is allowed.

A view receives the request, identifies the current Human, calls the appropriate service, and translates the result into an HTTP response.

```text
request
    ↓
API view
    ↓
service
    ↓
domain state change
```

This keeps the meeting rules independent from the HTTP interface.

## Intention before identity

Before a Moment begins, Presence does not expose one Human's identity to the other.

An Invitation carries only the author's short message, while a Response carries only the responder's words.

Only after the Invitation's author accepts a Response does a direct meeting begin between them.

At that point a Moment is created and public Invitations are no longer available to the participants.

## Current Presence state

The client can request one current state for a Human:

```text
moment
invitation
response
idle
```

The backend determines that state from the current domain data and returns it to the client.

An active Moment is checked first, followed by an open Invitation and then a pending Response. If none exists, the Human is `idle`.

## Moment and media

A `Moment` represents the meeting independently from the technology used for the video connection.

The Presence model stores only a media room identifier, while the LiveKit implementation is kept separately in the media layer.

## Quiet assistant

A Moment can include a quiet assistant: an agent that joins the media room, listens, and occasionally offers both participants a short text hint when the conversation stalls.

The assistant is present only while both participants consent. Each `Presence` stores its own `agent_consent`, and either participant can withdraw it at any time. The assistant is active only while both consents are set.

Consent is presented as an offer rather than a request. A Human never sees whether the other participant declined or has not decided. If the other participant has agreed, the Human sees only that the assistant is on offer (`invited`), and a Moment where the other has not agreed looks the same as one where nobody has been asked.

The assistant works in the same room as the participants and keeps no memory of them:

- It hears the conversation, but the transcript is not stored and is not shown to anyone. Its working context exists only in memory and only for the duration of the Moment.
- It knows the Invitation gesture and the Response words, because they are the reason the meeting exists. It does not know anything about either Human's profile.
- The database keeps only metadata about its work: when a hint was offered, its kind, whether it was dismissed ("not now"), and an optional rating from each participant. The text of a hint is not stored.

Hints are recorded by `record_assistant_hint`, which refuses to record anything unless the assistant is active. Feedback is a rating without free text, and it can be sent only for a Moment where the assistant offered at least one hint.

### The assistant process

The assistant is a separate process (`assistant/`) built on LiveKit Agents. It shares no code or database with the Django applications and talks to them only through two internal endpoints protected by a service token (`ASSISTANT_SERVICE_TOKEN`).

```text
both Humans consent
    ↓
Django asks LiveKit to dispatch the assistant to the room
    ↓
assistant joins, listens, checks consent every few seconds
    ↓
after a pause, it records a hint in Django and sends it to the room
```

- **Dispatch.** `set_agent_consent` dispatches the assistant once the second consent is saved. Django never waits for it: a failed dispatch is logged and does not undo the consent.
- **Consent is checked, not remembered.** The assistant asks Django whether it is still active every few seconds and leaves as soon as the answer is no. If Django cannot be reached several times in a row it also leaves, because it can no longer know that consent stands.
- **Hearing.** Each participant's audio goes to a speech-to-text provider and is discarded. Only recognised text is kept, in memory, labelled `A` and `B`. Speaker labels are not identities.
- **When it speaks.** Rarely. A hint is allowed after a long pause or a long one-sided stretch (`assistant/policy.py`), never during the first seconds, and never more often than a cooldown. Dismissing a hint with "not now" doubles the cooldown.
- **What it says.** Claude writes one short question or topic from the Invitation, the Response and the conversation so far, using the participants' own language. Participant text reaches the model only as tagged data, never as instructions.
- **Delivery.** Hints reach the clients as LiveKit data packets on the `assistant.hint` topic (`{"hint_id": ..., "text": ...}`). Clients dismiss a hint through the public API, and the assistant learns about it from the next consent check.

### Client contract

Presence has no client of its own, so the assistant's contract with any client is the following.

| Need | How |
| --- | --- |
| Show the offer and the current state | `GET /api/presence/current/` returns `assistant: {consent, invited, active}` next to the Moment |
| Agree to or withdraw from the assistant | `PUT /api/presence/moments/<id>/agent-consent/` with `{"consent": true}` |
| Receive a hint | LiveKit data packet on topic `assistant.hint`: `{"hint_id": 1, "text": "..."}` |
| "Not now" | `POST /api/presence/assistant-hints/<hint_id>/dismiss/` |
| Rate the assistant after a Moment | `POST /api/presence/moments/<id>/assistant-feedback/` with `{"rating": "helpful"}`, accepted only if the assistant offered a hint |

When and how often a client asks for a rating is the client's decision. The backend only guarantees one rating per participant and only for a Moment where the assistant spoke.

### Privacy of the speech-to-text provider

The assistant opts out of the provider's model improvement program (`mip_opt_out`), so participants' audio is not used for training.

