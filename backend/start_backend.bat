@echo off
call C:\Users\Howard\anaconda3\Scripts\activate.bat ML
cd /d "%~dp0"
uvicorn main:app --reload
