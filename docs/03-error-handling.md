# Standardized Error Handling Guidelines

## Overview
All errors MUST return consistent, structured responses following industry standards (OpenAI, Stripe). Never expose internal implementation details.

## Rules

### 1. Error Response Structure
ALL error responses MUST follow this format:
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "resource_not_found",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "field_name",
        "message": "Specific error",
        "code": "ERROR_CODE"
      }
    ],
    "request_id": "req_123abc",
    "timestamp": "2025-10-24T10:00:00Z"
  }
}
```

### 2. Error Types
Use appropriate error types:
- `invalid_request_error` - Client errors (400, 404, 422)
- `authentication_error` - Auth issues (401, 403)
- `rate_limit_error` - Rate limiting (429)
- `api_error` - Server errors (500, 502, 503)

### 3. Common Error Codes
| Code | Status | Usage |
|------|--------|-------|
| `resource_not_found` | 404 | Resource doesn't exist |
| `validation_error` | 422 | Request validation failed |
| `unauthorized` | 401 | Authentication required |
| `forbidden` | 403 | Access denied |
| `rate_limit_exceeded` | 429 | Too many requests |
| `internal_error` | 500 | Unexpected server error |
| `external_service_error` | 502 | External service failed |
| `service_unavailable` | 503 | Service temporarily down |

### 4. Custom Exception Classes
Define domain-specific exceptions:
```python
# app/models/errors.py
class ResourceNotFoundError(APIException):
    def __init__(self, resource_type: str, resource_id: str, field: str = None):
        message = f"{resource_type} not found: {resource_id}"
        details = [ErrorDetail(
            field=field or f"{resource_type.lower()}_id",
            message=message,
            code=f"{resource_type.upper()}_NOT_FOUND"
        )]
        super().__init__(
            message=message,
            status_code=404,
            error_type="invalid_request_error",
            error_code="resource_not_found",
            details=details
        )
```

### 5. Using Custom Exceptions
In endpoints, raise appropriate exceptions:
```python
@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    resource = await get_by_id(resource_id)
    if not resource:
        raise ResourceNotFoundError("Resource", resource_id)
    return resource
```

### 6. Global Exception Handlers
Register handlers in main.py:
```python
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

### 7. Field-Level Details
Provide specific field information for validation errors:
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format",
        "code": "INVALID_FORMAT"
      },
      {
        "field": "age",
        "message": "Must be at least 18",
        "code": "VALUE_TOO_SMALL"
      }
    ]
  }
}
```

### 8. Request ID Tracking
Every error MUST include a request_id:
```python
def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", f"req_{id(request)}")
```

### 9. Security Rules
- ❌ **NEVER** expose stack traces to clients
- ❌ **NEVER** expose database errors
- ❌ **NEVER** expose file paths
- ❌ **NEVER** expose internal service names
- ✅ **DO** log full details internally
- ✅ **DO** provide user-friendly messages
- ✅ **DO** include request_id for support

### 10. Logging
Log errors with structured data:
```python
logger.error(
    "resource_not_found",
    resource_type="Conversation",
    resource_id=conv_id,
    path=request.url.path,
    request_id=request_id
)
```

## HTTP Status Code Guidelines

### 2xx Success
- `200 OK` - Standard success
- `201 Created` - Resource created
- `204 No Content` - Success with no body

### 4xx Client Errors
- `400 Bad Request` - Malformed request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Authenticated but not authorized
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Validation failed
- `429 Too Many Requests` - Rate limited

### 5xx Server Errors
- `500 Internal Server Error` - Unexpected error
- `502 Bad Gateway` - External service error
- `503 Service Unavailable` - Temporary outage

## Implementation Checklist

- [ ] All exceptions extend base APIException
- [ ] Error models defined (ErrorDetail, ErrorResponse)
- [ ] Global exception handlers registered
- [ ] All endpoints use custom exceptions
- [ ] Request IDs tracked
- [ ] Timestamps in ISO 8601 format
- [ ] No internal details exposed
- [ ] Structured logging in place
- [ ] Error responses include field details

## Exception Handler Priority

1. Custom APIException → api_exception_handler
2. RequestValidationError → validation_exception_handler
3. HTTPException → http_exception_handler
4. All others → generic_exception_handler

## Testing Requirements

- [ ] Test 404 errors return proper format
- [ ] Test 422 validation errors include field details
- [ ] Test error responses have all required fields
- [ ] Test request_id is unique per request
- [ ] Test no stack traces in responses
- [ ] Test timestamps are ISO 8601
- [ ] Test error codes match documentation

## Common Patterns

### Resource Not Found
```python
if not resource:
    raise ResourceNotFoundError("Goal", goal_id, field="goal_id")
```

### Validation Error
```python
if not is_valid(value):
    raise ValidationError(
        "Invalid input",
        details=[ErrorDetail(
            field="field_name",
            message="Specific issue",
            code="VALIDATION_FAILED"
        )]
    )
```

### External Service Error
```python
try:
    result = await external_api.call()
except Exception as e:
    raise ExternalServiceError("GroqAPI", str(e))
```

## Anti-Patterns to Avoid

### ❌ Generic Exceptions
```python
# DON'T DO THIS
raise Exception("Something went wrong")
```

### ❌ HTTPException Directly
```python
# DON'T DO THIS (unless truly necessary)
raise HTTPException(status_code=404, detail="Not found")
```

### ❌ Exposing Internal Details
```python
# DON'T DO THIS
return {"error": str(e)}  # May expose stack trace
```

### ✅ Use Custom Exceptions
```python
# DO THIS
raise ResourceNotFoundError("Conversation", conv_id)
```

## References
- OpenAI Error Format: Consistent type/code/message
- Stripe Error Format: Detailed with field information
- RFC 7807: Problem Details for HTTP APIs
- Our implementation: Enhanced with request tracking

