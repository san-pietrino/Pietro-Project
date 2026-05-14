# Pietro - Peer-to-Peer Lending Web App

## Project Overview
- **Name**: Pietro
- **Type**: Web application (local self-hosted)
- **Purpose**: Facilitate organized peer-to-peer lending within a city
- **Tone**: Friendly and informal (both aesthetic and language)

## Tech Stack
- **Backend**: Python Flask (lightweight, easy to understand)
- **Database**: SQLite (simple, local, no setup required)
- **Frontend**: Vanilla HTML/CSS/JavaScript (single-page app)
- **Protocol**: HTTP/JSON

## Components

### 1. Authentication
- Login form with username/password
- Registration page for new users
- User location stored during registration
- Session-based authentication

### 2. Item Search
- Search bar for items (e.g., "screwdriver")
- Query item database
- Show availability status
- Sort by proximity to user's location
- Request form for items not in database
- Keyword notification system

### 3. Borrowing Process
- Item selection from search results
- Request to owner (accept/decline)
- Pre-defined response options
- Chat between borrower and owner
- Item status management (available/suspended)

## Data Models

### User
- id (primary key)
- username (unique)
- password (hashed)
- location
- keywords (for notifications)

### Item
- id (primary key)
- name
- description
- owner_id (foreign key)
- status (available/unavailable)
- keywords

### Request
- id (primary key)
- item_id (foreign key)
- borrower_id (foreign key)
- status (pending/accepted/declined)

### Message
- id (primary key)
- request_id (foreign key)
- sender_id (foreign key)
- content
- timestamp

## Acceptance Criteria
1. User can register with username, password, and location
2. User can login with valid credentials
3. User can search for items by name
4. User can see available items sorted by proximity
5. User can request an item
6. Owner can accept/decline requests
7. Chat works between borrower and owner
8. Request form works for items not in database
9. Keyword notifications are sent