@echo off
title SKML Mobiles POS Server
cd /d "%~dp0"
echo Starting SKML Mobiles POS & Inventory System Server...
echo The application will be accessible at http://127.0.0.1:5001/
echo Do not close this window while using the application.
echo -------------------------------------------------------------
python app.py
pause
