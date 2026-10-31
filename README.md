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

## Project structure

```
config/              Django settings and root URLs
apps/
  pages/             Dashboard and theme pages, Product model
  charts/            Charts page
  dyn_dt/            Dynamic data tables
  dyn_api/           Dynamic API
templates/
  layouts/base.html  Base layout all pages extend
  includes/          Sidebar, navbar, footer, settings panel
  pages/             Dashboard, tables, billing, profile, rtl, virtual-reality
static/
  assets/            Theme CSS, JS, fonts, images
  scss/              Theme SCSS source (compile with gulp)
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
