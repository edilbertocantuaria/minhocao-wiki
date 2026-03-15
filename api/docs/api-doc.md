# Minhocão Wiki API — Documentation

## Overview

REST API built with FastAPI. Provides JWT-authenticated access to a RAG (Retrieval-Augmented Generation) chat backed by PostgreSQL persistence.

- **Base URL (local):** `http://localhost:8000`
- **Interactive docs:** `http://localhost:8000/docs`
- **Content-Type:** `application/json` for all request bodies (except `/auth/token`)

---

## Authentication

All endpoints except `/auth/register`, `/auth/login`, and `/auth/token` require a Bearer token in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

The token is a **JWT** (HS256), valid for **60 minutes**. There is no refresh token — re-authenticate when the token expires.

### Typical auth flow

```
1. POST /auth/register   → create account
2. POST /auth/login      → receive access_token
3. Use access_token      → send as Authorization: Bearer header on every protected request
```

---

## Error Response Shape

All errors follow the standard FastAPI error envelope:

```json
{
  "detail": "Human-readable error message"
}
```

---

## Endpoints

### 1. Register

**`POST /auth/register`**

Creates a new user account.

#### Request body

```json
{
  "email": "user@example.com",
  "password": "minimum6chars"
}
```

| Field      | Type   | Required | Rules             |
|------------|--------|----------|-------------------|
| `email`    | string | yes      | valid email format |
| `password` | string | yes      | min length: 6     |

#### Response — `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-03-15T14:00:00.000000+00:00"
}
```

| Field        | Type             | Description                  |
|--------------|------------------|------------------------------|
| `id`         | string (UUID v4) | Unique user identifier       |
| `email`      | string           | Registered email             |
| `created_at` | string (ISO 8601)| Account creation timestamp   |

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `409`  | `"Email already registered"` | Email already in use |
| `422`  | Validation error object | Invalid email format or short password |
| `503`  | `"Database unavailable..."` | PostgreSQL unreachable |
| `500`  | `"Database error while creating user"` | Unexpected DB error |

---

### 2. Login

**`POST /auth/login`**

Authenticates a user and returns a JWT token.

#### Request body

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

| Field      | Type   | Required |
|------------|--------|----------|
| `email`    | string | yes      |
| `password` | string | yes      |

#### Response — `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

| Field          | Type   | Description                         |
|----------------|--------|-------------------------------------|
| `access_token` | string | JWT to be sent in `Authorization` header |
| `token_type`   | string | Always `"bearer"`                   |

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Invalid email or password"` | Wrong credentials |
| `422`  | Validation error object | Malformed request body |
| `503`  | `"Database unavailable..."` | PostgreSQL unreachable |

---

### 3. Login (OAuth2 form — Swagger only)

**`POST /auth/token`**

OAuth2 password grant form endpoint. Primarily used by the Swagger **Authorize 🔒** button. Functionally identical to `/auth/login`.

#### Request body — `application/x-www-form-urlencoded`

| Field      | Type   | Required |
|------------|--------|----------|
| `username` | string | yes (send the user's email here) |
| `password` | string | yes      |

#### Response — `200 OK`

Same as `/auth/login`.

> **Note for frontend:** Prefer `/auth/login` (JSON body). Use `/auth/token` only if you need OAuth2 form compatibility.

---

### 4. Create Conversation

**`POST /conversations`** 🔒

Creates a new conversation for the authenticated user.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request body

```json
{
  "title": "My first conversation"
}
```

| Field   | Type            | Required | Notes                              |
|---------|-----------------|----------|------------------------------------|
| `title` | string or null  | no       | Omit or send `null` for no title   |

#### Response — `201 Created`

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "My first conversation",
  "created_at": "2026-03-15T14:05:00.000000+00:00"
}
```

| Field        | Type              | Description                   |
|--------------|-------------------|-------------------------------|
| `id`         | string (UUID v4)  | Conversation identifier       |
| `title`      | string or null    | Conversation title            |
| `created_at` | string (ISO 8601) | Creation timestamp            |

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Missing bearer token..."` | No/invalid token |
| `422`  | Validation error object | Malformed body |

---

### 5. List Conversations

**`GET /conversations`** 🔒

Returns all conversations belonging to the authenticated user.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response — `200 OK`

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "My first conversation",
    "created_at": "2026-03-15T14:05:00.000000+00:00"
  },
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": null,
    "created_at": "2026-03-15T15:00:00.000000+00:00"
  }
]
```

Returns an empty array `[]` if the user has no conversations.

Each item has the same shape as the `POST /conversations` response.

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Missing bearer token..."` | No/invalid token |

---

### 6. Get Conversation Messages

**`GET /conversations/{conversation_id}`** 🔒

Returns all messages in a specific conversation (in chronological order).

#### Path parameter

| Parameter         | Type             | Description           |
|-------------------|------------------|-----------------------|
| `conversation_id` | string (UUID v4) | Conversation to fetch |

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response — `200 OK`

