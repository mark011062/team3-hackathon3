"""
Admin Dashboard for Pathwise Learning Application
==================================================

Monitors usage data, user queries, system responses, and basic usage metrics.

Features:
- Password authentication
- Overview metrics (total events, users, success rates)
- Recent activity logs
- Usage breakdown by question
- Activity timeline visualization
- AI tutor query logs

Requirements:
- databricks-sql-connector (for Databricks connection)
- pandas
- matplotlib

Setup:
1. Set environment variables or pass credentials to AdminDashboard class
2. Run: python admin_dashboard.py
3. Enter password when prompted (default: admin123)

For Databricks notebook version, see Admin_Dashboard.ipynb
"""

import os
import sys
from datetime import datetime, timedelta
import uuid
import random
from typing import Optional
import getpass

try:
    from databricks import sql
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    DATABRICKS_AVAILABLE = True
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install with: pip install databricks-sql-connector pandas matplotlib")
    sys.exit(1)


class AdminDashboard:
    """Admin dashboard for Pathwise learning application"""
    
    def __init__(self, 
                 server_hostname: Optional[str] = None,
                 http_path: Optional[str] = None,
                 access_token: Optional[str] = None,
                 catalog: str = "workspace",
                 schema: str = "default",
                 table: str = "usage_logs"):
        """
        Initialize admin dashboard
        
        Args:
            server_hostname: Databricks workspace URL
            http_path: SQL warehouse HTTP path
            access_token: Personal access token
            catalog: Unity Catalog name
            schema: Schema name
            table: Table name
        """
        self.server_hostname = server_hostname or os.getenv('DATABRICKS_SERVER_HOSTNAME')
        self.http_path = http_path or os.getenv('DATABRICKS_HTTP_PATH')
        self.access_token = access_token or os.getenv('DATABRICKS_ACCESS_TOKEN')
        self.table_name = f"{catalog}.{schema}.{table}"
        
        if not all([self.server_hostname, self.http_path, self.access_token]):
            print("⚠️  Warning: Databricks credentials not fully configured")
            print("Set environment variables or pass to constructor:")
            print("  - DATABRICKS_SERVER_HOSTNAME")
            print("  - DATABRICKS_HTTP_PATH")
            print("  - DATABRICKS_ACCESS_TOKEN")
            sys.exit(1)
    
    def _get_connection(self):
        """Get database connection"""
        return sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token
        )
    
    def _execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return pd.DataFrame(rows, columns=columns)
    
    def authenticate(self, password: str = "admin123") -> bool:
        """
        Simple authentication check
        
        Args:
            password: Admin password (default: admin123)
            
        Returns:
            True if authenticated, False otherwise
        """
        print("🔐 Admin Authentication")
        print("=" * 40)
        
        if sys.stdin.isatty():
            entered_password = getpass.getpass("Enter admin password: ")
        else:
            # Non-interactive mode
            entered_password = input("Enter admin password: ")
        
        if entered_password == password:
            print("\n✓ Authentication successful!")
            print("You can now access the admin dashboard.\n")
            return True
        else:
            print("\n✗ Authentication failed. Incorrect password.")
            return False
    
    def setup_table(self):
        """Create usage_logs table if it doesn't exist"""
        print("Setting up database table...")
        
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
          log_id STRING NOT NULL,
          timestamp TIMESTAMP NOT NULL,
          user_id STRING NOT NULL,
          session_id STRING NOT NULL,
          event_type STRING NOT NULL,
          question_unit STRING,
          user_input STRING,
          system_response STRING,
          is_correct BOOLEAN,
          response_time_ms INT
        )
        USING DELTA
        COMMENT 'Usage logs for Pathwise learning application'
        """
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(create_query)
        cursor.close()
        conn.close()
        
        print(f"✓ Table {self.table_name} ready")
    
    def generate_sample_data(self, num_records: int = 100):
        """Generate sample data for testing"""
        print(f"Generating {num_records} sample records...")
        
        # Check if table already has data
        count_query = f"SELECT COUNT(*) as cnt FROM {self.table_name}"
        df = self._execute_query(count_query)
        current_count = df['cnt'].iloc[0]
        
        if current_count > 0:
            print(f"Table already contains {current_count} records. Skipping sample data generation.")
            return
        
        # Generate sample data
        users = ['user_001', 'user_002', 'user_003', 'user_004']
        sessions = {u: str(uuid.uuid4()) for u in users}
        questions = ['Unit 1.0', 'Unit 1.1', 'Unit 1.2']
        
        base_time = datetime.now() - timedelta(days=7)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        insert_query = f"""
        INSERT INTO {self.table_name} 
        (log_id, timestamp, user_id, session_id, event_type, 
         question_unit, user_input, system_response, is_correct, response_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for i in range(num_records):
            user = random.choice(users)
            question = random.choice(questions)
            
            # Question viewed
            cursor.execute(insert_query, (
                str(uuid.uuid4()),
                base_time + timedelta(hours=i*2, minutes=random.randint(0, 59)),
                user,
                sessions[user],
                'question_viewed',
                question,
                None, None, None, None
            ))
            
            # Answer submitted
            is_correct = random.random() > 0.3
            cursor.execute(insert_query, (
                str(uuid.uuid4()),
                base_time + timedelta(hours=i*2, minutes=random.randint(0, 59), seconds=30),
                user,
                sessions[user],
                'answer_submitted',
                question,
                f'user_answer_{i}',
                None,
                is_correct,
                random.randint(1000, 5000)
            ))
            
            # Occasional AI query
            if random.random() > 0.7:
                cursor.execute(insert_query, (
                    str(uuid.uuid4()),
                    base_time + timedelta(hours=i*2, minutes=random.randint(0, 59), seconds=45),
                    user,
                    sessions[user],
                    'ai_query',
                    None,
                    'How do I solve this?',
                    None, None, None
                ))
                
                cursor.execute(insert_query, (
                    str(uuid.uuid4()),
                    base_time + timedelta(hours=i*2, minutes=random.randint(0, 59), seconds=46),
                    user,
                    sessions[user],
                    'ai_response',
                    None,
                    'How do I solve this?',
                    'Here is a hint...',
                    None,
                    random.randint(500, 2000)
                ))
        
        cursor.close()
        conn.close()
        
        print(f"✓ Generated sample data")
    
    def get_overview_metrics(self) -> pd.DataFrame:
        """Get overview metrics"""
        query = f"""
        SELECT 
          '📊 Total Events' as metric,
          COUNT(*) as value,
          '' as details
        FROM {self.table_name}
        
        UNION ALL
        
        SELECT 
          '👥 Unique Users' as metric,
          COUNT(DISTINCT user_id) as value,
          '' as details
        FROM {self.table_name}
        
        UNION ALL
        
        SELECT 
          '📝 Answer Submissions' as metric,
          COUNT(*) as value,
          '' as details
        FROM {self.table_name}
        WHERE event_type = 'answer_submitted'
        
        UNION ALL
        
        SELECT 
          '✓ Success Rate' as metric,
          ROUND(AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END), 1) as value,
          '%' as details
        FROM {self.table_name}
        WHERE event_type = 'answer_submitted'
        
        UNION ALL
        
        SELECT 
          '⏱️ Avg Response Time' as metric,
          ROUND(AVG(response_time_ms), 0) as value,
          'ms' as details
        FROM {self.table_name}
        WHERE response_time_ms IS NOT NULL
        
        UNION ALL
        
        SELECT 
          '🤖 AI Queries' as metric,
          COUNT(*) as value,
          '' as details
        FROM {self.table_name}
        WHERE event_type = 'ai_query'
        
        ORDER BY metric
        """
        
        return self._execute_query(query)
    
    def get_recent_activity(self, limit: int = 50) -> pd.DataFrame:
        """Get recent activity"""
        query = f"""
        SELECT 
          timestamp as time,
          user_id,
          event_type,
          question_unit,
          CASE 
            WHEN LENGTH(user_input) > 50 THEN CONCAT(SUBSTRING(user_input, 1, 50), '...')
            ELSE user_input 
          END as user_input,
          is_correct,
          response_time_ms
        FROM {self.table_name}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        return self._execute_query(query)
    
    def get_usage_by_question(self) -> pd.DataFrame:
        """Get usage breakdown by question"""
        query = f"""
        SELECT 
          COALESCE(question_unit, 'N/A (General)') as question_unit,
          COUNT(*) as total_views,
          SUM(CASE WHEN event_type = 'answer_submitted' THEN 1 ELSE 0 END) as submissions,
          SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct_answers,
          ROUND(
            100.0 * SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) / 
            NULLIF(SUM(CASE WHEN event_type = 'answer_submitted' THEN 1 ELSE 0 END), 0),
            1
          ) as success_rate_pct,
          ROUND(AVG(CASE WHEN event_type = 'answer_submitted' THEN response_time_ms END), 0) as avg_response_ms
        FROM {self.table_name}
        GROUP BY question_unit
        ORDER BY question_unit
        """
        
        return self._execute_query(query)
    
    def get_ai_tutor_logs(self, limit: int = 50) -> pd.DataFrame:
        """Get AI tutor query logs"""
        query = f"""
        SELECT 
          timestamp as time,
          user_id,
          CASE 
            WHEN LENGTH(user_input) > 80 THEN CONCAT(SUBSTRING(user_input, 1, 80), '...')
            ELSE user_input 
          END as query,
          CASE 
            WHEN LENGTH(system_response) > 80 THEN CONCAT(SUBSTRING(system_response, 1, 80), '...')
            ELSE system_response 
          END as response,
          response_time_ms
        FROM {self.table_name}
        WHERE event_type IN ('ai_query', 'ai_response')
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        return self._execute_query(query)
    
    def plot_activity_timeline(self):
        """Plot activity timeline"""
        query = f"""
        SELECT 
          DATE_TRUNC('hour', timestamp) as hour,
          event_type,
          COUNT(*) as count
        FROM {self.table_name}
        GROUP BY DATE_TRUNC('hour', timestamp), event_type
        ORDER BY hour
        """
        
        df = self._execute_query(query)
        
        if len(df) == 0:
            print("⚠️ No data available for timeline chart")
            return
        
        # Create pivot table
        pivot_df = df.pivot(index='hour', columns='event_type', values='count').fillna(0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 5), facecolor='#0F1117')
        ax.set_facecolor('#1E2435')
        
        # Plot stacked area
        pivot_df.plot.area(ax=ax, alpha=0.7, 
                           color=['#00C9A7', '#4C8BF5', '#FFB627', '#F87171'],
                           linewidth=0)
        
        # Styling
        ax.set_title('Activity Timeline by Event Type', 
                     fontsize=14, color='#E8ECF4', pad=15, weight='bold')
        ax.set_xlabel('Time', fontsize=11, color='#6B7A99')
        ax.set_ylabel('Event Count', fontsize=11, color='#6B7A99')
        ax.legend(title='Event Type', loc='upper left', 
                  facecolor='#161B27', edgecolor='#2E3650',
                  labelcolor='#E8ECF4', title_fontsize=10)
        
        # Grid
        ax.grid(True, alpha=0.2, color='#2E3650', linestyle='--')
        ax.spines['top'].set_color('#2E3650')
        ax.spines['right'].set_color('#2E3650')
        ax.spines['bottom'].set_color('#2E3650')
        ax.spines['left'].set_color('#2E3650')
        ax.tick_params(colors='#6B7A99')
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig('activity_timeline.png', facecolor='#0F1117', dpi=150)
        print(f"\n✓ Saved timeline chart to activity_timeline.png")
        plt.show()
    
    def print_dashboard(self):
        """Print complete dashboard to console"""
        print("\n" + "="*60)
        print("PATHWISE ADMIN DASHBOARD")
        print("="*60 + "\n")
        
        # Overview Metrics
        print("📊 OVERVIEW METRICS")
        print("-" * 60)
        metrics = self.get_overview_metrics()
        for _, row in metrics.iterrows():
            print(f"{row['metric']:.<40} {row['value']:.0f} {row['details']}")
        
        print("\n" + "="*60 + "\n")
        
        # Usage by Question
        print("📚 USAGE BY QUESTION")
        print("-" * 60)
        usage = self.get_usage_by_question()
        print(usage.to_string(index=False))
        
        print("\n" + "="*60 + "\n")
        
        # Recent Activity
        print("📝 RECENT ACTIVITY (Last 10)")
        print("-" * 60)
        recent = self.get_recent_activity(limit=10)
        print(recent.to_string(index=False))
        
        print("\n" + "="*60 + "\n")
        
        # AI Tutor Logs
        print("🤖 AI TUTOR LOGS (Last 10)")
        print("-" * 60)
        ai_logs = self.get_ai_tutor_logs(limit=10)
        print(ai_logs.to_string(index=False))
        
        print("\n" + "="*60 + "\n")


def main():
    """Main entry point"""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║         PATHWISE ADMIN DASHBOARD                       ║
    ║  Usage Tracking & Analytics for Learning Application  ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Initialize dashboard
    dashboard = AdminDashboard()
    
    # Authenticate
    if not dashboard.authenticate():
        print("Access denied.")
        sys.exit(1)
    
    # Setup table
    dashboard.setup_table()
    
    # Generate sample data if needed
    dashboard.generate_sample_data()
    
    # Display dashboard
    dashboard.print_dashboard()
    
    # Plot timeline
    print("\nGenerating activity timeline chart...")
    dashboard.plot_activity_timeline()
    
    print("\n✓ Dashboard complete!")


if __name__ == "__main__":
    main()
