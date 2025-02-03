@echo off
REM Run the PowerShell script with ExecutionPolicy Bypass
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0Setup-Environment.ps1'"