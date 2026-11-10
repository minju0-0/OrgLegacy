# OrgLegacy — Vertically Sliced

This project has been restructured to follow the CSIT327 vertical-slicing
guide, and the UI has been redesigned across every screen.

## What changed

**1. Login and Register were split into separate apps.**
The old `authentication` app mixed two features together. It is now:

- `apps/login/` — the login screen, log-out, and nothing else.
- `apps/register/` — the registration screen and its form, and nothing else.
- `apps/accounts/` — a small **shared** app holding the `Profile` model.
  It isn't a screen a user visits; it exists because `register`, `profile`,
  and `settings` all need to read/write `Profile`, and the guide's rule is
  that features shouldn't import each other directly. Putting the shared
  model in its own small app (rather than inside `login` or `register`)
  keeps that rule intact.

**2. Every feature is its own vertical slice**, per the guide's target
structure:

```
orgleg/
├── manage.py
├── requirements.txt
├── .env.example
├── apps/
│   ├── login/
│   ├── register/
│   ├── accounts/        (shared Profile model)
│   ├── home/
│   ├── profile/
│   └── settings/
├── templates/
│   ├── base.html
│   ├── partials/_navbar.html
│   ├── login/login.html
│   ├── register/register.html
│   ├── home/home.html
│   ├── profile/profile.html
│   └── settings/settings.html
├── static/
│   ├── css/
│   │   ├── shared/base.css      (design tokens, resets, shared components)
│   │   ├── login/login.css
│   │   ├── register/register.css
│   │   ├── home/home.css
│   │   ├── profile/profile.css
│   │   └── settings/settings.css
│   ├── js/
│   │   ├── shared/base.js       (toast + login<->register slide transition)
│   │   ├── profile/profile.js
│   │   └── settings/settings.js
│   └── images/shared/handover-table.jpg
└── config/
    ├── settings.py
    ├── urls.py
    ├── asgi.py
    └── wsgi.py
```

Only genuinely cross-cutting code lives under a `shared/` folder — the
design tokens/resets, the toast helper, the login↔register slide
animation, and the hero photo used by both auth screens. Everything else
(HTML, CSS, JS, views, forms) belongs to exactly one feature.

**3. The UI was redesigned** on every screen, keeping the "warm archival
paper" identity but refreshing the layout:

- **Navbar** — icon nav pills and a user-initial avatar chip.
- **Login / Register** — refined split-hero layout with a status badge
  and a rounded photo panel.
- **Home** — now a real dashboard: a welcome banner, quick links to
  Profile/Settings, and a grid previewing the feature slices planned
  next (Event Logger, Supplier Directory, Handover Notes, Adviser
  Sign-off) — each of which will become its own vertical slice/app.
- **Profile** — a two-column layout: an identity summary card next to
  the editable details form, with a round avatar.
- **Settings** — password change and the danger zone are now separated
  into distinct cards, with a clearer danger-zone treatment.

All existing view/form logic (login, registration, profile editing,
password change, account deletion) is unchanged — only where the code
lives and how the pages look.

## Running it

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env             # set SECRET_KEY; DATABASE_URL already points at a local SQLite file
python manage.py check
python manage.py migrate         # applies accounts 0001, 0002, 0003. Do not run makemigrations or delete them.
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/ . Register an account, then on Home create an organization.

**Start from an empty database.** This project ships migrations (`apps/accounts/migrations/0001` to `0003`).
If you ran an older copy of OrgLegacy before, its tables will not match: delete the old `db.sqlite3`, or point
`DATABASE_URL` at a new empty Postgres/Supabase database, then run `migrate`.

Run the tests with `python manage.py test` (about 115 tests; they use a temporary database).
