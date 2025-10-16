# 🗄️ ML Data Collection & Storage System

## Overview
The OpsPilot AI agent uses a comprehensive **SQLite-based database system** to automatically collect, store, and learn from every command execution. Here's exactly how the ML learning pipeline works:

## 📊 Database Schema

### Core Tables:

1. **`command_executions`** - Main training data table
   ```sql
   CREATE TABLE command_executions (
       id INTEGER PRIMARY KEY,
       session_id TEXT NOT NULL,
       user_id TEXT DEFAULT 'unknown',
       host_info TEXT NOT NULL,
       command TEXT NOT NULL,
       command_hash TEXT NOT NULL,          -- For pattern recognition
       initial_risk_level TEXT NOT NULL,    -- AI's initial assessment
       initial_risk_score REAL NOT NULL,
       ml_risk_level TEXT,                  -- ML model prediction
       ml_confidence REAL,                  -- ML confidence score
       user_confirmed BOOLEAN NOT NULL,     -- Did user confirm risky command?
       confirmation_time_ms INTEGER,        -- How long to decide?
       execution_success BOOLEAN NOT NULL,  -- Did command succeed?
       execution_time_ms INTEGER,           -- How long did it take?
       exit_code INTEGER,                   -- Command exit code
       stdout_length INTEGER DEFAULT 0,     -- Output length
       stderr_length INTEGER DEFAULT 0,     -- Error output length
       actual_impact TEXT NOT NULL,         -- Real impact: none/minor/moderate/severe
       system_context TEXT NOT NULL,        -- JSON: OS, memory, disk, etc.
       timestamp TEXT NOT NULL,
       user_feedback TEXT,                  -- Optional user feedback
       feedback_rating INTEGER              -- 1-5 star rating
   );
   ```

2. **`command_patterns`** - Frequent command tracking
3. **`training_sessions`** - ML model training history  
4. **`user_behavior`** - User behavior analytics
5. **`system_contexts`** - System environment profiles

## 🔄 Data Collection Flow

### Step 1: Command Generation
```
User Request → AI generates command → Risk Analysis → ML Enhancement
                                                           ↓
                               Session Started (collect_command_execution())
```

### Step 2: User Interaction
```
Warning Popup → User Decision → Timing Recorded → Confirmation Stored
    ↓               ↓               ↓                    ↓
 Show Risk     Confirm/Cancel   Track Time        Store Decision
```

### Step 3: Command Execution  
```
SSH Execute → Monitor System → Capture Output → Detect Impact
     ↓            ↓               ↓              ↓
   Time It    Before/After     stdout/stderr   Auto-Classify
```

### Step 4: Data Storage
```
All Data Collected → Database Insert → ML Training Data → Model Improvement
                                           ↓                     ↓
                                    Ready for Training    Better Predictions
```

## 📍 **Database Location**

- **File**: `C:\projects\OpsPilot-main\data\ml_risk_database.db`
- **Type**: SQLite (single file, no server required)
- **Size**: Grows with usage (~1MB per 1000 commands)
- **Backup**: Automatic via file system

## 🚀 **Automatic Data Collection Points**

### 1. **Command Request** (Entry Point)
```python
# In app.py - /ask endpoint
session_id = collect_command_execution(
    command=generated_command,
    risk_analysis=analysis_result,
    system_context=current_system_context
)
```

### 2. **User Confirmation** (Frontend)
```javascript
// When user clicks confirm/cancel
fetch('/ml/feedback', {
    method: 'POST',
    body: JSON.stringify({
        session_id: currentSessionId,
        user_confirmed: confirmed,
        confirmation_time_ms: decisionTime
    })
});
```

### 3. **Command Execution** (SSH)
```python
# In run_command endpoint
start_execution_timer(session_id)
output, error = run_shell(command, ssh_client)
success = (exit_code == 0)

finalize_command_collection(
    session_id, success, exit_code, 
    output, error, system_context_after
)
```

## 🧠 **ML Training Data Examples**

