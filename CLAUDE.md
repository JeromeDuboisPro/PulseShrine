# Claude Development Guide for PulseShrine

**IMPORTANT**: This is THE guide for development. Follow these principles for every change.

## Project Overview
PulseShrine is a serverless productivity tracking application built for a contest/jury presentation. Focus on speed, clean code, and demonstrable features.

### Architecture
- **Backend**: AWS Lambda (Python 3.13) + DynamoDB + Step Functions
- **Infrastructure**: AWS CDK (TypeScript)
- **Frontend**: React (separate package)
- **Event Processing**: EventBridge Pipes → Step Functions → Lambda chain

### Key Workflows
1. **Pulse Creation**: API → DynamoDB → Stream → AI Processing → Storage
2. **AI Enhancement**: Standard enhancement (rule-based) vs Bedrock enhancement (LLM)
3. **Data Flow**: Start Pulse → Stop Pulse → AI Selection → Enhancement → Ingestion

## Development Standards

### Core Engineering Principles

#### DRY (Don't Repeat Yourself)
- **Shared Layer**: All common code goes in `/shared/lambda_layer/python/shared/`
- **Reusable Services**: Use service classes for business logic (e.g., `AIBudgetService`, `WorthinessCalculator`)
- **Configuration**: Centralize config in SSM parameters, not hardcoded values
- **Models**: Single source of truth in `shared/models/pulse.py`

**Example**:
```python
# ❌ BAD: Duplicated logic
# In handler1.py
cost = (tokens / 1000) * 0.00006
# In handler2.py  
cost = (tokens / 1000) * 0.00006

# ✅ GOOD: Centralized
# In shared/services/cost_calculator.py
def calculate_cost(tokens: int, model_id: str) -> float:
    return PRICING[model_id].calculate(tokens)
```

#### YAGNI (You Aren't Gonna Need It)
- **No Premature Abstraction**: Start with simple implementations
- **Feature Flags**: Use SSM parameters to toggle features instead of complex code
- **Minimal Dependencies**: Only add packages when truly needed

**Example**:
```python
# ❌ BAD: Over-engineering
class AbstractPulseProcessor(ABC):
    @abstractmethod
    def pre_process(self): pass
    @abstractmethod 
    def process(self): pass
    @abstractmethod
    def post_process(self): pass

# ✅ GOOD: Simple and direct
def process_pulse(pulse_data: dict) -> dict:
    validated = validate_pulse(pulse_data)
    enhanced = enhance_if_worthy(validated)
    return store_pulse(enhanced)
```

#### SOLID Principles

**Single Responsibility**:
```python
# Each Lambda function has ONE job:
# - ai_selection: Decides if AI-worthy
# - bedrock_enhancement: Enhances with AI
# - standard_enhancement: Rule-based enhancement
# - pure_ingest: Stores in DynamoDB
```

**Open/Closed**:
```python
# Services are open for extension via composition
class WorthinessCalculator:
    def __init__(self, budget_service: AIBudgetService):
        self.budget_service = budget_service
        # Easy to add new scoring strategies without modifying existing code
```

**Liskov Substitution**:
```python
# All pulse types can be used interchangeably where PulseBase is expected
class StartPulse(PulseBase): ...
class StopPulse(PulseBase): ...
class ArchivedPulse(StopPulse): ...
```

**Interface Segregation**:
```python
# Separate interfaces for different concerns
class PulseReader(Protocol):
    def get_pulse(self, pulse_id: str) -> Pulse: ...

class PulseWriter(Protocol):
    def save_pulse(self, pulse: Pulse) -> None: ...
```

**Dependency Inversion**:
```python
# Depend on abstractions (boto3 clients), not concrete implementations
def __init__(self, dynamodb_client=None):
    self.client = dynamodb_client or boto3.client('dynamodb')
```

#### TDD (Test-Driven Development)
- **Test First**: Write tests before implementation
- **Red-Green-Refactor**: Follow TDD cycle
- **Test Structure**: Use Arrange-Act-Assert pattern

**Example Test Structure**:
```python
# tests/unit/test_worthiness_calculator.py
def test_exceptional_pulse_gets_high_score():
    # Arrange
    calculator = WorthinessCalculator(mock_budget_service)
    pulse_data = create_test_pulse(duration=1800, reflection_length=150)
    
    # Act
    score = calculator.calculate_worthiness(pulse_data, "user123")
    
    # Assert
    assert score >= EXCEPTIONAL_THRESHOLD
```

