# Data Model

This document describes the entities of the Mirror Presence Layer, their fields, and the relationships between them.

## Entities

### User

The project uses Django’s configured authentication User model. Its fields and authentication behavior are managed by Django.

The Presence Layer relates each User to one Human through a one-to-one relationship.

### Human

| Field      | Description                                                                   |
|------------|-------------------------------------------------------------------------------|
| `human_id` | Unique identifier of the Human.                                               |
| `user_id`  | Identifier of the associated User. Each User can be linked to only one Human. |
| `name`     | Name of the Human within Mirror.                                              |

### Invitation

| Field           | Description                                        |
|-----------------|----------------------------------------------------|
| `invitation_id` | Unique identifier of the Invitation.               |
| `human_id`      | Human who created the Invitation.                  |
| `gesture`       | Gesture written by the Human.                      |
| `created_at`    | Date and time when the Invitation was created.     |
| `status`        | Invitation status: `open`, `matched`, or `closed`. |

### Response

| Field           | Description                                                                    |
|-----------------|--------------------------------------------------------------------------------|
| `response_id`   | Unique identifier of the Response.                                             |
| `invitation_id` | Invitation to which the Response belongs.                                      |
| `human_id`      | Human who created the Response.                                                |
| `words`         | Words written in the Response.                                                 |
| `created_at`    | Date and time when the Response was created.                                   |
| `status`        | Response status: `pending`, `accepted`, `rejected`, `cancelled`, or `expired`. |

### Moment

| Field                  | Description                                              |
|------------------------|----------------------------------------------------------|
| `moment_id`            | Unique identifier of the Moment.                         |
| `accepted_response_id` | Accepted Response from which the Moment was created.     |
| `media_room_id`        | Identifier of the private media room.                    |
| `started_at`           | Date and time when the Moment started.                   |
| `ended_at`             | Date and time when the Moment ended. Empty while active. |
| `status`               | Moment status: `active` or `completed`.                  |

### Presence

| Field         | Description                                                       |
|---------------|-------------------------------------------------------------------|
| `presence_id` | Unique identifier of the Presence record.                         |
| `moment_id`   | Moment in which the Human participates.                           |
| `human_id`    | Participating Human.                                              |
| `joined_at`   | Date and time when the Human joined the Moment.                   |
| `left_at`     | Date and time when the Human left the Moment. Empty while active. |
| `status`      | Presence status: `active` or `completed`.                         |               |

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
