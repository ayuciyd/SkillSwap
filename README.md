# SkillSwap

SkillSwap is a secure, server-side rendered, peer-to-peer skill exchange platform built with Python (Flask) and MySQL. Designed to facilitate high-quality knowledge sharing, the platform matches users who want to learn a skill with those who want to teach it.

Unlike standard platforms, SkillSwap acts as a complete ecosystem built without heavy UI frameworks, relying on highly optimized SQL and vanilla styling to achieve a modern, cohesive aesthetic.

## Key Technical Highlights

- **Advanced Matchmaking Algorithm:** Calculates compatibility using a dynamic 50-point base system, factoring in mutual exchange requests, skill level gaps, logistics, and bitmask-based schedule overlapping for high-performance query execution.
- **Escrowed Virtual Economy:** Incorporates an immutable double-entry ledger system where users trade credits to book sessions, mitigating spam and enforcing platform accountability.
- **Robust Security Architecture:** Implements bcrypt password hashing, real-time OTP email verification via SMTP, and strict account lockout mechanisms (15-minute lockouts after 3 failed attempts) to protect against brute-force attacks.
- **Dynamic ID & Notification Systems:** Features custom, readable unique ID generation (e.g., `USR-STU-2024-00001`) alongside a global context-processed real-time notification engine.
- **Optimized Frontend Stack:** Utilizes responsive, zero-framework Vanilla CSS/JS and Jinja2 templates, prioritizing performance, accessibility, and an engaging user experience logic.

## Features

- Custom User and Session Roles (Students, Admins)
- Email OTP Verification Workflow
- Session Scheduling with Real-Time Validation
- Virtual Credit System (10 credits on sign-up; escrow system with automated refunds)
- Gamified Achievements and Dynamic Profile Badges
- Fully Featured Admin Dashboard with analytics and moderation tooling

## Prerequisites

- Python 3.10+
- MySQL Server

## Setup Instructions

1. **Clone or Navigate to the Project:**
   ```bash
   cd SkillSwap
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database:**
   Ensure your MySQL server is running and accessible. Load the database schema:
   ```bash
   mysql -u root < schema.sql
   ```
   *(If your MySQL configuration requires a password, append the `-p` flag).*

4. **Launch the Application:**
   ```bash
   python app.py
   ```

5. **Access the Platform:**
   Open your browser and navigate to `http://127.0.0.1:5000/`.

## Author & Contact

For inquiries, support, or further information regarding the SkillSwap project, please contact:
**Email:** skillswap050@gmail.com

## Default Credentials

- **Admin Access:**
  - Email: `admin@skillswap.io`
  - Password: `Admin@123`