**Testing Commands**:
```bash
# Run tests before committing
pytest packages/backend/tests/unit/ -v

# Run with coverage
pytest --cov=packages/backend/src --cov-report=term-missing

# Run specific test
pytest -k "test_worthiness" -v
```

#### SOC (Separation of Concerns)
- **Handlers**: HTTP/Event handling only, no business logic
- **Services**: Business logic and orchestration
- **Models**: Data validation and transformation
- **Utils**: Cross-cutting concerns (logging, metrics)

**Layer Architecture**:
```
handlers/api/         → API Gateway integration
handlers/events/      → Event processing (DynamoDB streams)
shared/services/      → Business logic
shared/models/        → Data models
shared/utils/         → Utilities
```

### Python Best Practices
```python
# Always use type hints
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Standard function signature
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Function description with input/output details."""
    pass

# Error handling pattern
try:
    result = risky_operation()
    return {"success": True, "data": result}
except SpecificException as e:
    logger.error(f"Specific error: {e}")
    return {"success": False, "error": str(e)}
except Exception as e:
    logger.exception("Unexpected error")
    return {"success": False, "error": "Internal error"}
```

### AWS Lambda Patterns
- **Single Responsibility**: One function = one purpose
- **Stateless**: No global state, use environment variables for config
- **Fast Cold Starts**: Keep imports minimal, use shared layers
- **Powertools**: Always use for logging, tracing, metrics
- **Timeout**: Set appropriate timeouts (API: 30s, Processing: 2-5min)
- **Memory**: Start with 1024MB, adjust based on performance

### DynamoDB Patterns
- **Single Table Design**: Use composite keys (PK/SK patterns)
- **Efficient Queries**: Design access patterns first
- **Handle Decimals**: Convert Decimal to float/int for JSON serialization
- **Batch Operations**: Use batch_write for multiple items

### Step Functions Best Practices
- **Express Workflows**: For high-volume, short-duration processes
- **Error Handling**: Use Retry and Catch states
- **JSON Serialization**: Ensure all response objects are JSON-serializable
- **Parallel Processing**: Use Map states for batch operations

### CDK Best Practices
```typescript
// Resource naming convention
functionName: 'ps-{function-purpose}',  // e.g., 'ps-ai-selection'

// Common Lambda props pattern
const commonLambdaProps = {
    architecture: lambda.Architecture.ARM_64,  // Better price/performance
    runtime: lambda.Runtime.PYTHON_3_13,
    layers: [sharedLayer],
    timeout: cdk.Duration.seconds(30),
    memorySize: 1024,
};

// Environment variables
environment: {
    TABLE_NAME: props.table.tableName,
    PARAMETER_PREFIX: '/pulseshrine/ai/',
}
```

## File Organization

### Backend Structure
```
packages/backend/src/
├── handlers/
│   ├── api/          # HTTP API handlers
│   └── events/       # Event-driven handlers
├── shared/
│   └── lambda_layer/
│       └── python/shared/
│           ├── models/     # Pydantic models
│           ├── services/   # Business logic
│           └── utils/      # Helper functions
```

### Key Files
- `ai_selection/app.py`: Determines AI worthiness
- `bedrock_enhancement/app.py`: LLM-based enhancement
- `standard_enhancement/app.py`: Rule-based enhancement  
- `pure_ingest/app.py`: DynamoDB storage
- `shared/models/pulse.py`: Core data models

## Development Commands

### Testing
```bash
# ALWAYS run tests before committing
pytest packages/backend/tests/ -v

# Run specific test file
pytest packages/backend/tests/test_ai_selection.py -v

# Run with coverage
pytest packages/backend/tests/ --cov=packages/backend/src --cov-report=html
```

### Development Workflow
1. **Before coding**: Read this guide and check existing patterns
2. **While coding**: Follow DRY, YAGNI, SOLID, TDD, SOC principles
3. **Before committing**: Run tests, linting, and review checklist below
4. **Code Review Checklist**:
   - [ ] No duplicated code (DRY)
   - [ ] No over-engineering (YAGNI)
   - [ ] Single responsibility per function/class (SOLID)
   - [ ] Tests written and passing (TDD)
   - [ ] Business logic in services, not handlers (SOC)
   - [ ] Used existing patterns from codebase
   - [ ] No hardcoded values (use env vars/SSM)

