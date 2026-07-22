# AI Attendance Agent - Project Context

## Project Overview

### Project Name
AI Attendance Agent (HR Middleware)

### Purpose
The AI Attendance Agent is an HR Middleware application that integrates with an organization's existing biometric attendance system.

The company already has:

- Biometric fingerprint attendance machines
- HRMS / Attendance Management Software
- Employee Database
- Payroll Process

This project DOES NOT replace the company's software.

Instead, it acts as an intelligent middleware layer that:

- Imports attendance exports (CSV / XLS / XLSX)
- Normalizes attendance data
- Calculates employee attendance
- Calculates payroll based on configurable HR rules
- Generates reports
- Produces AI-powered HR insights
- Sends employer notifications through Telegram
- Can later integrate directly with the company's APIs without changing the business logic.

---

# Project Goals

The middleware should:

✔ Read attendance exports from the company

✔ Validate attendance records

✔ Store attendance in PostgreSQL

✔ Detect invalid or unknown employees

✔ Calculate working hours

✔ Calculate monthly salary

✔ Apply HR deduction rules

✔ Generate reports

✔ Notify HR

✔ Produce AI insights

✔ Scale later to API integrations instead of manual file uploads.

---

# High Level Architecture

Biometric Machine

↓

Company HR Software

↓

CSV / XLS / XLSX Export

↓

AI Attendance Middleware (Current)

↓

Validation

↓

Parser

↓

Normalization

↓

PostgreSQL Database

↓

Attendance Engine

↓

Payroll Engine

↓

AI Insights Engine

↓

Reports

↓

Notifications

↓

Employer Dashboard

Future Architecture:

Company HR Software

↓

REST API / Webhook

↓

AI Attendance Middleware

↓

Everything else remains exactly the same.

---

# Technology Stack

## Backend

Python 3.14

FastAPI

SQLAlchemy

Alembic

PostgreSQL

Pydantic

Pandas

OpenPyXL

xlrd

ReportLab

Uvicorn

Pytest

Dependency Injection

Repository Pattern

Service Layer

---

## Frontend

React 18

TypeScript

Vite

Tailwind CSS

Axios

React Context

React Router

Recharts

---

## Database

PostgreSQL

Managed using Alembic migrations.

---

## Notifications

Telegram Bot API

---

## AI

Currently deterministic AI.

No LLM is required for attendance calculations.

AI modules generate:

- HR Insights
- Executive Summary
- Smart Alerts
- Recommendations

Future versions may optionally integrate:

- Gemini
- OpenAI
- Ollama

for natural language explanations only.

Attendance calculations must ALWAYS remain deterministic.

---

# Folder Structure

AI_Attendance_Agent/

backend/

app/

api/

attendance/

payroll/

notifications/

ai/

database/

middleware/

models/

schemas/

services/

utils/

frontend/

src/

components/

pages/

services/

context/

utils/

sample_data/

tests/

docs/

reports/

uploads/

---

# Backend Architecture

The backend follows a layered architecture.

Client

↓

API Router

↓

Service Layer

↓

Repository Layer

↓

Database

Business logic MUST stay inside Services.

API endpoints should remain lightweight.

Repositories should handle database operations.

Business rules must never be duplicated.

---

# Frontend Architecture

React SPA

↓

Pages

↓

Reusable Components

↓

API Services

↓

FastAPI Backend

The frontend should NEVER calculate payroll.

All calculations happen in the backend.

The frontend only displays backend results.

---

# Database Schema

Main tables:

Employee

Attendance

Payroll

SalaryRule

IgnoredAttendance

AiDailyInsight

AiMonthlyInsight

SmartAlert

ExecutiveSummary

AiRecommendation

Relationships:

Employee

↓

Attendance

↓

Payroll

↓

Reports

SalaryRule controls all payroll calculations.

---

# Attendance Flow

User uploads:

CSV

XLS

XLSX

↓

System detects format from file content

↓

Parser selected automatically

↓

Normalize data

↓

Validate records

↓

Unknown Employee?

YES

