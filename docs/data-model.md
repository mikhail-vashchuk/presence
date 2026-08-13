# Data Model

This document describes the entities of the Mirror Presence Layer, their fields, and the relationships between them.

## Entities

### User

`User` is the configured Django authentication model. It represents the technical account used for authentication.

| Field     | Meaning                          |
|-----------|----------------------------------|
| `user_id` | Unique identifier of the User.   |
| `email`   | Unique authentication email.     |

### Human

| Field        | Description                                                                   |
|--------------|-------------------------------------------------------------------------------|
| `human_id`   | Unique identifier of the Human.                                               |
| `user_id`    | Identifier of the associated User. Each User can be linked to only one Human. |
| `first_name` | First name of the Human.                                                      |
| `last_name`  | Last name of the Human.                                                       |

### Invitation

| Field           | Description                                        |
|-----------------|----------------------------------------------------|
| `invitation_id` | Unique identifier of the Invitation.               |
| `human_id`      | Human who created the Invitation.                  |
| `gesture`       | Gesture written by the Human.                      |
| `created_at`    | Date and time when the Invitation was created.     |
| `status`        | Invitation status: `open`, `matched`, or `closed`. |

### Response

| Field           | Description                                                                   |
|-----------------|-------------------------------------------------------------------------------|
| `response_id`   | Unique identifier of the Response.                                            |
| `invitation_id` | Invitation to which the Response belongs.                                     |
| `human_id`      | Human who created the Response.                                               |
| `words`         | Words written in the Response.                                                |
| `created_at`    | Date and time when the Response was created.                                  |
| `status`        | Response status: `pending`, `accepted`, `rejected`, `cancelled`, or `closed`. |

### Moment

| Field                  | Description                                              |
|------------------------|----------------------------------------------------------|
| `moment_id`            | Unique identifier of the Moment.                         |
| `accepted_response_id` | Accepted Response from which the Moment was created.     |
| `media_room_id`        | Identifier of the private media room.                    |
| `started_at`           | Date and time when the Moment started.                   |
| `ended_at`             | Date and time when the Moment ended. Empty while active. |

### Presence

| Field         | Description                                                       |
|---------------|-------------------------------------------------------------------|
| `presence_id` | Unique identifier of the Presence record.                         |
| `moment_id`   | Moment in which the Human participates.                           |
| `human_id`    | Participating Human.                                              |

## Relationships

| Entities              | Cardinality | Description                                   |
|-----------------------|-------------|-----------------------------------------------|
| User — Human          | One-to-one  | Technical account and its Human.              |
| Human — Invitation    | One-to-many | A Human may create multiple Invitations.      |
| Invitation — Response | One-to-many | An Invitation may receive multiple Responses. |
| Human — Response      | One-to-many | A Human may create multiple Responses.        |
| Response — Moment     | One-to-one  | An accepted Response creates one Moment.      |
| Moment — Presence     | One-to-many | A Moment contains Presence records.           |
| Human — Presence      | One-to-many | A Human may participate in multiple Moments.  |

## Domain Constraints

- A Human may have at most one open Invitation.
- A Human may have at most one pending Response.
- A Human may not respond to their own Invitation.
- A Human participating in an active Moment may not create an Invitation or send a Response.
- An Invitation may have at most one accepted Response.
- Each Response may create at most one Moment.
- Each Human may have at most one Presence record within the same Moment.
- Only the author of an Invitation may accept or reject its Responses.
- Only the author of an Invitation may close it.
- Only the author of a Response may cancel it.
- Only a participant of an active Moment may complete it.