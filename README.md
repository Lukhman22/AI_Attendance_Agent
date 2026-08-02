# 🚀 AI Attendance Agent

> An AI-powered HR Attendance & Payroll Desktop Application built with **FastAPI, React, Tauri, and Python**, designed to automate employee attendance management, payroll generation, AI-powered insights, and HR reporting.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![Tauri](https://img.shields.io/badge/Tauri-Desktop-App-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 📌 Overview

AI Attendance Agent is an intelligent desktop HR management system that automates attendance processing, payroll calculations, reporting, and AI-powered workforce insights.

The application is designed for organizations that use biometric attendance systems and need a modern solution for:

- Attendance Management
- Payroll Processing
- Salary Calculation
- Leave Tracking
- AI HR Insights
- Telegram Notifications
- Executive Reports

The application runs completely as a **native desktop application** using **Tauri**, with a **FastAPI backend** and **React frontend**.

---

# ✨ Features

## 👥 Employee Management

- Add/Edit/Delete Employees
- Employee Salary Management
- Employee Directory
- Attendance Percentage Calculation
- Monthly Attendance Summary

---

## 📅 Attendance Management

- Upload Attendance CSV
- Monthly Attendance Processing
- Daily Attendance Summary
- Attendance Validation
- Unknown Employee Detection
- Attendance Analytics

---

## 💰 Payroll Engine

- Monthly Payroll Generation
- Salary Rules
- Automatic Deductions
- Minimum Working Hours Validation
- Late Arrival Detection
- Leave Deduction Support
- Payroll Reports

---

## 🤖 AI HR Assistant

- Interactive AI Chat
- HR Analytics
- Workforce Insights
- Employee Performance Analysis
- Executive Summaries
- Attendance Trend Analysis
- Organization Analytics

---

## 📊 Reports

Generate:

- Payroll Reports
- Attendance Reports
- HR Executive Reports
- AI Insights Reports

Supported formats:

- PDF
- Excel
- CSV

---

## 🔔 Notifications

Telegram Integration

Supports:

- Daily Attendance Summary
- Monthly Payroll Report
- Executive HR Report
- Attendance Alerts

---

## 🖥 Desktop Application

Cross-platform desktop support

- macOS
- Windows

Built using:

- Tauri
- FastAPI
- React

---

# 🏗 Architecture

```
                 Desktop App (Tauri)
                        │
          ┌─────────────┴─────────────┐
          │                           │
      React Frontend             FastAPI Backend
          │                           │
          │                    Business Logic
          │                           │
          ├───────────────┐───────────┤
                          │
                    SQLite Database
                          │
          ┌───────────────┼────────────────┐
          │               │                │
      Attendance      Payroll        AI Insights
```

---

# 🛠 Tech Stack

### Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- APScheduler
- Pydantic

### Frontend

- React
- TypeScript
- Vite
- TailwindCSS

### Desktop

- Tauri v2
- Rust

### AI

- OpenAI API (optional)
- AI Insights Engine
- Prompt Engineering

### Database

- SQLite

### Notifications

- Telegram Bot API

---

# 📂 Project Structure

```
backend/
    app/
        ai/
        api/
        attendance/
        payroll/
        notifications/
        services/
        database/

frontend/
    src/
    src-tauri/

docs/

tests/

reports/

uploads/
```

---

# ⚙ Installation

## Clone Repository

```bash
git clone https://github.com/Lukhman22/AI_Attendance_Agent.git

cd AI_Attendance_Agent
```

---

## Backend

```bash
python -m venv venv

source venv/bin/activate      # macOS/Linux

venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Frontend

```bash
cd frontend

npm install
```

---

## Run Development

Backend

```bash
uvicorn backend.app.main:app --reload
```

Frontend

```bash
npm run dev
```

Desktop

```bash
npm run tauri dev
```

---

# 📦 Build Desktop Application

## macOS

```bash
python build.py
```

Produces:

```
dist/
    AI Attendance Agent.dmg
```

---

## Windows

```bash
python build.py
```

Produces

```
dist/

AI Attendance Agent Setup.exe
```

---

# 🚀 Usage

1. Launch AI Attendance Agent
2. Configure Telegram (optional)
3. Upload Employee Attendance CSV
4. Import Salary Data
5. Generate Payroll
6. Review AI Insights
7. Export Reports
8. Send Telegram Notifications

---

# 🔒 Security

This repository has undergone a full security audit.

✔ No API Keys committed

✔ No Secrets in Git History

✔ Environment Variables excluded

✔ Gitleaks Verified

✔ Production Ready

---

# 📈 Future Improvements

- Email Notifications
- WhatsApp Notifications
- Multi-Company Support
- Role-Based Authentication
- Cloud Synchronization
- Leave Management Portal
- Employee Self-Service Portal
- Dashboard Charts
- Mobile Companion App

---

# 🤝 Contributing

Contributions are welcome.

Feel free to open an Issue or submit a Pull Request.

---

# 📜 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Mohammed Lukhmaan**

GitHub:

https://github.com/Lukhman22

---

## ⭐ If you found this project useful, consider giving it a Star!