# Admin View Setup Guide

## Overview
This setup provides usage tracking and an admin dashboard for the Pathwise learning app.

## Components Created

### 1. `usage_logger.py` - Usage Tracking Module
Logs user interactions to both:
- **Databricks Delta table** (when credentials configured)
- **Local JSONL file** (fallback when offline or not configured)

### 2. `Admin_Dashboard` - Admin Viewing Interface
Databricks notebook that provides:
- Authentication (password: `admin123`)
- Overview metrics
- Recent activity logs
- Usage breakdowns
- Timeline visualizations

## Quick Start

### Step 1: Integrate Logging into app.py

Add at the top of your `app.py` (after imports):

```python
from usage_logger import UsageLogger

# Initialize logger (will use local fallback by default)
usage_logger = UsageLogger()
```

### Step 2: Add Logging Calls

In the `PathwiseApp` class, add logging at key points:

**When loading a question:**
```python
def _load_question(self):
    # ... existing code ...
    
    # Add logging
    q = QUESTIONS[self.q_index]
    usage_logger.log_question_view(q["unit"])
```

**When checking answer:**
```python
def _check_answer(self):
    user_answer = self.answer_entry.get("1.0", "end").strip()
    q = QUESTIONS[self.q_index]
    
    # Check if correct
    is_correct = user_answer in q["accepted"]
    
    # Log the submission
    usage_logger.log_answer_submission(
        question_unit=q["unit"],
        user_answer=user_answer,
        is_correct=is_correct
    )
    
    # ... rest of your existing code ...
```

**When user queries AI tutor:**
```python
def _send_tutor_query(self):
    query = self.tutor_entry.get().strip()
    if not query:
        return
    
    # Log the query
    usage_logger.log_ai_query(query)
    
    # ... generate AI response ...
    
    # Log the response
    usage_logger.log_ai_response(query, ai_response)
```

## Step 3: Access Admin Dashboard

### Option A: Local File Viewing (No Setup Required)
By default, logs are saved to `usage_logs.jsonl` in your app directory.

You can view them with:
```python
import json

with open('usage_logs.jsonl') as f:
    for line in f:
        log = json.loads(line)
        print(f"{log['timestamp']}: {log['event_type']} - {log.get('user_input', 'N/A')}")
```

### Option B: Databricks Dashboard (Full Featured)

1. **Set up Databricks credentials** (one-time):
   ```bash
   export DATABRICKS_SERVER_HOSTNAME="your-workspace.cloud.databricks.com"
   export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/xxxxx"
   export DATABRICKS_ACCESS_TOKEN="your-token"
   ```

2. **Install Databricks connector**:
   ```bash
   pip install databricks-sql-connector
   ```

3. **Initialize logger with credentials** (in app.py):
   ```python
   usage_logger = UsageLogger(
       server_hostname="your-workspace.cloud.databricks.com",
       http_path="/sql/1.0/warehouses/xxxxx",
       access_token="your-token"
   )
   ```

4. **Open the Admin Dashboard**:
   - Navigate to the `Admin_Dashboard` notebook in Databricks
   - Run all cells
   - Enter password: `admin123`
   - View metrics and activity logs

## Admin Dashboard Features

### Authentication
- Simple password protection (password: `admin123`)
- Prevents unauthorized access to usage data

### Overview Metrics
- Total queries submitted
- Unique users
- Overall success rate
- Average response time

### Activity Tables
- Recent interactions (last 50)
- Detailed view of all user inputs and responses
- Timestamps and correctness indicators

### Analytics
- Usage by question unit
- Success rates per question
- Timeline of activity
- AI tutor query frequency

## Troubleshooting

### Logs not appearing?
- Check if `usage_logs.jsonl` file exists in your app directory
- Verify logging calls are being executed (add print statements)

### Can't connect to Databricks?
- Verify environment variables are set
- Check token hasn't expired
- Ensure SQL warehouse is running
- Logger will automatically fallback to local file logging

### Admin dashboard shows no data?
- Run the table creation cell in the dashboard first
- Upload local logs using the "Upload Local Logs" section in dashboard
- Check that logger is configured to write to Databricks

## Next Steps

1. **Customize authentication**: Replace simple password with proper user management
2. **Add more metrics**: Track time spent per question, hints viewed, etc.
3. **Export data**: Add CSV export functionality to dashboard
4. **Alerts**: Set up notifications for system issues or low completion rates

## Security Notes

- Default password is `admin123` - **change this for production**
- Access tokens should never be committed to version control
- Use environment variables or Databricks secrets for credentials
- Consider implementing role-based access control for sensitive data
