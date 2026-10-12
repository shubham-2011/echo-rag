# Run EcoRAG on Windows

## Start the backend

Open PowerShell in the repository folder. Configure the API key first (the command below saves it for future terminals and sets it in this one):

```powershell
$key = python -c "import secrets; print(secrets.token_urlsafe(32))"
setx ECORAG_API_KEY $key
$env:ECORAG_API_KEY = $key
```

Start FastAPI from the backend directory. On this machine, the tested Python executable is `C:\Python314\python.exe`:

```powershell
Set-Location .\backend
C:\Python314\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Keep this terminal open while using the API. The local-only bind (`127.0.0.1`) avoids exposing the development server to other machines.

Search, query, and ingestion require a bearer API key. Set the key **before starting the backend**. `setx` persists it for newly opened terminals; `$env:ECORAG_API_KEY` sets it in the current terminal. If the server is already running, stop and restart it after configuring the key. Do not commit or share the key.

## Check that it is running

In another PowerShell terminal:

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

Expected response includes `"status":"healthy"`. Interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

To test a protected endpoint:

```powershell
$headers = @{ Authorization = "Bearer $env:ECORAG_API_KEY" }
$body = @{ query = "What is EcoRAG?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/search -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Stop the backend

Press **Ctrl+C** in the terminal running Uvicorn.

## Docker alternative

Configure `ECORAG_API_KEY` in the repository-root `.env` file, then from the repository root run:

```powershell
docker compose up --build
```
