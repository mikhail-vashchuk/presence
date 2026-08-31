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