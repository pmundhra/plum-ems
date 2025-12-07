# Structured Logging Guidelines

## Overview
Use structured (JSON) logging for all application events to enable efficient searching, filtering, and analysis. Machine-readable logs are essential for production systems.

## Rules

### 1. JSON Log Format
ALL logs MUST be in JSON format:
```json
{
  "timestamp": "2025-10-24T10:15:30.123456Z",
  "level": "INFO",
  "event": "http_request",
  "method": "GET",
  "path": "/v1/goals/",
  "status": 200,
  "duration": 0.045,
  "request_id": "req_abc123"
}
```

### 2. Logger Configuration
Configure logger in `app/utils/logger.py`:
```python
import structlog
import logging

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### 3. Event-Based Logging
Use descriptive event names, not free-form messages:

```python
# ✅ Good - Structured with event name
logger.info("http_request", method="GET", path="/v1/goals/", status=200)

# ❌ Bad - Unstructured message
logger.info("GET request to /v1/goals/ returned 200")
```

### 4. Standard Fields
Include these fields in relevant logs:
- `event` - Event type (required)
- `timestamp` - ISO 8601 format (auto-added)
- `level` - Log level (auto-added)
- `request_id` - For request tracking
- `user_id` - If authenticated
- `conversation_id` - For conversation events
- `duration` - For timed operations
- `error` - For error logs
- `error_type` - Exception class name

### 5. Log Levels

#### DEBUG - Detailed Development Info
```python
logger.debug("cache_hit", key="user:123", ttl=300)
```

#### INFO - Normal Operations
```python
logger.info("conversation_created", conversation_id=conv_id, goal_id=goal_id)
```

#### WARNING - Unexpected but Handled
```python
logger.warning("rate_limit_approached", user_id=user_id, requests=90, limit=100)
```

#### ERROR - Error Occurred
```python
logger.error("external_service_failed", service="groq", error=str(e), error_type=type(e).__name__)
```

#### CRITICAL - System Failure
```python
logger.critical("database_connection_lost", error=str(e))
```

### 6. HTTP Request Logging
Log all HTTP requests:
```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        request_id=request_id
    )
    
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=duration,
        request_id=request_id
    )
    
    return response
```

### 7. LLM Request Logging
Track LLM operations with timing:
```python
start_time = time.time()
logger.info("llm_request_started", model=model, stream_mode=True)

try:
    result = await llm.generate(...)
    duration = time.time() - start_time
    
    logger.info(
        "llm_request_completed",
        model=model,
        stream_mode=True,
        latency=duration,
        tokens_used=result.usage.total_tokens
    )
except Exception as e:
    duration = time.time() - start_time
    logger.error(
        "llm_request_failed",
        model=model,
        stream_mode=True,
        latency=duration,
        error=str(e),
        error_type=type(e).__name__
    )
    raise
```

### 8. Error Logging
Always log errors with context:
```python
try:
    resource = await get_resource(resource_id)
except Exception as e:
    logger.error(
        "resource_fetch_failed",
        resource_id=resource_id,
        error=str(e),
        error_type=type(e).__name__,
        traceback=traceback.format_exc()
    )
    raise
```

### 9. Business Event Logging
Track important business events:
```python
logger.info(
    "conversation_escalated",
    conversation_id=conv_id,
    reason="frustrated_customer",
    message_count=len(conversation.messages),
    duration=conversation.duration_seconds
)

logger.info(
    "handoff_completed",
    conversation_id=conv_id,
    handoff_service="zendesk",
    status="success"
)
```

### 10. Sensitive Data
NEVER log sensitive information:
- ❌ Passwords
- ❌ API keys
- ❌ Credit card numbers
- ❌ Personal identifiable information (PII)
- ❌ Full message content (log summary/metadata only)

```python
# ❌ Bad - Logs sensitive data
logger.info("user_login", password=password)

# ✅ Good - No sensitive data
logger.info("user_login", user_id=user_id, method="password")
```

## Implementation Checklist

- [ ] structlog library installed and configured
- [ ] JSON output format enabled
- [ ] ISO 8601 timestamps
- [ ] Event-based logging (not messages)
- [ ] Standard fields used consistently
- [ ] Request ID tracking implemented
- [ ] HTTP requests logged
- [ ] LLM requests logged with timing
- [ ] Errors logged with context
- [ ] No sensitive data in logs

## Event Naming Conventions

Use lowercase with underscores, verb-based:
```python
# ✅ Good
"http_request_started"
"conversation_created"
"message_sent"
"escalation_detected"
"handoff_triggered"

