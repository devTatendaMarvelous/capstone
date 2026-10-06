# SmartCrop frontend

React, Vite, and Tailwind interface for the maize yield API.

## Setup

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://127.0.0.1:8000`. Start the Django server first.

```bash
npm test
npm run build
```

Sign in with an account from `python manage.py seed_demo`. Public registration creates a farmer account only.
