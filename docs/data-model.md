# Data Model

This document describes how the six core entities of the Mirror Presence Layer — User, Human, Moment, Response, Presence, and Memory — are represented as data and related to one another.

## Entities

### User

| Field        | Description                                       |
|--------------|---------------------------------------------------|
| `user_id`    | Unique identifier of the User.                    |
| `email`      | Unique email address associated with the account. |
| `created_at` | Date and time when the account was created.       |

### Human

| Field      | Description                                                                   |
|------------|-------------------------------------------------------------------------------|
| `human_id` | Unique identifier of the Human.                                               |
| `user_id`  | Identifier of the associated User. Each User can be linked to only one Human. |
| `name`     | Name of the Human within Mirror.                                              |

### Moment

| Field          | Description                                                                         |
|----------------|-------------------------------------------------------------------------------------|
| `moment_id`    | Unique identifier of the Moment.                                                    |
| `human_id`     | Identifier of the Human who opened the Moment.                                      |
| `gesture`      | Short written Gesture that sets the Moment’s initial meaning or way of entering it. |
| `media_stream` | Identifier or reference to the Moment’s media stream.                               |
| `created_at`   | Date and time when the Moment was opened.                                           |
| `ended_at`     | Date and time when the Moment was ended. Empty while the Moment is active.          |
| `status`       | Moment status: `active` or `completed`.                                             |

### Response

| Field         | Description                                                                    |
|---------------|--------------------------------------------------------------------------------|
| `response_id` | Unique identifier of the Response.                                             |
| `moment_id`   | Identifier of the Moment to which the Response belongs.                        |
| `human_id`    | Identifier of the Human who created the Response.                              |
| `words`       | Words through which the Human addresses another Human’s Moment.                |
| `created_at`  | Date and time when the Response was created.                                   |
| `status`      | Response status: `pending`, `accepted`, `rejected`, `cancelled`, or `expired`. |

### Presence

| Field         | Description                                                                       |
|---------------|-----------------------------------------------------------------------------------|
| `presence_id` | Unique identifier of the Presence record.                                         |
| `moment_id`   | Identifier of the Moment in which the Human participates.                         |
| `human_id`    | Identifier of the participating Human.                                            |
| `role`        | Human’s role in the Moment: `author` or `participant`.                            |
| `joined_at`   | Date and time when the Human entered the Moment.                                  |
| `left_at`     | Date and time when the Human left the Moment. Empty while the Presence is active. |
| `status`      | Presence status: `active` or `completed`.                                         |

### Memory

| Field         | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `memory_id`   | Unique identifier of the Memory record.                                     |
| `human_id`    | Identifier of the Human whose manifestation is preserved.                   |
| `moment_id`   | Identifier of the Moment in which the manifestation appeared.               |
| `source_type` | Source of the preserved manifestation: `gesture` or `response`.             |
| `content`     | A snapshot of the Gesture or Response Words preserved by the Memory record. |
| `created_at`  | Date and time when the Memory record was created.                           |

## Relationships

| Entities          | Cardinality | Description                                                                                        |
|-------------------|-------------|----------------------------------------------------------------------------------------------------|
| User — Human      | One-to-one  | Each User is associated with one Human, and each Human belongs to one User.                        |
| Human — Moment    | One-to-many | A Human may open multiple Moments. Each Moment has one author.                                     |
| Human — Response  | One-to-many | A Human may create multiple Responses. Each Response belongs to one Human.                         |
| Moment — Response | One-to-many | A Moment may receive multiple Responses. Each Response belongs to one Moment.                      |
| Human — Presence  | One-to-many | A Human may have Presence records in multiple Moments. Each Presence record belongs to one Human.  |
| Moment — Presence | One-to-many | A Moment may include multiple Presence records. Each Presence record belongs to one Moment.        |
| Human — Memory    | One-to-many | A Human may have multiple Memory records. Each Memory record belongs to one Human.                 |
| Moment — Memory   | One-to-many | A Moment may be associated with multiple Memory records. Each Memory record belongs to one Moment. |
