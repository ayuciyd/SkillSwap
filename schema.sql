CREATE DATABASE IF NOT EXISTS skillswap_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE skillswap_db;

-- USERS
CREATE TABLE users (
  id                VARCHAR(25)  PRIMARY KEY,
  full_name         VARCHAR(120) NOT NULL,
  username          VARCHAR(40)  NOT NULL UNIQUE,
  email             VARCHAR(180) NOT NULL UNIQUE,
  password_hash     VARCHAR(255) NOT NULL,
  role              ENUM('student','admin') NOT NULL DEFAULT 'student',
  credits_balance   INT          NOT NULL DEFAULT 10,
  credits_earned    INT          NOT NULL DEFAULT 0,
  credits_spent     INT          NOT NULL DEFAULT 0,
  bio               TEXT,
  university        VARCHAR(150),
  year_of_study     TINYINT,
  is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
  is_verified       BOOLEAN      NOT NULL DEFAULT FALSE,
  failed_login_attempts TINYINT  NOT NULL DEFAULT 0,
  locked_until      TIMESTAMP    NULL,
  last_login_at     TIMESTAMP    NULL,
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email),
  INDEX idx_users_role  (role)
) ENGINE=InnoDB;

-- SKILL CATEGORIES (lookup table)
CREATE TABLE skill_categories (
  id          VARCHAR(10)  PRIMARY KEY,
  name        VARCHAR(80)  NOT NULL UNIQUE,
  code        VARCHAR(5)   NOT NULL UNIQUE,
  icon        VARCHAR(10)  NOT NULL,
  description VARCHAR(255),
  is_active   BOOLEAN      NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

INSERT INTO skill_categories VALUES
  ('CAT-001', 'Programming',  'PRG', 'laptop', 'Coding, web dev, data science', TRUE),
  ('CAT-002', 'Music',        'MUS', 'music', 'Instruments, theory, composition', TRUE),
  ('CAT-003', 'Languages',    'LNG', 'globe', 'Foreign languages, linguistics', TRUE),
  ('CAT-004', 'Mathematics',  'MTH', 'ruler', 'Calculus, statistics, algebra', TRUE),
  ('CAT-005', 'Design',       'DES', 'palette', 'UI/UX, graphic design, Figma', TRUE),
  ('CAT-006', 'Science',      'SCI', 'microscope', 'Physics, chemistry, biology', TRUE),
  ('CAT-007', 'Business',     'BIZ', 'pie-chart', 'Finance, marketing, entrepreneurship', TRUE),
  ('CAT-008', 'Art & Craft',  'ART', 'pencil', 'Drawing, painting, photography', TRUE);

-- SKILLS
CREATE TABLE skills (
  id              VARCHAR(25)  PRIMARY KEY,
  user_id         VARCHAR(25)  NOT NULL,
  category_id     VARCHAR(10)  NOT NULL,
  skill_name      VARCHAR(120) NOT NULL,
  skill_type      ENUM('teach','learn') NOT NULL,
  level           ENUM('beginner','intermediate','advanced') NOT NULL DEFAULT 'intermediate',
  description     TEXT,
  tags            VARCHAR(255),
  available_days  TINYINT UNSIGNED NOT NULL DEFAULT 62,
  preferred_mode  ENUM('online','offline','both') NOT NULL DEFAULT 'both',
  view_count      INT UNSIGNED NOT NULL DEFAULT 0,
  match_count     INT UNSIGNED NOT NULL DEFAULT 0,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES skill_categories(id),
  INDEX idx_skills_user     (user_id),
  INDEX idx_skills_category (category_id),
  INDEX idx_skills_type     (skill_type),
  FULLTEXT idx_skills_search (skill_name, description, tags)
) ENGINE=InnoDB;

-- MATCHES
CREATE TABLE matches (
  id               VARCHAR(20)  PRIMARY KEY,
  teacher_id       VARCHAR(25)  NOT NULL,
  learner_id       VARCHAR(25)  NOT NULL,
  teacher_skill_id VARCHAR(25)  NOT NULL,
  learner_skill_id VARCHAR(25)  NOT NULL,
  match_score      TINYINT UNSIGNED NOT NULL DEFAULT 50,
  is_mutual        BOOLEAN NOT NULL DEFAULT FALSE,
  initiated_by     VARCHAR(25)  NULL,
  status           ENUM('pending','accepted','rejected','expired') NOT NULL DEFAULT 'pending',
  rejected_reason  VARCHAR(255) NULL,
  responded_at     TIMESTAMP    NULL,
  expires_at       TIMESTAMP    NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL 7 DAY),
  created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (teacher_id)       REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (learner_id)       REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_skill_id) REFERENCES skills(id) ON DELETE CASCADE,
  FOREIGN KEY (learner_skill_id) REFERENCES skills(id) ON DELETE CASCADE,
  UNIQUE KEY uq_match_skills (teacher_skill_id, learner_skill_id),
  INDEX idx_matches_teacher (teacher_id),
  INDEX idx_matches_learner (learner_id),
  INDEX idx_matches_status  (status)
) ENGINE=InnoDB;

