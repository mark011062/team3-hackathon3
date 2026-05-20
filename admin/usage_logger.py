"""
Usage Logger for Pathwise Learning App
Logs user interactions to Databricks Delta table for admin dashboard
"""

import json
import uuid
from datetime import datetime
from typing import Optional
import os

# Try to import Databricks SQL connector (optional - falls back to local logging)
try:
    from databricks import sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: databricks-sql-connector not installed. Using local logging only.")


class UsageLogger:
    """Logs usage data to Databricks and/or local file"""
    
    def __init__(self, 
                 server_hostname: Optional[str] = None,
                 http_path: Optional[str] = None,
                 access_token: Optional[str] = None,
                 catalog: str = "workspace",
                 schema: str = "default",
                 table: str = "usage_logs",
                 local_fallback: bool = True):
        """
        Initialize logger
        
        Args:
            server_hostname: Databricks workspace URL (e.g., 'dbc-xxx.cloud.databricks.com')
            http_path: SQL warehouse HTTP path
            access_token: Personal access token
            catalog: Unity Catalog name
            schema: Schema name
            table: Table name
            local_fallback: If True, log to local file when DB unavailable
        """
        self.server_hostname = server_hostname or os.getenv('DATABRICKS_SERVER_HOSTNAME')
        self.http_path = http_path or os.getenv('DATABRICKS_HTTP_PATH')
        self.access_token = access_token or os.getenv('DATABRICKS_ACCESS_TOKEN')
        self.table_name = f"{catalog}.{schema}.{table}"
        self.local_fallback = local_fallback
        self.local_log_file = "usage_logs.jsonl"
        
        self.session_id = str(uuid.uuid4())
        self.user_id = os.getenv('USER', 'anonymous')
        
        self.db_available = DATABRICKS_AVAILABLE and all([
            self.server_hostname, 
            self.http_path, 
            self.access_token
        ])
    
    def _get_connection(self):
        """Get database connection"""
        if not self.db_available:
            return None
        
        try:
            return sql.connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token
            )
        except Exception as e:
            print(f"Failed to connect to Databricks: {e}")
            return None
    
    def log_event(self,
                  event_type: str,
                  question_unit: Optional[str] = None,
                  user_input: Optional[str] = None,
                  system_response: Optional[str] = None,
                  is_correct: Optional[bool] = None,
                  response_time_ms: Optional[int] = None):
        """
        Log a usage event
        
        Args:
            event_type: Type of event ('question_viewed', 'answer_submitted', 'ai_query', 'ai_response')
            question_unit: Question identifier (e.g., 'Unit 1.0')
            user_input: User's input/answer
            system_response: System's response
            is_correct: Whether answer was correct
            response_time_ms: Response time in milliseconds
        """
        log_entry = {
            'log_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_type': event_type,
            'question_unit': question_unit,
            'user_input': user_input,
            'system_response': system_response,
            'is_correct': is_correct,
            'response_time_ms': response_time_ms
        }
        
        # Try to log to database
        logged_to_db = False
        if self.db_available:
            logged_to_db = self._log_to_db(log_entry)
        
        # Fallback to local file
        if not logged_to_db and self.local_fallback:
            self._log_to_file(log_entry)
    
    def _log_to_db(self, log_entry: dict) -> bool:
        """Log to Databricks table"""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Insert log entry
            query = f"""
            INSERT INTO {self.table_name} 
            (log_id, timestamp, user_id, session_id, event_type, 
             question_unit, user_input, system_response, is_correct, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                log_entry['log_id'],
                log_entry['timestamp'],
                log_entry['user_id'],
                log_entry['session_id'],
                log_entry['event_type'],
                log_entry['question_unit'],
                log_entry['user_input'],
                log_entry['system_response'],
                log_entry['is_correct'],
                log_entry['response_time_ms']
            ))
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to log to database: {e}")
            return False
    
    def _log_to_file(self, log_entry: dict):
        """Log to local JSONL file as fallback"""
        try:
            with open(self.local_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Failed to log to file: {e}")
    
    # Convenience methods for common events
    
    def log_question_view(self, question_unit: str):
        """Log when a question is displayed"""
        self.log_event('question_viewed', question_unit=question_unit)
    
    def log_answer_submission(self, question_unit: str, user_answer: str, 
                             is_correct: bool, response_time_ms: Optional[int] = None):
        """Log when user submits an answer"""
        self.log_event(
            'answer_submitted',
            question_unit=question_unit,
            user_input=user_answer,
            is_correct=is_correct,
            response_time_ms=response_time_ms
        )
    
    def log_ai_query(self, user_query: str):
        """Log when user asks AI tutor a question"""
        self.log_event('ai_query', user_input=user_query)
    
    def log_ai_response(self, user_query: str, ai_response: str, response_time_ms: Optional[int] = None):
        """Log AI tutor response"""
        self.log_event(
            'ai_response',
            user_input=user_query,
            system_response=ai_response,
            response_time_ms=response_time_ms
        )


# Example usage
if __name__ == "__main__":
    # Initialize logger (will use local fallback if DB not configured)
    logger = UsageLogger()
    
    # Log some example events
    logger.log_question_view("Unit 1.0")
    logger.log_answer_submission("Unit 1.0", '"cheese"[:3]', is_correct=True, response_time_ms=2500)
    logger.log_ai_query("How do I slice a string?")
    logger.log_ai_response(
        "How do I slice a string?",
        "Use square brackets with start:end notation, like string[0:3]",
        response_time_ms=800
    )
    
    print(f"Logged events to {logger.local_log_file if not logger.db_available else logger.table_name}")
