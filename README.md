# Installation Instructions

```powershell
python3 -m venv venv
venv\Scripts\Activate.ps1
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

After setup, you can visit `http://localhost:8000/wallets/`
