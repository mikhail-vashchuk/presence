# Presence

**A Django backend for a private online meeting between two people.**

## How the meeting works

A Human creates an Invitation with a short message.

Another Human can respond to an open Invitation.

The Invitation's author can accept or reject that Response.

When a Response is accepted, a Moment begins and both participants can enter its private video room.

```text
Invitation
    ↓
Response
    ↓
Acceptance
    ↓
Moment
```

Each Human taking part in a Moment is represented by a Presence.

Either participant can later complete the Moment.

## Domain rules

- A Human can have only one open Invitation.
- A Human can have only one pending Response.
- A Human cannot respond to their own Invitation.
- A Human in an active Moment cannot create an Invitation or send a Response.
- Only the author of an Invitation can accept or reject its Responses.
- Only participants of a Moment can access its video room.
- Public Invitations are unavailable while a Human is in an active Moment.

## Project structure

Presence is built with Django and Django REST Framework and is divided into three applications.

### `accounts`

Handles authentication and email verification and contains the `User` model.

### `humans`

Contains the `Human` model.

A `User` represents an authenticated account, while a `Human` represents the person taking part in the meeting.

### `presence`

Contains the meeting logic and its four central models:

- `Invitation`
- `Response`
- `Moment`
- `Presence`

Private video rooms are provided through LiveKit.

## Scope

Presence is limited to this meeting flow.

It does not define discovery or ranking systems, a social graph, persistent messaging, detailed profiles, or a wider social application around the meeting.

## Running the project

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using `.env.example` as a reference.

Apply migrations:

```bash
python manage.py migrate
```

Run the development server:

```bash
python manage.py runserver
```

## Documentation

The main architectural decisions are described in [`docs/architecture.md`](docs/architecture.md).