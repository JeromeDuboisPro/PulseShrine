# PulseShrine End-to-End Pipeline Test

This directory contains a comprehensive end-to-end test that validates the complete PulseShrine pipeline from start to finish.

## What It Tests

The test simulates a complete user journey through the system:

1. **Start Pulse** - Creates a new productivity session
2. **Stop Pulse** - Completes the session with reflection
3. **AI Selection** - Determines if the pulse should get AI enhancement
4. **Standard Enhancement** - Generates standard title and badge using rule-based logic
5. **Bedrock Enhancement** - (If AI-worthy) Generates AI-enhanced content using AWS Bedrock
6. **Pure Ingest** - Stores the final processed pulse in DynamoDB

## Features

- ✅ **Pure Python** - No external dependencies on AWS infrastructure
- 🔧 **Complete Mocking** - Mocks all AWS services (DynamoDB, SSM, Bedrock)
- 📊 **Detailed Output** - Shows results from each pipeline step
- 🎯 **Real Data Flow** - Uses actual lambda handler functions
- 🚀 **Contest Ready** - Perfect for demonstrating the complete system

## How to Run

### Quick Start
```bash
cd packages/backend/tests/end_to_end
python run_test.py
```

### Direct Test Execution
```bash
cd packages/backend/tests/end_to_end
python test_complete_pipeline.py
```

### With Virtual Environment
```bash
cd packages/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd tests/end_to_end
python run_test.py
```

## Sample Output

```
🚀 PulseShrine End-to-End Test Runner
=====================================

🔧 Test environment configured:
   START_PULSE_TABLE_NAME: test-start-pulse-table
   STOP_PULSE_TABLE_NAME: test-stop-pulse-table
   ...

============================================================
 STEP 1: START PULSE
============================================================

🔹 Start Pulse
Result: {
  "pulse_id": "abc123...",
  "user_id": "test-user-12345",
  "intent": "Focus deeply on coding a revolutionary AI system",
  ...
}

============================================================
 STEP 2: STOP PULSE
============================================================

🔹 Stop Pulse
Result: {
  "message": "Pulse stopped successfully",
  ...
}

============================================================
 STEP 3: AI SELECTION
============================================================

🔹 AI Selection
Result: {
  "aiWorthy": true,
  "aiConfig": {...},
  ...
}

🤖 AI Enhancement Selected: Yes

============================================================
 STEP 4: STANDARD ENHANCEMENT
============================================================

🔹 Standard Enhancement
Result: {
  "generatedTitle": "🎯 Intensive Creation Session",
  "generatedBadge": "✨ Deep Thinker",
  ...
}

📝 Generated Title: 🎯 Intensive Creation Session
🏆 Generated Badge: ✨ Deep Thinker

============================================================
 STEP 5: BEDROCK ENHANCEMENT
============================================================

🔹 Bedrock Enhancement
Result: {
  "enhanced": true,
  "enhancedPulse": {
    "gen_title": "🎯 Deep Focus Coding Session Complete!",
    "gen_badge": "🤖 AI Enhanced",
    "ai_insights": {...}
  },
  ...
}

🤖 AI Enhanced Title: 🎯 Deep Focus Coding Session Complete!
🏆 AI Enhanced Badge: 🤖 AI Enhanced
💡 AI Insights: {...}
💰 AI Cost: 0.15¢

============================================================
 STEP 6: PURE INGEST
============================================================

🔹 Pure Ingest
Result: {
  "success": true,
  "message": "Pulse ingested successfully"
}

✅ Pulse successfully ingested to DynamoDB

============================================================
 FINAL RESULTS SUMMARY
============================================================
👤 User ID: test-user-12345
🎯 Original Intent: Focus deeply on coding a revolutionary AI system
⏱️  Duration: 25 minutes
💭 Reflection: I achieved deep focus and made significant progress...
😊 Final Emotion: accomplished
🤖 AI Enhanced: Yes
🎨 AI Generated Title: 🎯 Deep Focus Coding Session Complete!
🏅 AI Generated Badge: 🤖 AI Enhanced
💰 AI Cost: 0.15¢

🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!
```

## Test Data

The test uses realistic sample data:
- **Intent**: "Focus deeply on coding a revolutionary AI system"
- **Duration**: 25 minutes (1500 seconds)
- **Energy**: Creation
- **Reflection**: Detailed reflection about achieving focus and progress
- **Emotion**: Accomplished

## Architecture Validation

This test validates:
- ✅ Import reorganization (module-qualified imports)
- ✅ Lambda function handler signatures
- ✅ Event processing pipeline
- ✅ AI selection algorithm
- ✅ Standard and AI enhancement logic
- ✅ Data flow between components
- ✅ Error handling and resilience

## For Contest/Jury Demonstration

This test is perfect for demonstrating:
1. **Technical Excellence** - Shows clean, well-tested code
2. **Complete System** - Validates the entire pipeline works
3. **AI Integration** - Demonstrates both standard and AI-enhanced paths
4. **Professional Testing** - Shows comprehensive testing approach
5. **Easy Execution** - Can be run anywhere without AWS setup

Perfect for showing the jury that PulseShrine is a complete, well-engineered system! 🚀