### Linting & Formatting
```bash
# Format Python code
black packages/backend/src/
ruff check packages/backend/src/ --fix

# Format TypeScript
prettier --write packages/infrastructure/**/*.ts

# Type checking
mypy packages/backend/src/
```

### CDK Commands
```bash
cd packages/infrastructure

# Deploy all stacks
cdk deploy --all --require-approval never

# Deploy specific stack
cdk deploy LambdaStack

# View diff before deploy
cdk diff

# Destroy for cleanup
cdk destroy --all
```

### Git Workflow
```bash
# Standard commit message format
git commit -m "feat: add emotion-aware title generation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Claude Efficiency Guidelines

### Files and Directories to Ignore
When searching, reading, or modifying files, avoid these common build artifacts and dependencies:

**Node.js/TypeScript:**
- `node_modules/` - NPM dependencies (thousands of files)
- `dist/`, `build/`, `out/` - Compiled output
- `*.js`, `*.d.ts` in infrastructure (CDK generates these from TS)
- `.next/` - Next.js build cache

**Python:**
- `venv/`, `env/`, `.venv/` - Virtual environments
- `__pycache__/` - Python bytecode cache
- `*.pyc`, `*.pyo`, `*.pyd` - Compiled Python files
- `.pytest_cache/` - Pytest cache
- `htmlcov/` - Coverage reports
- `.mypy_cache/` - Type checking cache
- `.ruff_cache/` - Linter cache

**AWS CDK:**
- `cdk.out/` - CDK synthesis output (CloudFormation templates)
- `.cdk.staging/` - CDK asset staging
- `cdk-outputs.json` - CDK deployment outputs

**IDE/Editor:**
- `.vscode/` - VS Code settings
- `.idea/` - IntelliJ IDEA settings
- `*.swp`, `*.swo` - Vim swap files
- `.DS_Store` - macOS metadata

**Testing/Coverage:**
- `coverage/` - Test coverage reports
- `.coverage` - Coverage data file
- `*.log` - Log files

**Other:**
- `.git/` - Git repository data
- `tmp/`, `temp/` - Temporary files
- `*.bak`, `*.backup` - Backup files
- `.env.local`, `.env.*.local` - Local environment files

### Search Strategy Tips
1. **Use specific paths**: Instead of searching all files, target source directories:
   ```bash
   # Good - searches only source code
   grep "pattern" packages/backend/src/
   
   # Avoid - searches everything including node_modules
   grep "pattern" .
   ```

2. **Use glob patterns wisely**:
   ```bash
   # Good - finds Python source files
   **/*.py --exclude venv --exclude __pycache__
   
   # Good - finds TypeScript source files
   packages/**/src/**/*.ts
   ```

3. **Check file size before reading**: Large generated files can waste context
   ```bash
   # Check file size first
   ls -lh packages/infrastructure/cdk.out/
   ```

### When to Use Task Tool
- Searching for unknown file locations
- Finding patterns across multiple files
- Complex multi-step research tasks
- When you need to explore unfamiliar code areas

### Direct Tool Usage
- Reading specific known files: Use `Read`
- Finding files by pattern: Use `Glob`
- Searching code in known directories: Use `Grep`
- Making targeted edits: Use `Edit` or `MultiEdit`

### File Search Strategy
1. **Start with Glob**: Find files by pattern (`**/*.py`, `**/app.py`)
2. **Use Grep**: Search for specific code patterns
3. **Read files**: Understand context before editing
4. **Task tool**: When above approaches don't work

### Common Patterns
```bash
# Find Lambda handlers
find packages/backend/src/handlers -name "app.py"

# Search for specific functions
rg "def handler" packages/backend/src/

# Find model definitions
rg "class.*Model" packages/backend/src/shared/

