# Tomate

MVP Pomodoro mono-utilisateur (Vue 3 + FastAPI + SQLite) avec timer, tasks, cartes de pause et timelines.

## Demarrage (dev)

Prerequis: podman + podman compose.

```bash
podman compose --profile dev up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000

## Backup SQLite

La base est dans un volume `tomate_data` sous `/data/app.db`.

Option simple:

```bash
podman volume inspect tomate_data
```

Puis copier le fichier `app.db` depuis le chemin `Mountpoint`.

Ou via un conteneur temporaire:

```bash
podman run --rm -v tomate_data:/data -v $PWD:/backup alpine cp /data/app.db /backup/tomate.db
```

## Structure

- `backend/` FastAPI + SQLite
- `frontend/` Vue 3 + Vite
- `compose.yml` profils dev
- `TODO.md` idee evolutions
