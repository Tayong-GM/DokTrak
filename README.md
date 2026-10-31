# Soft UI Dashboard (Django)

Internal dashboard built on Django 4.2 and the Soft UI Dashboard (Bootstrap 5) theme.

## Requirements

- Python 3.10+
- pip / virtualenv

## Setup

```bash
python -m venv env
source env/bin/activate        # Windows: env\Scripts\activate
pip install -r requirements.txt

cp env.sample .env             # then set SECRET_KEY and DEBUG
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The app runs at http://127.0.0.1:8000/.

## Configuration

Settings are read from `.env`:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key. Set a strong value. |
| `DEBUG` | `True` for development, `False` for production. |
| `DB_ENGINE`, `DB_NAME`, `DB_USERNAME`, `DB_PASS`, `DB_HOST`, `DB_PORT` | Optional. SQLite is used if these are not set. |

## Pages

| URL | Description |
|---|---|
| `/` | Dashboard |
| `/tables/` | Tables |
| `/billing/` | Billing |
| `/profile/` | Profile |
| `/virtual-reality/` | Virtual reality demo |
| `/rtl/` | RTL layout demo |
| `/charts/` | Charts built from the `Product` model |
| `/dynamic-dt/` | Dynamic data tables (models listed in `DYNAMIC_DATATB`) |
| `/api/` | Dynamic REST API (models listed in `DYNAMIC_API`) |
| `/admin/` | Django admin |

Login, logout, and registration pages come from the `django-admin-soft-dashboard` package.

## Codebase structure

```
< PROJECT ROOT >
 |
 |-- config/                       # Project configuration
 |    |-- settings.py              # Settings (apps, DB, static, DYNAMIC_DATATB / DYNAMIC_API)
 |    |-- urls.py                  # Root routing
 |    |-- wsgi.py / asgi.py        # Server entry points
 |
 |-- apps/
 |    |-- pages/                   # Dashboard and theme pages
 |    |    |-- models.py           # Product model
 |    |    |-- views.py            # index, tables, billing, vr, rtl, profile
 |    |    |-- urls.py             # Page routes
 |    |
 |    |-- charts/                  # Charts page (reads Product data)
 |    |-- dyn_dt/                  # Dynamic data tables (filters, CSV export, CRUD)
 |    |-- dyn_api/                 # Dynamic REST API
 |
 |-- templates/
 |    |-- layouts/
 |    |    |-- base.html           # Base layout every page extends
 |    |-- includes/
 |    |    |-- sidebar.html        # Left navigation
 |    |    |-- navigation.html     # Top navbar
 |    |    |-- footer.html
 |    |    |-- fixed-plugin.html   # Theme settings panel
 |    |-- pages/                   # index (dashboard), tables, billing, profile, rtl, virtual-reality
 |    |-- charts/                  # Charts page template
 |    |-- dyn_dt/                  # Dynamic table templates
 |    |-- dyn_api/                 # Dynamic API index template
 |
 |-- static/
 |    |-- assets/
 |    |    |-- css/                # Theme CSS, Nucleo icons
 |    |    |-- js/                 # Theme JS (core/, plugins/)
 |    |    |-- fonts/              # Nucleo icon fonts
 |    |    |-- img/                # Images, logos, illustrations
 |    |-- scss/                    # Theme SCSS source
 |
 |-- cli/                          # Project CLI helpers (git, env, dependencies)
 |-- nginx/                        # Nginx config for Docker
 |
 |-- manage.py                     # Django entry point
 |-- requirements.txt              # Python dependencies
 |-- env.sample                    # Example environment file (copy to .env)
 |-- gulpfile.js, package.json     # SCSS compilation (gulp)
 |-- Dockerfile, docker-compose.yml, gunicorn-cfg.py
 |-- render.yaml, build.sh         # Render deployment
 |-- db.sqlite3                    # Default SQLite database
```

## Adding a page

1. Create `templates/pages/<name>.html` that starts with `{% extends 'layouts/base.html' %}` and fills `{% block content %}`.
2. Add a view in `apps/pages/views.py` and pass `{'segment': '<name>'}` in the context.
3. Add a route in `apps/pages/urls.py`.
4. Add a sidebar link in `templates/includes/sidebar.html`.

Page-specific scripts go in `{% block extra_js %}`.

## Adding a model to the dynamic table or API

Register it in `config/settings.py`:

```python
DYNAMIC_DATATB = {'product': 'apps.pages.models.Product'}
DYNAMIC_API    = {'product': 'apps.pages.models.Product'}
```

## Deployment

- **Docker:** `docker-compose up --build` (see `Dockerfile` and `docker-compose.yml`).
- **Render:** `render.yaml` and `build.sh` are included.
- Before deploying, set `DEBUG=False` and a strong `SECRET_KEY`.

## Credits

Based on Soft UI Dashboard by [Creative Tim](https://www.creative-tim.com/) and the Django starter by [App-Generator](https://app-generator.dev/). See `LICENSE.md` for license terms.