↓

Store inside IgnoredAttendance

Generate warning

NO

↓

Store attendance

↓

Calculate working hours

↓

Update dashboard

---

# Supported Upload Formats

CSV

XLS

XLSX

The parser should detect file format using file signatures (magic bytes), not only extensions.

Extension is only a fallback.

PDF is NOT an upload format.

---

# Payroll Rules (Current)

Current assumptions:

Working Days Per Month = 26

Minimum Working Hours = 8

Maximum Payable Hours = 8

Overtime = Not Paid

Hourly Rate

Monthly Salary / 26 / 8

Daily Salary

Monthly Salary / 26

Rules:

If Work Hours >= 8

Deduction = 0

If Work Hours < 8

Missing Hours

=

8

-

Worked Hours

Deduction

=

Missing Hours

×

Hourly Rate

If Absent

Deduction

=

Daily Salary

Final Salary

=

Monthly Salary

-

Total Deductions

These rules MUST remain configurable.

Never hardcode HR rules.

---

# Notification Flow

Current:

Manual trigger

↓

Generate summary

↓

Telegram

Future:

Automatic Scheduler

↓

End of Day

↓

Generate Summary

↓

Telegram Backup

Notification content:

Present employees

Absent employees

Late employees

Missing checkout

Payroll summary

Important AI alerts

---

# AI Insights

Current AI features:

Daily insights

Monthly insights

Executive summary

Recommendations

Smart alerts

Unknown employee detection

Attendance anomalies

AI is rule-based.

No attendance calculations should ever depend on LLM reasoning.

---

# Current Completed Features

✔ PostgreSQL integration

✔ Alembic migrations

✔ Attendance upload

✔ CSV parser

✔ XLS parser

✔ XLSX parser

✔ Automatic format detection

✔ Unknown employee detection

✔ Attendance dashboard

✔ Employee management

✔ Payroll engine

✔ Salary deduction

✔ AI Insights

✔ Reports

✔ Notifications module

✔ REST APIs

✔ React frontend

✔ Dark/Light mode

✔ Test suite

✔ GitHub repository

---

# Pending Features

Priority 1

- Company API integration
- Employee Master synchronization
- Real HR salary rules
- Configurable payroll settings
- Automatic scheduled notifications
- HR Settings page
- Dynamic salary rule editor

Priority 2

- Telegram fallback
- Email notifications
- Leave management
- Holiday calendar
- Overtime configuration
- Late coming rules
- Early logout rules

Priority 3

- HR analytics dashboard
- Trend analysis
- Department analytics
- Employee performance reports
- AI chatbot (optional)

---

# Coding Conventions

Always follow these rules.

Business logic belongs inside Services.

Repositories only access the database.

API endpoints remain lightweight.

Never duplicate payroll calculations.

Never hardcode salary values.

Everything configurable belongs in SalaryRule.

Always write unit tests.

Maintain backward compatibility.

Never break API contracts.

Use meaningful variable names.

Prefer composition over duplication.

Keep code modular.

---

# Future Roadmap

Phase 1 ✅

Attendance Upload

Payroll

Reports

Dashboard

AI Insights

Notifications

Phase 2

Real Company Deployment

Employee Master Sync

Company API Integration

Real Salary Rules

Automatic Scheduler

Phase 3

HR Portal

Analytics

Advanced AI Insights

Predictive Attendance

Leave Forecasting

Performance Analytics

---

# Important Project Constraints

The company already owns the Employee Database.

The middleware should synchronize with the existing company system.

Employees should NOT be manually created unless specifically required.

Attendance data comes from company exports or APIs.

The middleware must adapt to company rules, not force its own rules.

Every payroll rule must be configurable.

All attendance calculations must remain deterministic.

Future AI models should explain results, not calculate salaries.

---

# Development Philosophy

This project is intended to become production-ready HR middleware.

Primary goals:

Reliability

Scalability

Maintainability

Configurability

Clear architecture

Future integrations

Every new feature should fit into the existing architecture instead of introducing shortcuts or duplicate logic.
