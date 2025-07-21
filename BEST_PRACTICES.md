# PulseShrine Best Practices Guide

This guide provides practical examples of how to apply software engineering principles in the PulseShrine codebase.

## 🔄 DRY (Don't Repeat Yourself)

### ✅ Good Examples in PulseShrine

**Shared Models** (`shared/models/pulse.py`):
```python
# Single source of truth for all pulse types
class PulseBase(BaseModel):
    user_id: str
    intent: str = Field(max_length=200)
    # Common fields defined once
    
class StartPulse(PulseBase):
    # Inherits all base fields
    
class StopPulse(PulseBase):
    reflection: str = Field(max_length=200)
    # Extends base with specific fields
```

**Configuration Management**:
```python
# shared/utils/config.py
def get_parameter(parameter_name: str, default_value: str = "") -> str:
    """Centralized parameter fetching with caching"""
    if parameter_name in parameter_cache:
        return parameter_cache[parameter_name]
    # ... SSM logic
```

### ❌ Anti-patterns to Avoid

```python
# BAD: Duplicated DynamoDB client creation
# In handler1.py
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

# In handler2.py  
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

# GOOD: Use shared service
from shared.services.aws import get_dynamodb_table
table = get_dynamodb_table()
```

## 🚫 YAGNI (You Aren't Gonna Need It)

### ✅ Good Examples in PulseShrine

**Simple Step Functions Design**:
```typescript
// Just three states: Choice, Process, Store
const workflowDefinition = aiSelectionTask
  .next(aiWorthyChoice)
  .next(pureIngestTask);

// NOT: Complex state machine with 20 states "for future flexibility"
```

**Direct Lambda Integration**:
```python
# Simple, direct implementation
@logger.inject_lambda_context
def handler(event, context):
    pulse_data = extract_pulse_data(event)
    enhanced = enhance_pulse(pulse_data)
    return {"statusCode": 200, "body": enhanced}

# NOT: Abstract factory pattern for "future enhancement providers"
```

### ❌ Anti-patterns to Avoid

```python
# BAD: Over-engineered for unknown future
class PulseProcessorFactory:
    def create_processor(self, type: str) -> PulseProcessor:
        # We only have one type...
        
class AbstractMetricsCollector(ABC):
    # We don't even collect metrics yet...

# GOOD: Start simple
def process_pulse(pulse: dict) -> dict:
    return enhance_pulse(pulse)
```

## 🏗️ SOLID Principles

### Single Responsibility

**✅ Good: Each Lambda has ONE job**
```python
# ai_selection/app.py - ONLY decides if AI-worthy
def handler(event, context):
    pulse_data = extract_pulse_data(event)
    ai_worthy = should_enhance_with_ai(pulse_data)
    return {"aiWorthy": ai_worthy, "pulseData": pulse_data}

# bedrock_enhancement/app.py - ONLY enhances with AI
def handler(event, context):
    pulse_data = event["pulseData"]
    enhanced = enhance_with_bedrock(pulse_data)
    return {"enhancedData": enhanced}
```

### Open/Closed

**✅ Good: Extensible without modification**
```python
# shared/services/worthiness_service.py
class WorthinessCalculator:
    def __init__(self, strategies: List[ScoringStrategy] = None):
        self.strategies = strategies or [
            DurationStrategy(),
            ReflectionQualityStrategy(),
            ConsistencyStrategy()
        ]
    
    def calculate_worthiness(self, pulse_data: dict) -> float:
        return sum(s.score(pulse_data) for s in self.strategies)

# Easy to add new strategies without changing calculator
```

### Liskov Substitution

**✅ Good: Subtypes are truly substitutable**
```python
def process_any_pulse(pulse: PulseBase) -> dict:
    # Works with StartPulse, StopPulse, or ArchivedPulse
    return {
        "user_id": pulse.user_id,
        "intent": pulse.intent,
        "pulse_id": pulse.valid_pulse_id
    }
```

### Interface Segregation

**✅ Good: Focused interfaces**
```python
# Separate read/write interfaces
class PulseReader(Protocol):
    def get_pulse(self, pulse_id: str) -> Optional[dict]:
        ...

class PulseWriter(Protocol):
    def save_pulse(self, pulse: dict) -> None:
        ...

# Clients depend only on what they need
class DisplayService:
    def __init__(self, reader: PulseReader):
        self.reader = reader  # Only needs read access
```

### Dependency Inversion

**✅ Good: Depend on abstractions**
```python
class AIBudgetService:
    def __init__(self, 
                 table_name: str,
                 dynamodb_client=None,  # Inject dependency
                 user_service=None):
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        self.user_service = user_service or UserService()
```

## 🧪 TDD (Test-Driven Development)

### Test Structure in PulseShrine

