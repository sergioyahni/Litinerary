## Start the backend

-Open a terminal at the repository root:

```cmd
    cd backend
    ..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Keep this terminal open.
- Then check in your browser:

```text
http://localhost:8000/api/health
http://localhost:8000/api/readiness
```
- Both should return healthy/readiness JSON.

## Start the frontend

- Open a second terminal at the repository root:
```cmd
    cd frontend
    npm run dev
```
- It will usually show something like:
```text
    http://localhost:5173/
```

- Open that URL in your browser.