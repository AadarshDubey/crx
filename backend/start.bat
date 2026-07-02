@echo off
set PYTHONPATH=C:\pylibs
python -m uvicorn app.main:app --reload
