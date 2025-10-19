import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                timezone VARCHAR(100) DEFAULT 'Europe/Rome',
                daily_hadith_enabled BOOLEAN DEFAULT FALSE,
                daily_hadith_time TIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hadith_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                hadith_number VARCHAR(50),
                book_name VARCHAR(255),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing database: {e}")
    finally:
        cur.close()
        conn.close()

def save_user(user_id, chat_id, username=None, first_name=None, last_name=None):
    """Save or update user in database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO users (user_id, chat_id, username, first_name, last_name, last_interaction)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                chat_id = EXCLUDED.chat_id,
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                last_interaction = EXCLUDED.last_interaction
        """, (user_id, chat_id, username, first_name, last_name, datetime.now()))
        
        conn.commit()
        logger.info(f"User {user_id} saved/updated")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving user {user_id}: {e}")
    finally:
        cur.close()
        conn.close()

def get_user(user_id):
    """Get user from database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def update_daily_hadith_settings(user_id, enabled, time_str=None):
    """Update user's daily hadith settings"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE users 
            SET daily_hadith_enabled = %s, daily_hadith_time = %s
            WHERE user_id = %s
        """, (enabled, time_str, user_id))
        
        conn.commit()
        logger.info(f"Daily hadith settings updated for user {user_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating daily hadith settings for {user_id}: {e}")
    finally:
        cur.close()
        conn.close()

def get_all_daily_hadith_users():
    """Get all users with daily hadith enabled"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT user_id, chat_id, daily_hadith_time, timezone 
            FROM users 
            WHERE daily_hadith_enabled = TRUE
        """)
        users = cur.fetchall()
        return [dict(user) for user in users]
    except Exception as e:
        logger.error(f"Error fetching daily hadith users: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def save_hadith_history(user_id, hadith_number, book_name):
    """Save hadith to user's history"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO hadith_history (user_id, hadith_number, book_name)
            VALUES (%s, %s, %s)
        """, (user_id, hadith_number, book_name))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving hadith history: {e}")
    finally:
        cur.close()
        conn.close()

def update_user_timezone(user_id, timezone_str):
    """Update user's timezone"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE users 
            SET timezone = %s
            WHERE user_id = %s
        """, (timezone_str, user_id))
        
        conn.commit()
        logger.info(f"Timezone updated for user {user_id}: {timezone_str}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating timezone for {user_id}: {e}")
    finally:
        cur.close()
        conn.close()