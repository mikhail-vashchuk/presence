# Core Workflows

This document describes the state-changing operations supported by the Mirror Presence Layer and their effects on the domain entities.

## Registering

1. A person provides an email address and a name.
2. The system creates a User and an associated Human.

## Opening a Moment

1. A Human opens a Moment with a Gesture and a media stream.
2. The system creates the Moment with the `active` status.
3. An active Presence is created for the Human with the `author` role.

## Sending a Response

1. A Human sends Words in response to another Human’s active Moment.
2. The system creates a Response with the `pending` status.

## Reviewing a Response

1. The author of an active Moment accepts or rejects one of its pending Responses.
2. The system updates the Response status to `accepted` or `rejected`.
3. If the Response is accepted, an active Presence is created for the responding Human with the `participant` role.

## Cancelling a Response

1. A Human cancels one of their own pending Responses.
2. The system changes the Response status to `cancelled`.

## Leaving a Moment

1. A participant leaves a Moment in which their Presence is active.
2. The system records the leaving time and changes the Presence status to `completed`.
3. The Moment and the Presences of other Humans remain active.

## Ending a Moment

1. The author ends their active Moment.
2. The system records the ending time and changes the Moment status to `completed`.
3. All active Presences associated with the Moment are completed and receive a leaving time.
4. The completed Moment no longer accepts new Responses.

## Forming Memory

1. When a Human opens a Moment or submits a Response, the system creates a Memory record containing a snapshot of the Moment’s Gesture or the Response’s Words.
2. The record remains linked to the Human and the Moment regardless of the later status of the Response.
