# modules/database_manager.py
import os
import json
import sqlite3
import logging
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Handles SQLite database operations for storing question metadata.
    """
    
    def __init__(self, db_file):
        """
        Initialize database manager with the path to the SQLite database file.
        
        Args:
            db_file (str): Path to the SQLite database file
        """
        self.db_file = db_file
        
        # Ensure parent directory exists
        db_dir = os.path.dirname(db_file)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # Initialize the database
        self._initialize_db()
    
    def _initialize_db(self):
        """
        Initialize the database schema if it doesn't exist.
        """
        conn = None
        try:
            # Connect to the database (creates file if it doesn't exist)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create metadata table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    created TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    review_completed INTEGER NOT NULL DEFAULT 0,
                    review_completed_at TEXT,
                    metadata_json TEXT NOT NULL
                )
            ''')
            
            # Create indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON questions (filename)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_review_completed ON questions (review_completed)')
            
            conn.commit()
            logger.info(f"Database initialized: {self.db_file}")
            
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
        finally:
            if conn:
                conn.close()
                
    def _get_connection(self):
        """
        Get a fresh database connection.
        
        Returns:
            sqlite3.Connection: Database connection
        """
        try:
            conn = sqlite3.connect(self.db_file)
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Return dictionary-like rows
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {str(e)}")
            return None
    
    def save_question(self, metadata):
        """
        Save question metadata to the database.
        
        Args:
            metadata (dict): Question metadata including filename
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not metadata or 'filename' not in metadata:
            logger.error("Invalid metadata: missing filename")
            return False
            
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            filename = metadata['filename']
            created = metadata.get('created', datetime.datetime.now().isoformat())
            last_updated = metadata.get('last_updated', created)
            review_completed = 1 if metadata.get('review_completed', False) else 0
            review_completed_at = metadata.get('review_completed_at') if review_completed else None
            
            # Convert full metadata to JSON for storage
            metadata_json = json.dumps(metadata)
            
            # Check if record already exists
            cursor.execute('SELECT id FROM questions WHERE filename = ?', (filename,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute('''
                    UPDATE questions
                    SET last_updated = ?,
                        review_completed = ?,
                        review_completed_at = ?,
                        metadata_json = ?
                    WHERE filename = ?
                ''', (last_updated, review_completed, review_completed_at, metadata_json, filename))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO questions
                    (filename, created, last_updated, review_completed, review_completed_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (filename, created, last_updated, review_completed, review_completed_at, metadata_json))
            
            conn.commit()
            logger.info(f"Question metadata saved to database: {filename}")
            return True
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error saving question to database: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_question(self, filename):
        """
        Get question metadata from the database.
        
        Args:
            filename (str): Question image filename
            
        Returns:
            dict: Question metadata or None if not found
        """
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT metadata_json FROM questions WHERE filename = ?', (filename,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return json.loads(row['metadata_json'])
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving question from database: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_all_questions(self, review_completed=None):
        """
        Get all questions from the database, optionally filtered by review status.
        
        Args:
            review_completed (bool, optional): Filter by review status
            
        Returns:
            list: List of question metadata dictionaries
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            
            if review_completed is None:
                cursor.execute('SELECT metadata_json FROM questions ORDER BY last_updated DESC')
            else:
                review_val = 1 if review_completed else 0
                cursor.execute('SELECT metadata_json FROM questions WHERE review_completed = ? ORDER BY last_updated DESC', 
                              (review_val,))
            
            rows = cursor.fetchall()
            
            return [json.loads(row['metadata_json']) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving questions from database: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
    
    def delete_question(self, filename):
        """
        Delete a question from the database.
        
        Args:
            filename (str): Question image filename
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM questions WHERE filename = ?', (filename,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Question deleted from database: {filename}")
                return True
            else:
                logger.warning(f"No question found to delete: {filename}")
                return False
                
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error deleting question from database: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def close(self):
        """
        Placeholder for compatibility - connections are closed after each operation.
        """
        pass