# Check CDK stack definitions
ls packages/infrastructure/lib/*-stack.ts
```

## Applying Engineering Principles

### Code Review Checklist
Before committing code, ensure it follows these principles:

**DRY Check**:
- [ ] No duplicated logic across files
- [ ] Common functionality extracted to shared services
- [ ] Configuration values from environment/SSM, not hardcoded

**YAGNI Check**:
- [ ] No unused code or features
- [ ] No complex abstractions for simple problems
- [ ] No "just in case" implementations

**SOLID Check**:
- [ ] Each function/class has one clear responsibility
- [ ] New features added without modifying existing code
- [ ] Dependencies injected, not hardcoded
- [ ] Interfaces focused on specific use cases

**Testing Check**:
- [ ] Unit tests written for new functionality
- [ ] Tests follow AAA pattern
- [ ] Edge cases covered
- [ ] Mocks used for external dependencies

**SOC Check**:
- [ ] Business logic in services, not handlers
- [ ] Data validation in models
- [ ] Infrastructure concerns separate from application code

### Refactoring Examples

**Before (Violates DRY, SOC)**:
```python
# In start_pulse/app.py
def handler(event, context):
    # Business logic mixed with handler
    user_id = event['body']['user_id']
    table = boto3.resource('dynamodb').Table('pulses')
    
    # Duplicated validation
    if len(event['body']['intent']) > 200:
        return {"statusCode": 400, "body": "Intent too long"}
    
    # Direct DynamoDB access
    table.put_item(Item={...})
```

**After (Follows principles)**:
```python
# In start_pulse/app.py
def handler(event, context):
    # Handler only handles HTTP concerns
    try:
        pulse = StartPulse(**json.loads(event['body']))
        result = pulse_service.create_pulse(pulse)
        return {"statusCode": 200, "body": json.dumps(result)}
    except ValidationError as e:
        return {"statusCode": 400, "body": str(e)}

# In shared/services/pulse_service.py
class PulseService:
    def create_pulse(self, pulse: StartPulse) -> dict:
        # Business logic centralized
        return self.repository.save(pulse.dict())
```

### When to Break the Rules

Sometimes pragmatism wins:

1. **Lambda Cold Starts**: Some DRY violations acceptable to reduce imports
2. **Proof of Concept**: YAGNI heavily during experimentation
3. **Performance Critical**: May violate SOC for optimization
4. **Time Constraints**: Document technical debt for later refactoring

Always document why you're breaking a principle:
```python
# TODO: Duplicated to avoid cold start penalty from heavy imports
# Technical debt ticket: PULSE-123
```

## Error Patterns & Solutions

### JSON Serialization Issues
```python
# Problem: Enum not serializable
"eventName": record.event_name,  # ❌

# Solution: Convert to string
"eventName": str(record.event_name),  # ✅
```

### DynamoDB Decimal Handling
```python
# Problem: Decimal not JSON serializable
duration = pulse_data["duration_seconds"]  # Decimal type

# Solution: Convert to float
duration = float(pulse_data["duration_seconds"])  # ✅
```

### Iterator Issues
```python
# Problem: Can't get length of iterator
len(ddb_event.records)  # ❌

# Solution: Convert to list first
records_list = list(ddb_event.records)
len(records_list)  # ✅
```

## Critical Development Rules

### ALWAYS DO:
1. **Use existing patterns** - Check similar files before creating new ones
2. **Test first** - Write tests before implementation (TDD)
3. **Keep it simple** - No abstractions until needed 3+ times (YAGNI)
4. **One job per function** - If it has "and" in the description, split it
5. **Use shared layer** - Put reusable code in `/shared/lambda_layer/python/shared/`

### NEVER DO:
1. **Never duplicate code** - Extract to shared services/utils
2. **Never hardcode values** - Use environment variables or SSM parameters
3. **Never mix concerns** - Business logic stays in services, not handlers
4. **Never skip tests** - Every new function needs a test
5. **Never commit without running**: `pytest && black . && ruff check`

## 🔒 SECURITY: API Keys & Credentials

**⚠️ CRITICAL WARNING: NEVER COMMIT SECRETS ⚠️**

### FORBIDDEN - Never commit these to Git:
- AWS Access Keys (`AKIA...`, `AWS_SECRET_ACCESS_KEY`)
- API Keys (OpenAI, Anthropic, third-party services)
- Database passwords or connection strings
- JWT secrets, encryption keys, certificates
- Personal tokens, session tokens
- `.env` files with real values
- Hardcoded credentials in source code

### SAFE PRACTICES:
```bash
# ✅ Environment variables (runtime)
BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"

# ✅ SSM Parameters (secure storage)
aws ssm put-parameter --name "/pulseshrine/ai/api-key" --value "secret" --type "SecureString"

# ✅ CDK deployment with env vars
ENVIRONMENT=prod MARKET=global cdk deploy

# ❌ NEVER hardcode in source
api_key = "sk-1234567890abcdef"  # DON'T DO THIS
```

### Git Pre-commit Checklist:
- [ ] No AWS keys in code (`grep -r "AKIA" .`)
- [ ] No API keys in code (`grep -r "sk-" .`)
- [ ] No passwords in code (`grep -r "password" .`)
- [ ] `.env.example` only has placeholder values
- [ ] All secrets use environment variables or SSM

### If You Accidentally Commit Secrets:
1. **Immediately rotate** the compromised credentials
2. **Force push** to remove from Git history: `git filter-branch` or BFG
3. **Verify** no other copies exist in forks/backups
4. **Report** to security team if applicable

### Credential Management:
- **Development**: Use AWS CLI profiles (`aws configure`)
- **CI/CD**: Use IAM roles, not access keys
- **Production**: Use IAM roles, SSM SecureString parameters
- **Frontend**: Never store backend credentials in React app

### Quick Patterns Reference
```python
# Lambda Handler Pattern
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    try:
        # 1. Parse input
        data = parse_event(event)
        # 2. Call service
        result = service.process(data)
        # 3. Return response
        return {"statusCode": 200, "body": json.dumps(result)}
    except ValidationError as e:
        return {"statusCode": 400, "body": str(e)}
    except Exception as e:
        logger.exception("Unexpected error")
        return {"statusCode": 500, "body": "Internal error"}

# Service Pattern
class PulseService:
    def __init__(self, table_name: str, dynamodb_client=None):
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        self.table_name = table_name
    
    def process(self, data: dict) -> dict:
        # Business logic here
        pass

# Test Pattern
def test_feature_description():
    # Arrange
    service = PulseService("test-table", mock_client)
    input_data = {...}
    
    # Act
    result = service.process(input_data)
    
    # Assert
    assert result["status"] == "success"
```

## Quick Reference

### Essential Environment Variables
- `START_PULSE_TABLE_NAME`: DynamoDB table for active pulses
- `STOP_PULSE_TABLE_NAME`: DynamoDB table for completed pulses  
- `INGESTED_PULSE_TABLE_NAME`: DynamoDB table for processed pulses
- `PARAMETER_PREFIX`: SSM parameter path prefix (`/pulseshrine/ai/`)
- `DEFAULT_BEDROCK_MODEL_ID`: Override default model selection (optional)

### Key AWS Resources
- **Tables**: `ps-start-pulse`, `ps-stop-pulse`, `ps-ingested-pulse`
- **Functions**: `ps-ai-selection`, `ps-bedrock-enhancement`, `ps-standard-enhancement`
- **Workflow**: `ps-ai-ingestion-workflow`

### Required Bedrock Models
Before deployment, ensure these models are enabled in AWS Bedrock Console:

**Primary Models (Nova Lite - Recommended):**
- `us.amazon.nova-lite-v1:0` (US regions)
- `eu.amazon.nova-lite-v1:0` (EU regions)  
- `apac.amazon.nova-lite-v1:0` (APAC regions)

**Universal Fallback:**
- `anthropic.claude-3-haiku-20240307-v1:0` (Available in all Bedrock regions)

**Model Access Setup:**
1. Go to AWS Bedrock Console in your deployment region
2. Navigate to "Model access" 
3. Request access to Nova Lite and Claude Haiku
4. Wait for approval (usually instant)

**Model Override Options:**
```bash
# CDK deployment with custom model
BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0" cdk deploy --all

# Runtime fallback automatically handles unavailable models
```

### Critical Files for Contest Demo
1. **AI Selection Logic**: `ai_selection/app.py` (smart selection algorithm)
2. **Bedrock Integration**: `bedrock_enhancement/app.py` (LLM enhancement)
3. **Standard Processing**: `standard_enhancement/app.py` (efficient rule-based)
4. **Step Functions**: `sfn-stack.ts` (orchestration showcase)

## Contest/Jury Focus Areas

### Technical Excellence
- Clean, typed Python code
- Proper error handling and logging
- Efficient AWS resource usage
- Smart caching and performance optimization

### Architecture Highlights  
- Event-driven serverless design
- Cost-effective AI selection algorithm
- Scalable Step Functions workflow
- Multi-modal processing (standard vs premium AI)

### Demonstrable Features
- Real-time pulse tracking
- Intelligent AI enhancement selection  
- Emotion-aware content generation
- Cost-optimized processing pipeline