# SkillSwap

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-Database-orange.svg)](https://www.mysql.com/)
[![Deployment](https://img.shields.io/badge/Status-Live-success.svg)]()

## Abstract
SkillSwap is a peer-to-peer web platform designed for college students to exchange skills without financial transactions. While traditional e-learning is one-directional and often costly, SkillSwap facilitates a reciprocal learning economy where students teach to earn "credits" and spend them to learn from others.

Built using Flask and MySQL, the platform features a smart matchmaking algorithm that uses bitwise operations to pair users based on skill compatibility, proficiency, and schedule overlap. To ensure security and fairness, the system incorporates Bcrypt authentication, OTP verification, and an escrow-based credit ledger that prevents fraud by holding credits until a session is confirmed. By combining a gesture-based discovery interface with gamification elements like leaderboards and badges, SkillSwap creates a trusted, engaging, and scalable ecosystem for collaborative education.

---

## Key Features

- **Gesture-Based Discovery Interface:** Discover other students and their educational offerings through an engaging, intuitive swipe-to-match UI designed for quick connections.
- **Collaborative Education Economy:** A fully functional virtual credit system designed specifically for students. Teach a subject to earn credits, and spend those credits to be tutored by peers in other disciplines.
- **Advanced Matchmaking AI:** Calculates compatibility using a dynamic 50-point base system, factoring in mutual exchange requests, skill level gaps, logistics, and bitmask-based schedule overlapping for high-performance query execution.
- **Escrowed Virtual Ledger:** Incorporates an immutable double-entry ledger system where users trade credits to book educational sessions, mitigating spam and enforcing academic accountability.
- **Premium Responsive UI/UX:** Built with a custom, mobile-first design system featuring fluid layouts, interactive micro-animations, glassmorphism elements, and modern typography—achieved entirely without external CSS frameworks.
- **Robust Security Architecture:** Implements bcrypt password hashing, real-time OTP email verification via SMTP, secure environment variable configuration, and strict account lockout mechanisms (15-minute lockouts after 3 failed attempts) to protect against brute-force attacks.
- **Dynamic ID & Notification Systems:** Features custom, readable unique ID generation (e.g., `USR-STU-2024-00001`) alongside a global context-processed real-time notification engine.
- **Comprehensive Admin Dashboard:** Powerful analytics and moderation tooling to review academic certificates, manage tutoring sessions, and oversee credit transactions.

---

## Technology Stack

- **Backend:** Python, Flask, Jinja2
- **Database:** MySQL (Flask-MySQLdb)
- **Authentication:** Flask-Bcrypt, Flask-Mail (OTP Verifications)
- **Frontend:** Vanilla HTML/CSS/JS, Lucide Icons

---

## Local Development Setup

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

## Deployment (Production)

SkillSwap is fully configured for cloud deployments using Railway. 
- **Application & Database:** You can host both the web service and the MySQL database within the same Railway project for fast, internal networking.
- **Environment Variables:** Define all variables listed in the `.env` step directly within your Railway project's variables panel to keep secrets out of the codebase.

---

## Contact & Support

For inquiries, support, or further information regarding the SkillSwap project, please contact:
- **Email:** [skillswap050@gmail.com](mailto:skillswap050@gmail.com)

---
*© 2026 SkillSwap. All rights reserved.*
