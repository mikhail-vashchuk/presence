# Core Workflows

This document describes the state-changing workflows currently implemented by the Mirror Presence Layer.

## Creating an Invitation

1. A Human submits a Gesture.
2. The system validates the request.
3. The system creates an `open` Invitation.

---

## Sending a Response

1. A Human chooses an Invitation.
2. The Human submits a Response.
3. The system validates the request.
4. The system creates a `pending` Response.

---

## Rejecting a Response

1. The author of the Invitation chooses a Response and sends the request.
2. The system validates the request.
3. The system marks the Response as `rejected`.

---

## Accepting a Response

1. The author of the Invitation chooses a Response and sends the request.
2. The system validates the request.
3. The selected Response becomes `accepted`.
4. All other pending Responses to the same Invitation become `closed`.
5. The Invitation becomes `matched`.
6. The system creates a Moment.
7. The system records the Presence of both Humans.

---

## Closing an Invitation

1. The author chooses their Invitation and sends the request.
2. The system validates the request.
3. The Invitation becomes `closed`.
4. All pending Responses to that Invitation become `closed`.

---

## Cancelling a Response

1. The author chooses their Response and sends the request.
2. The system validates the request.
3. The Response becomes `cancelled`.

---

## Completing a Moment

1. One of the participants in the Moment sends the request.
2. The system validates the request.
3. The Moment is marked as completed by recording its completion time.