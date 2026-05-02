# 🚀 SkillSwap

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-Database-orange.svg)](https://www.mysql.com/)
[![Deployment](https://img.shields.io/badge/Status-Live-success.svg)]()

**SkillSwap** is a secure, server-side rendered, peer-to-peer skill exchange platform. Designed to facilitate high-quality knowledge sharing, the platform matches university students who want to learn a skill with those who want to teach it.

Unlike standard platforms, SkillSwap acts as a complete ecosystem built without heavy UI frameworks, relying on highly optimized SQL and vanilla styling to achieve a modern, cohesive, and premium aesthetic.

---

## ✨ Key Features

- **Tinder-Style Swipe Interface:** Discover other students and their skills through an engaging, intuitive swipe-to-match UI.
- **Advanced Matchmaking AI:** Calculates compatibility using a dynamic 50-point base system, factoring in mutual exchange requests, skill level gaps, logistics, and bitmask-based schedule overlapping for high-performance query execution.
- **Escrowed Virtual Economy:** Incorporates an immutable double-entry ledger system where users trade credits to book sessions, mitigating spam and enforcing platform accountability.
- **Premium Responsive UI/UX:** Built with a custom, mobile-first design system featuring fluid layouts, interactive micro-animations, glassmorphism elements, and modern typography—all achieved with zero external CSS frameworks.
- **Robust Security Architecture:** Implements bcrypt password hashing, real-time OTP email verification via SMTP, secure environment variable configuration, and strict account lockout mechanisms (15-minute lockouts after 3 failed attempts) to protect against brute-force attacks.
- **Dynamic ID & Notification Systems:** Features custom, readable unique ID generation (e.g., `USR-STU-2024-00001`) alongside a global context-processed real-time notification engine.
- **Comprehensive Admin Dashboard:** Powerful analytics and moderation tooling to review certificates, manage sessions, and oversee transactions.

---

## 🛠️ Technology Stack

- **Backend:** Python, Flask, Jinja2
- **Database:** MySQL (Flask-MySQLdb)
- **Authentication:** Flask-Bcrypt, Flask-Mail (OTP Verifications)
- **Frontend:** Vanilla HTML/CSS/JS, Lucide Icons

---

## ⚙️ Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ayuciyd/SkillSwap.git
cd SkillSwap
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and configure your secrets securely. **Do not commit this file to version control.**
```env
SECRET_KEY=your_secure_secret_key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_local_mysql_password
MYSQL_DB=skillswap_db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=skillswap050@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=skillswap050@gmail.com
```

### 4. Initialize Database
Ensure your MySQL server is running. Load the database schema and default configuration:
```bash
mysql -u root -p < schema.sql
```

### 5. Launch the Application
Start the Flask development server:
```bash
python app.py
```
Access the platform at `http://127.0.0.1:5001/` (or the port specified in your console).

---

## 🚀 Deployment (Production)

SkillSwap is fully configured for cloud deployments (e.g., Render, Heroku). 
- **Database:** Use a managed MySQL database (like Railway).
- **Environment Variables:** Define all variables listed in the `.env` step directly within your hosting provider's dashboard to keep secrets out of the codebase.

---

## 📬 Contact & Support

For inquiries, support, or further information regarding the SkillSwap project, please contact:
- **Email:** [skillswap050@gmail.com](mailto:skillswap050@gmail.com)

---
*© 2026 SkillSwap. All rights reserved.*