```python
# tests/unit/test_worthiness_calculator.py
class TestWorthinessCalculator:
    def test_long_duration_increases_score(self):
        # Arrange
        calculator = WorthinessCalculator()
        short_pulse = {"duration_seconds": 300}  # 5 min
        long_pulse = {"duration_seconds": 1800}  # 30 min
        
        # Act
        short_score = calculator.calculate_worthiness(short_pulse, "user1")
        long_score = calculator.calculate_worthiness(long_pulse, "user1")
        
        # Assert
        assert long_score > short_score

    def test_empty_reflection_reduces_score(self):
        # Arrange
        calculator = WorthinessCalculator()
        pulse_with_reflection = {
            "duration_seconds": 600,
            "reflection": "Learned about DRY principles"
        }
        pulse_without = {
            "duration_seconds": 600,
            "reflection": ""
        }
        
        # Act & Assert
        assert calculator.calculate_worthiness(pulse_with_reflection, "user1") > \
               calculator.calculate_worthiness(pulse_without, "user1")
```

### Mocking External Dependencies

```python
# tests/unit/test_ai_selection.py
@patch('boto3.client')
def test_ai_selection_with_mocked_ssm(mock_boto_client):
    # Arrange
    mock_ssm = MagicMock()
    mock_ssm.get_parameter.return_value = {
        'Parameter': {'Value': 'true'}
    }
    mock_boto_client.return_value = mock_ssm
    
    # Act
    from handlers.events.ai_selection import handler
    result = handler(test_event, test_context)
    
    # Assert
    assert result['aiWorthy'] is True
```

## 🎯 SOC (Separation of Concerns)

### Layer Architecture in Practice

```
handlers/           → Lambda entry points (thin layer)
  api/             → HTTP request/response handling
  events/          → Event processing (DynamoDB, S3, etc.)

shared/services/   → Business logic (fat layer)
  ai_budget_service.py      → AI usage tracking logic
  worthiness_service.py     → Scoring algorithms
  user_service.py          → User management

shared/models/     → Data structures and validation
  pulse.py         → Pydantic models with validation

shared/utils/      → Cross-cutting concerns
  app_with_tracking.py     → Decorator for metrics
  logging.py              → Structured logging setup
```

### Example: Proper Separation

```python
# ❌ BAD: Everything in handler
def handler(event, context):
    # Parsing
    body = json.loads(event['body'])
    
    # Validation
    if len(body['intent']) > 200:
        return {"statusCode": 400}
    
    # Business logic
    score = 0
    if body['duration'] > 600:
        score += 10
    
    # Database access
    table = boto3.resource('dynamodb').Table('pulses')
    table.put_item(Item=body)
    
    return {"statusCode": 200}

# ✅ GOOD: Separated concerns
def handler(event, context):
    # Handler only orchestrates
    try:
        pulse = parse_request(event)
        validated = validate_pulse(pulse)
        result = pulse_service.create_pulse(validated)
        return format_response(200, result)
    except ValidationError as e:
        return format_response(400, {"error": str(e)})
```

## 📋 Code Review Checklist

Before submitting a PR, check:

### Architecture
- [ ] New code follows existing patterns
- [ ] Business logic is in services, not handlers
- [ ] Shared code is in the shared layer
- [ ] No circular dependencies

### Code Quality
- [ ] Functions do one thing well
- [ ] Names clearly express intent
- [ ] Complex logic has comments explaining "why"
- [ ] No commented-out code

### Testing
- [ ] Unit tests for new functionality
- [ ] Integration tests for API changes
- [ ] Edge cases covered
- [ ] Mocks used appropriately

### Performance
- [ ] No unnecessary database calls
- [ ] Batch operations where possible
- [ ] Appropriate Lambda memory/timeout
- [ ] Caching implemented where beneficial

### Security
- [ ] No hardcoded secrets
- [ ] Input validation on all user data
- [ ] Proper error messages (no stack traces)
- [ ] Least privilege IAM policies

## 🚀 Performance Patterns

### Lambda Optimization

```python
# Move imports inside handler for cold start optimization
def handler(event, context):
    # Only import heavy libraries when needed
    if event.get('useAI'):
        import boto3
        bedrock = boto3.client('bedrock-runtime')
```

### DynamoDB Optimization

```python
# Batch writes for multiple items
def save_pulses(pulses: List[dict]):
    with table.batch_writer() as batch:
        for pulse in pulses:
            batch.put_item(Item=pulse)
```

### Caching Strategy

```python
# Cache expensive operations
@lru_cache(maxsize=128)
def get_user_plan(user_id: str) -> str:
    # This won't change often
    return user_service.get_plan(user_id)
```

## 🛠️ Debugging Patterns

### Structured Logging

```python
logger.info("Processing pulse", extra={
    "pulse_id": pulse_id,
    "user_id": user_id,
    "duration": duration,
    "ai_worthy": ai_worthy
})
# Makes CloudWatch Insights queries easy
```

### Correlation IDs

```python
@logger.inject_lambda_context(correlation_id_path="requestContext.requestId")
def handler(event, context):
    # All logs in this execution will have the same correlation ID
    logger.info("Starting processing")
```

## 📚 Learning Resources

1. **Clean Code** by Robert Martin - For general principles
2. **AWS Lambda Best Practices** - AWS documentation
3. **Domain-Driven Design** by Eric Evans - For complex business logic
4. **Test-Driven Development** by Kent Beck - For TDD practices

Remember: These are guidelines, not rules. Use judgment and prioritize code clarity and maintainability.