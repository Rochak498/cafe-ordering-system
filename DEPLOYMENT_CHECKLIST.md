# Deployment Checklist

## Before pushing
- [ ] Remove `.venv/` from the repository
- [ ] Remove `database.db` from the repository
- [ ] Commit `.gitignore`
- [ ] Confirm `requirements.txt` is UTF-8

## Render settings
- [ ] Use the included `render.yaml`
- [ ] Keep the service on a paid plan (`starter` or above) because SQLite needs a persistent disk
- [ ] Attach the persistent disk at `/opt/render/project/src/data`
- [ ] Set `DATABASE_PATH=/opt/render/project/src/data/database.db`
- [ ] Let Render generate `SECRET_KEY`
- [ ] Keep `FLASK_DEBUG=0`
- [ ] Confirm `/health` returns `{ "status": "ok" }`

## After first deploy
- [ ] Log in with the seeded admin or staff account
- [ ] Place a test order
- [ ] Confirm the dashboard loads
- [ ] Restart the service and confirm the order still exists
- [ ] Change demo passwords if this will be publicly shared