### Example Record:
```json
{
    "id": 1,
    "command": "sudo rm -rf /tmp/*",
    "initial_risk_level": "high", 
    "initial_risk_score": 0.8,
    "ml_risk_level": "medium",
    "ml_confidence": 0.75,
    "user_confirmed": true,
    "confirmation_time_ms": 3500,
    "execution_success": true,
    "actual_impact": "none",
    "system_context": {
        "os_info": {"distribution": "ubuntu"},
        "memory_usage": {"percent": 45},
        "disk_usage": {"/": {"percent": 67}},
        "load_avg": {"1min": 0.8}
    },
    "feedback_rating": 4
}
```

### ML Features Extracted:
```python
features = {
    "command_length": 18,
    "has_sudo": 1,
    "has_rm": 1,
    "has_wildcards": 1,
    "system_load": 0.8,
    "memory_usage_percent": 45,
    "is_weekend": 0,
    "hour_of_day": 14
}
# Label: actual_impact="none" → 0 (Low Risk)
```

## 📈 **ML Model Training Process**

### 1. **Data Preparation**
```python
# Get training data (last 90 days)
df = db_manager.get_training_dataset(days_back=90)

# Extract features for each command
features = extract_features(df)
labels = map_impact_to_labels(df['actual_impact'])
```

### 2. **Model Training**
```python
# Train Random Forest on collected data
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate performance
accuracy = model.score(X_test, y_test)
```

### 3. **Continuous Learning**
```python
# Check if retraining needed (every 30 days or low accuracy)
if ml_scorer.should_retrain():
    result = ml_scorer.train_model(min_samples=50)
```

## 🎯 **What ML Learns From**

### ✅ **Positive Signals** (Commands were safe)
- User confirmed high-risk command → Executed successfully → No impact
- AI predicted high risk → Actual impact was none/minor
- Fast user confirmation → Successful execution

### ❌ **Negative Signals** (Commands were risky)  
- User bypassed warning → Command failed/caused damage
- AI predicted low risk → Actual impact was severe
- Long confirmation time → User was hesitant

### 🔄 **Behavioral Learning**
- Time of day patterns (maintenance windows)
- User risk tolerance by role
- System-specific command safety
- Context-dependent risk factors

## 📊 **Analytics & Monitoring**

### Database Analytics:
```python
# Get comprehensive analytics
analytics = db_manager.get_analytics_summary(days_back=30)

print(analytics)
# {
#   "total_commands": 1250,
#   "success_rate": 0.94,
#   "risk_distribution": {"low": 800, "medium": 350, "high": 100},
#   "confirmation_patterns": {...}
# }
```

### Model Performance:
```python
# Check ML model status
status = ml_scorer.get_model_performance()
# {
#   "accuracy": 0.87,
#   "precision": 0.84, 
#   "recall": 0.89,
#   "training_date": "2024-01-15T10:30:00",
#   "sample_size": 1500
# }
```

## 🔧 **Database Management**

### Automatic Maintenance:
- **Cleanup**: Old data (>1 year) automatically removed
- **Indexing**: Optimized for fast queries
- **Backup**: SQLite file can be copied for backup
- **Export**: Training data exportable to CSV/JSON

### Manual Operations:
```python
# Export training data
db_manager.export_training_data("training_data.csv", format="csv")

# Clean up old data  
db_manager.cleanup_old_data(keep_days=365)

# Get training dataset
df = db_manager.get_training_dataset(days_back=180, min_samples=50)
```

## 🚀 **Getting Started**

The ML system starts collecting data **immediately** when you:

1. **Use the `/ask` endpoint** - Every command request starts a session
2. **Execute commands** - All results are automatically recorded  
3. **Interact with warnings** - User decisions are tracked
4. **Provide feedback** - Optional ratings improve learning

**No manual setup required!** The database initializes automatically on first use.

### First Training:
```bash
# After collecting ~50 command executions
curl -X POST http://localhost:8080/ml/train \
  -H "Content-Type: application/json" \
  -d '{"min_samples": 50}'
```

The ML system learns and improves automatically from every command you run! 🎯