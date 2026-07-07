# Fulabra
 
A real-time, browser-based multiplayer word-matching party game built with **Django** and **Django Channels**. Three players join a lobby, secretly pick a word from a shared category each round, and score points based on how their choices overlap — first to reach the target score wins the match.
 
---
 
## Table of Contents
 
- [Project Overview](#about--project-overview)
- [Features](#features)
- [Technologies](#technologies)
- [Installation Guide](#installation-guide)
- [Running the Tests](#running-the-tests)
- [Design Patterns](#design-patterns)
- [CI/CD](#cicd)
- [Authors](#authors)
- [License](#license)

---
 
## Project Overview
 
**Fulabra** is a social party game where: three players sit in the same lobby and, every round, each of them privately submits one word from a category everyone can see (e.g. *Profession*, *Animals*). Once all three players (or the round timer) resolve the round, the server reveals what everyone picked and scores it:
 
- If **exactly two** players submit the **same word**, both of them earn **+1 point**.
- If **all three** players submit the same word, players with a score above 0 **lose 1 point** (the "everybody thought alike" penalty).
- Any word picked by only one player scores nothing that round.
The game repeats rounds automatically (with a countdown to choose a word and a short pause to show results) until one or more players reach **3 points**, at which point the match ends, winners are recorded on their profile (`wins`), and everyone is returned to the lobby to play again.
 
Beyond the core loop, Fulabra also works as a small social hub: registered users have profiles, can add friends, see who's online/in a match in real time, invite friends directly into their lobby, and receive live notifications for friend requests and game invites — all without a page reload, thanks to HTMX and WebSockets.
 
## Features
 
- **Real-time multiplayer lobbies** — 3-player rooms identified by a short, shareable invite code, fully synced over WebSockets.
- **Guest access** — anyone can jump into a match with just a nickname and a preset/custom avatar, no account required.
- **Persistent accounts** — registration, login, and profile pages showing stats (`wins`, `stars`) and an editable avatar/nickname.
**Profile customization** — authenticated users can dynamically edit their registered nickname and choose from a collection of unique, preset profile avatars via a responsive modal interface.
- **Friends system** — search users, send/accept/reject friend requests, and see live **online / offline / in-game** presence indicators for each friend.
- **Live notifications inbox** — friend requests and game invites are pushed to the recipient instantly, with a live-updating unread badge in the navbar.
- **Word-matching game engine** — category-based word lists, per-round scoring logic, a live countdown timer for choosing a word, and an automatic round/victory flow.
- **Server-rendered, hypermedia-driven UI** — no SPA/JS framework: HTMX swaps in HTML fragments pushed straight from Django, both over regular HTTP and over the WebSocket connection.

## Technologies
 
**Backend**
- [Python](https://www.python.org/) 3.14
- [Django](https://www.djangoproject.com/) 6.0 — web framework, ORM, auth, forms, admin
- [Django Channels](https://channels.readthedocs.io/) — ASGI support & WebSocket consumers for real-time lobbies and notifications
- [SQLite](https://sqlite.org/) — default development database
**Frontend**
- Django Template Language — server-side rendering for full pages and HTMX partials
- [HTMX](https://htmx.org/) 1.9.12 (+ the `ws` extension) — AJAX/WebSocket-driven UI updates without custom JavaScript
- [Bootstrap](https://getbootstrap.com/) 4.4 & Bootstrap Icons — layout and styling
- Small vanilla JS helpers for form UX (`focusInvalidField.js`, `avatarModal.js`, `disableSubmitIfUnchanged.js`)

**Testing & CI**
- Django's built-in `TestCase` test runner
- GitHub Actions
 
## Installation Guide
 
### Prerequisites
 
- **Python 3.14+**
- **pip**
- **Git**
 
### Backend Setup
 
1. **Clone the repository**
```bash
    git clone https://github.com/EduBGou/Fulabra.git
    cd Fulabra
```
 
2. **Create and activate a virtual environment**

Linux/macOS:
```bash
    python -m venv venv
    source venv/bin/activate
```
 
   Windows (PowerShell):
```powershell
    python -m venv venv
    venv\Scripts\Activate.ps1
```
 
3. **Install dependencies**
```bash
    pip install -r requirements.txt
```
 
4. **Apply database migrations**
```bash
    python manage.py migrate
```
 
5. **Create an admin user** 
```bash
    python manage.py createsuperuser
```
(needed for the next step and for the Django admin panel)
 
6. **Seed at least one Category and a few Words** — the game engine reads its word lists from the database, and no fixture is bundled with the project. Log in to `http://127.0.0.1:8000/admin/` after starting the server and create:
   - One or more **Category** entries (e.g. "Professions")
   - Several **Word** entries linked to that category (e.g. "Doctor", "Engineer", "Programmer"...)
   Without this step, lobbies will start but no words will be available to submit.

7. **Run the development server**
```bash
    python manage.py runserver
```

8. Open **http://127.0.0.1:8000/** in your browser.

### Frontend Configuration
 
Fulabra doesn't have a separate frontend build step, package.json, or bundler — the UI is server-rendered Django templates progressively enhanced with HTMX. Bootstrap, Bootstrap Icons, and HTMX are loaded via CDN `<link>`/`<script>` tags in `fulabra_app/templates/fulabra_app/layout.html`, and app-specific CSS/JS live under `fulabra_app/static/fulabra_app/` (collected automatically by Django's `staticfiles` app in development).
 
This means:
- An internet connection is needed the first time the page loads (to fetch the CDN assets), unless you vendor those files locally.
- There is nothing extra to install or compile beyond the Python dependencies above — once `runserver` is up, the frontend is ready.

### Making Changes

If you are modifying the codebase and your new features involve altering the database schema (e.g., changing models in `models.py`), you must generate and apply new migrations before running the server or tests:

```bash
    python manage.py makemigrations
    python manage.py migrate
```

## Running the Tests
 
The automated test suite lives in [fulabra_app/tests.py](fulabra_app/tests.py) and ensures the stability of the application's core workflows. It includes:

- **Unit Tests:** Validates the game's strict scoring rules (zero, partial, and full matches) and enforces the 3-player maximum lobby capacity limits.
- **Integration Tests:** Ensures guest player profiles are correctly generated, stored in the active session, and seamlessly redirected.
- **End-to-End (E2E) Tests:** Simulates the complete journey of an authenticated user creating a lobby, following redirects, and successfully loading the room interface.

With your virtual environment activated, run the full suite using:
 
```bash
    python manage.py test fulabra_app
```
 
This is the exact command executed by the CI pipeline on every push (see [CI/CD](#cicd) below).
 
## Design Patterns
 
### Strategy Pattern — Notification Handling
 
**Where:** [fulabra_app/services/notification_strategy.py](fulabra_app/services/notification_strategy.py), consumed from `notification_action_view` in `views.py`.
 
**The problem it solves:** a user's inbox can contain different *kinds* of notifications — currently `friend_request` and `game_invite` — and accepting or rejecting each one triggers completely different business logic. Handling this with a growing `if notification.notification_type == "..." elif ...` chain directly inside the view would quickly make `views.py` harder to read and to extend safely.
 
**How it's implemented:**
- `NotificationStrategy` is an abstract base class defining a single `handle(request, notification, action)` method.
- `FriendRequestStrategy` and `GameInviteStrategy` each implement that method with the logic specific to their notification type (e.g. `FriendRequestStrategy` links the two users as friends on `"accept"`; `GameInviteStrategy` returns an HTMX redirect into the lobby on `"accept"`, or notifies the original sender to re-enable their "invite" button on `"reject"`).
- A `_STRATEGIES` dictionary maps each `notification_type` string to its corresponding strategy instance.
- `NotificationContext` is the single entry point the view talks to: given a `Notification`, it looks up the right strategy from `_STRATEGIES`, marks the notification as read, and delegates the actual `accept`/`reject` handling to `strategy.handle(...)`.

**Why it was introduced:** it keeps `notification_action_view` a thin, generic controller regardless of how many notification types exist. Adding a new notification type in the future (e.g. tournament invite) only requires writing a new `NotificationStrategy` subclass and registering it in `_STRATEGIES` — the view, the URL, and every other existing strategy stay untouched. This follows the Open/Closed Principle and keeps type-specific business rules encapsulated and independently testable.
 
## CI/CD
 
Continuous Integration is configured via GitHub Actions in [`.github/workflows/testing.yml`](.github/workflows/testing.yml).
 
- **Trigger:** every `push` to the repository.
- **Steps:**
  1. Check out the repository (`actions/checkout`).
  2. Set up Python 3.14.3 (`actions/setup-python`).
  3. Install dependencies from `requirements.txt`.
  4. Run the automated test suite with `python manage.py test fulabra_app`.
This gives a fast, consistent signal that the game logic, forms, and lobby flows haven't regressed before code is merged. There is currently no deployment (CD) stage configured — the pipeline covers testing only.

## Authors
 
Fulabra is developed and maintained by:
 
- **Eduardo Boaro Gouveia** — [@EduBGou](https://github.com/EduBGou)
- **Vinicius Herberts Dal Bem** — [@vininnn](https://github.com/vininnn)

## License
 
This project is licensed under the terms of the **MIT License** — see [`LICENSE`](LICENSE) for details.
 