-- SESSIONS
CREATE TABLE sessions (
  id                VARCHAR(22)  PRIMARY KEY,
  match_id          VARCHAR(20)  NOT NULL,
  teacher_id        VARCHAR(25)  NOT NULL,
  learner_id        VARCHAR(25)  NOT NULL,
  skill_id          VARCHAR(25)  NOT NULL,
  session_date      DATE         NOT NULL,
  session_time      TIME         NOT NULL,
  duration_minutes  TINYINT UNSIGNED NOT NULL DEFAULT 60,
  timezone          VARCHAR(50)  NOT NULL DEFAULT 'Asia/Kolkata',
  mode              ENUM('online','offline') NOT NULL,
  meeting_link      VARCHAR(500) NULL,
  location          VARCHAR(255) NULL,
  credits_cost      TINYINT UNSIGNED NOT NULL DEFAULT 5,
  credits_paid      BOOLEAN NOT NULL DEFAULT FALSE,
  status            ENUM('scheduled','in_progress','completed','cancelled','no_show') NOT NULL DEFAULT 'scheduled',
  cancelled_by      VARCHAR(25)  NULL,
  cancel_reason     VARCHAR(255) NULL,
  cancelled_at      TIMESTAMP    NULL,
  completed_at      TIMESTAMP    NULL,
  session_notes     TEXT         NULL,
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (match_id)   REFERENCES matches(id)  ON DELETE RESTRICT,
  FOREIGN KEY (teacher_id) REFERENCES users(id)    ON DELETE RESTRICT,
  FOREIGN KEY (learner_id) REFERENCES users(id)    ON DELETE RESTRICT,
  FOREIGN KEY (skill_id)   REFERENCES skills(id)   ON DELETE RESTRICT,
  INDEX idx_sessions_teacher (teacher_id),
  INDEX idx_sessions_learner (learner_id),
  INDEX idx_sessions_date    (session_date),
  INDEX idx_sessions_status  (status)
) ENGINE=InnoDB;

-- CREDIT TRANSACTIONS (full audit trail)
CREATE TABLE credit_transactions (
  id              VARCHAR(22)  PRIMARY KEY,
  user_id         VARCHAR(25)  NOT NULL,
  tx_type         ENUM('signup_bonus','session_payment','session_receipt','session_refund','admin_grant','admin_deduct','referral_bonus') NOT NULL,
  amount          SMALLINT     NOT NULL,
  balance_after   INT          NOT NULL,
  session_id      VARCHAR(22)  NULL,
  reference_note  VARCHAR(255) NULL,
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by      VARCHAR(25)  NULL,
  FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE RESTRICT,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
  INDEX idx_txn_user    (user_id),
  INDEX idx_txn_type    (tx_type),
  INDEX idx_txn_created (created_at DESC)
) ENGINE=InnoDB;

-- REVIEWS
CREATE TABLE reviews (
  id              VARCHAR(18)  PRIMARY KEY,
  session_id      VARCHAR(22)  NOT NULL,
  reviewer_id     VARCHAR(25)  NOT NULL,
  reviewee_id     VARCHAR(25)  NOT NULL,
  rating          TINYINT UNSIGNED NOT NULL,
  comment         TEXT,
  tags            VARCHAR(255),
  is_public       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id)  REFERENCES sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (reviewer_id) REFERENCES users(id)    ON DELETE CASCADE,
  FOREIGN KEY (reviewee_id) REFERENCES users(id)    ON DELETE CASCADE,
  UNIQUE KEY uq_review (session_id, reviewer_id),
  INDEX idx_reviews_reviewee (reviewee_id)
) ENGINE=InnoDB;

-- NOTIFICATIONS
CREATE TABLE notifications (
  id          VARCHAR(18)  PRIMARY KEY,
  user_id     VARCHAR(25)  NOT NULL,
  notif_type  ENUM('new_match','match_accepted','match_rejected','session_scheduled','session_reminder','session_completed','session_cancelled','credits_received','new_review','admin_message') NOT NULL,
  title       VARCHAR(150) NOT NULL,
  message     TEXT         NOT NULL,
  action_url  VARCHAR(255) NULL,
  is_read     BOOLEAN NOT NULL DEFAULT FALSE,
  read_at     TIMESTAMP    NULL,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_notif_user    (user_id),
  INDEX idx_notif_read    (is_read),
  INDEX idx_notif_created (created_at DESC)
) ENGINE=InnoDB;

-- SEED: Default admin (password: Admin@123)
INSERT INTO users (id, full_name, username, email, password_hash, role, credits_balance, is_active, is_verified)
VALUES (
  'USR-ADM-2024-00001', 'Platform Admin', 'admin',
  'admin@skillswap.io',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMuC2C7KPfZ8LB3DhQ9HxCbLpe',
  'admin', 999, TRUE, TRUE
);

INSERT INTO credit_transactions (id, user_id, tx_type, amount, balance_after, reference_note)
VALUES ('TXN-CRD-2024-00001', 'USR-ADM-2024-00001', 'admin_grant', 999, 999, 'Admin account initialization');
