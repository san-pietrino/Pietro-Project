# Implementation Decisions

This file documents all decisions made during the implementation that were not explicitly specified in the original requirements.

## Decision #1: Flask as Backend Framework

**What was unclear**: The specification mentioned "backend" but didn't specify the technology.

**What I decided**: Use Flask (Python) as it's lightweight, easy to understand for beginners, and well-documented.

**Alternatives**: FastAPI (more modern, better async support), Django (more feature-rich but complex)

**Can easily be changed**: Yes - the API structure is simple and can be ported to another framework if needed.

---

## Decision #2: Session Secret Key

**What was unclear**: How to manage user sessions securely.

**What I decided**: Use a hardcoded secret key for Flask sessions. In production, this should be an environment variable.

**Alternatives**: Environment variables, database-backed sessions

**Can easily be changed**: Yes - just update the `app.secret_key` line.

---

## Decision #3: Password Hashing

**What was unclear**: How to store passwords securely.

**What I decided**: Use werkzeug's `generate_password_hash` and `check_password_hash` (uses PBKDF2 by default).

**Alternatives**: bcrypt, argon2

**Can easily be changed**: Yes - werkzeug supports multiple hashers.

---

## Decision #4: Proximity Sorting

**What was unclear**: How to calculate "proximity" to user's location.

**What I decided**: Simple string matching - exact match first, then partial match, then others. This is a basic implementation that could be improved with geolocation coordinates.

**Alternatives**: GPS coordinates with haversine formula, postal code matching

**Can easily be changed**: Yes - the sorting logic is in the search route.

---

## Decision #5: Keyword Notification System

**What was unclear**: How to notify users when new items match their keywords.

**What I decided**: A simple notifications page that users can visit to see items matching their keywords. Real-time notifications would require WebSockets or polling.

**Alternatives**: Email notifications, push notifications, WebSocket real-time updates

**Can easily be changed**: Yes - the notification logic is in the notifications route.

---

## Decision #6: Pre-defined Response Options

**What was unclear**: The specification mentioned "pre-defined responses" for owners but didn't specify what they are.

**What I decided**: Simple Accept/Decline buttons on the dashboard. The pre-defined responses are implicit in the accept/decline action.

**Alternatives**: A dropdown with specific messages like "Yes, you can borrow it", "Sorry, it's in use", etc.

**Can easily be changed**: Yes - update the respond_request route.

---

## Decision #7: Item Status Management

**What was unclear**: How to handle item status when a request is declined.

**What I decided**: Set item status to "suspended" when declined, meaning it won't appear in search results. The owner would need to manually reactivate it.

**Alternatives**: Automatically reactivate after a certain time, allow owner to set availability manually

**Can easily be changed**: Yes - update the respond_request route.

---

## Decision #8: Single-Page App Structure

**What was unclear**: The specification didn't specify how to structure the frontend.

**What I decided**: Use Flask's template rendering with separate HTML pages for each view. This is simpler than a JavaScript SPA and easier for beginners to understand.

**Alternatives**: Next.js with React, Vue.js, Svelte

**Can easily be changed**: Yes - but would require significant rewrite.

---

## Decision #9: SQLite Database

**What was unclear**: The specification mentioned "database" but not which type.

**What I decided**: Use SQLite as it's built into Python, requires no setup, and stores data in a single file.

**Alternatives**: PostgreSQL, MySQL

**Can easily be changed**: Yes - but would require SQLAlchemy or similar ORM for easy migration.

---

## Decision #10: Chat Implementation

**What was unclear**: How the chat between borrower and owner works.

**What I decided**: A simple message-based chat tied to a borrow request. Messages are stored in the database and displayed chronologically.

**Alternatives**: Real-time chat with WebSockets, third-party chat service

**Can easily be changed**: Yes - the chat logic is in the chat routes.