# ❌ Bad
"HTTP Request"
"CreateConversation"
"msg_sent"
"Escalation"
```

## Common Event Types

### HTTP Events
- `http_request_started`
- `http_request_completed`
- `http_request_failed`

### LLM Events
- `llm_request_started`
- `llm_request_completed`
- `llm_request_failed`
- `llm_stream_first_token`

### Business Events
- `conversation_created`
- `conversation_ended`
- `message_sent`
- `message_received`
- `escalation_detected`
- `handoff_triggered`
- `handoff_completed`

### System Events
- `application_started`
- `application_shutdown`
- `database_connected`
- `external_service_unavailable`

## Searching and Filtering

### ELK Stack (Elasticsearch)
```json
// Find all errors for a specific request
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "ERROR" }},
        { "match": { "request_id": "req_abc123" }}
      ]
    }
  }
}
```

### JSON Logs with jq
```bash
# Find all LLM requests
cat app.log | jq 'select(.event | startswith("llm_"))'

# Calculate average LLM latency
cat app.log | jq -s 'map(select(.event == "llm_request_completed")) | map(.latency) | add / length'

# Find errors
cat app.log | jq 'select(.level == "ERROR")'
```

### Grep
```bash
# Find specific event
grep '"event":"conversation_created"' app.log

# Find errors for specific conversation
grep 'conv_123' app.log | grep '"level":"ERROR"'
```

## Context Management

Use context binding for request-scoped logging:
```python
# Bind context at start of request
logger = logger.bind(
    request_id=request_id,
    user_id=user_id
)

# All subsequent logs include this context
logger.info("processing_request")  # Includes request_id and user_id
logger.info("validation_passed")   # Includes request_id and user_id
```

## Log Rotation

Configure log rotation for production:
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "app.log",
    maxBytes=100_000_000,  # 100MB
    backupCount=10
)
```

## Performance Considerations

- Logging is relatively cheap (< 1ms per log)
- Use appropriate log levels (DEBUG only in development)
- Avoid logging in tight loops
- Consider async logging for high-throughput

```python
# ❌ Bad - Logging in loop
for item in large_list:
    logger.debug("processing_item", item=item)  # 1000s of logs

# ✅ Good - Log summary
logger.info("processing_items", count=len(large_list))
# ... process ...
logger.info("processing_complete", processed=successful, failed=errors)
```

## Testing Requirements

- [ ] Logs are in valid JSON format
- [ ] Timestamps are ISO 8601
- [ ] Events are properly named
- [ ] Required fields present
- [ ] No sensitive data logged
- [ ] Error logs include context
- [ ] Request IDs tracked across operations

## Development vs Production

### Development
```python
# Console output with pretty printing
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()  # Human-readable
    ]
)
```

### Production
```python
# JSON output for log aggregation
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()  # Machine-readable
    ]
)
```

## Integration with Monitoring

Logs should complement metrics:
```python
# Log the event
logger.info("llm_request_completed", latency=duration, model=model)

# Record the metric
LLM_LATENCY.labels(model=model).observe(duration)
```

## Anti-Patterns to Avoid

### ❌ String Formatting in Logs
```python
# DON'T - Hard to parse
logger.info(f"User {user_id} created conversation {conv_id}")
```

### ❌ Inconsistent Field Names
```python
# DON'T - Use same field names everywhere
logger.info("event1", user="john")
logger.info("event2", user_id="john")  # Inconsistent!
```

### ❌ Logging Objects
```python
# DON'T - Not serializable
logger.info("user_data", user=user_object)
```

### ✅ Correct Patterns
```python
# DO - Structured fields
logger.info("conversation_created", user_id=user_id, conversation_id=conv_id)

# DO - Consistent naming
logger.info("event1", user_id="john")
logger.info("event2", user_id="jane")

# DO - Log primitives
logger.info("user_data", user_id=user.id, name=user.name)
```

## References
- structlog Documentation: https://www.structlog.org/
- 12-Factor App Logging: https://12factor.net/logs
- JSON Logging Best Practices
- ELK Stack for log aggregation