```json
[
  {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "role": "user",
    "content": "What is the Minhocão?",
    "created_at": "2026-03-15T14:10:00.000000+00:00"
  },
  {
    "id": "d4e5f6a7-b8c9-0123-def0-234567890123",
    "role": "assistant",
    "content": "The Minhocão (officially Elevado Costa e Silva) is an elevated expressway...",
    "created_at": "2026-03-15T14:10:03.000000+00:00"
  }
]
```

| Field        | Type              | Description                                    |
|--------------|-------------------|------------------------------------------------|
| `id`         | string (UUID v4)  | Message identifier                             |
| `role`       | string            | Either `"user"` or `"assistant"`               |
| `content`    | string            | Full message text                              |
| `created_at` | string (ISO 8601) | Message timestamp                              |

Returns an empty array `[]` if no messages have been sent yet.

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Missing bearer token..."` | No/invalid token |
| `404`  | `"Conversation not found"` | ID doesn't exist or belongs to another user |

---

### 7. Delete Conversation

**`DELETE /conversations/{conversation_id}`** 🔒

Deletes a conversation and all its messages (cascade).

#### Path parameter

| Parameter         | Type             | Description              |
|-------------------|------------------|--------------------------|
| `conversation_id` | string (UUID v4) | Conversation to delete   |

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response — `204 No Content`

Empty body. Deletion was successful.

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Missing bearer token..."` | No/invalid token |
| `404`  | `"Conversation not found"` | ID doesn't exist or belongs to another user |

---

### 8. Chat (Streaming)

**`POST /chat`** 🔒

Sends a question within a conversation and returns the assistant's answer as a **streaming plain-text response** (Server-Sent style chunked transfer).

The message history of the conversation is automatically used as context. Both the user question and the assistant answer are persisted to the database after the stream completes.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request body

```json
{
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "question": "What is the Minhocão?"
}
```

| Field             | Type             | Required | Rules          |
|-------------------|------------------|----------|----------------|
| `conversation_id` | string (UUID v4) | yes      | must belong to the authenticated user |
| `question`        | string           | yes      | min length: 1  |

#### Response — `200 OK` (streaming)

- **Content-Type:** `text/plain`
- **Transfer-Encoding:** `chunked`

The response body is the assistant's answer delivered as a stream of text chunks. The frontend must read the response incrementally and concatenate the chunks to render the full message progressively.

**Example (concatenated result):**
```
The Minhocão (officially Elevado Costa e Silva) is an elevated expressway in São Paulo...
```

There is **no JSON envelope** — the raw text of the answer is streamed directly.

#### How to consume the stream (JavaScript)

```javascript
const response = await fetch("http://localhost:8000/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${accessToken}`,
  },
  body: JSON.stringify({
    conversation_id: conversationId,
    question: userMessage,
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let fullText = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value, { stream: true });
  fullText += chunk;
  // update UI incrementally here
}
```

#### Error codes

| Status | `detail` | Cause |
|--------|----------|-------|
| `401`  | `"Missing bearer token..."` | No/invalid token |
| `404`  | `"Conversation not found"` | `conversation_id` doesn't exist or belongs to another user |
| `422`  | Validation error object | Malformed body or empty question |

---

## Complete Frontend Flow

```
1. Register
   POST /auth/register
   Body: { email, password }
   → store nothing (optionally auto-login)

2. Login
   POST /auth/login
   Body: { email, password }
   → store access_token (memory or sessionStorage — avoid localStorage for security)

3. Load conversations
   GET /conversations
   Header: Authorization: Bearer <access_token>
   → render sidebar list

4. Create a conversation (if new chat)
   POST /conversations
   Body: { title: null }  or  { title: "some title" }
   Header: Authorization: Bearer <access_token>
   → store returned conversation.id

5. Load message history (when user opens an existing conversation)
   GET /conversations/{conversation_id}
   Header: Authorization: Bearer <access_token>
   → render messages with role "user" / "assistant"

6. Send a message
   POST /chat
   Body: { conversation_id, question }
   Header: Authorization: Bearer <access_token>
   → stream response, render chunks as they arrive

7. Delete a conversation
   DELETE /conversations/{conversation_id}
   Header: Authorization: Bearer <access_token>
   → remove from sidebar list on 204 response

8. Handle 401 globally
   → clear stored token, redirect to login screen
```

---

## Data Types Reference

| Type | Format | Example |
|------|--------|---------|
| UUID | `string` — UUID v4 | `"550e8400-e29b-41d4-a716-446655440000"` |
| Timestamp | `string` — ISO 8601 with timezone | `"2026-03-15T14:00:00.000000+00:00"` |
| Role | `string` — enum | `"user"` or `"assistant"` |
| Token type | `string` | always `"bearer"` |

---

## Security Notes

- Tokens expire after **60 minutes**. Implement re-authentication on `401` responses.
- Store `access_token` in memory (React state) or `sessionStorage`. Avoid `localStorage` due to XSS risk.
- All conversation/message endpoints are **scope-isolated**: users can only access their own data. Attempting to access another user's conversation returns `404`.
- Passwords must be at least **6 characters**. The API stores only bcrypt hashes — plaintext passwords are never stored.
