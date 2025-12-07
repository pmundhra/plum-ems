# JSON Body Request Guidelines

## Overview
All POST/PUT/PATCH endpoints MUST use JSON request bodies instead of query parameters. This follows RESTful principles and industry standards.

## Rules

### 1. Request Format
- ✅ **DO:** Use JSON body for POST/PUT/PATCH requests
- ✅ **DO:** Set `Content-Type: application/json` header
- ✅ **DO:** Validate requests with Pydantic models
- ❌ **DON'T:** Use query parameters for POST data
- ❌ **DON'T:** Use form-data unless specifically needed (file uploads)

### 2. Router Tags
APIRouter should define tags for the endpoints to group them in the API documentation, for example:
```python
router = APIRouter(prefix="/v1/conversations", tags=["Conversations v1"])
```

### 3. Request Models
All endpoints MUST define Pydantic request models:

```python
# app/models/requests.py
class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    role: str = Field(default="user")
    metadata: Optional[Dict[str, Any]] = None
```
**JSON body attributes should be in snake_case. For example: "conversation_id" instead of "conversationId".**

### 4. Endpoint Definition
Endpoints should have a summary and description
```python
@router.post("/", response_model=ResponseModel, status_code=201, summary="Create a resource", description="Create a new resource with the provided data")
async def create_resource(request: RequestModel = Body(...)):
    """Create resource with JSON body"""
    # Implementation
```
**Resources should be in plural and if multi-word, should be separated by hyphens. For example: "conversation-messages" instead of "conversationMessages".**

### 5. Required vs Optional Fields
- Use `Field(...)` for required fields
- Use `Field(default=value)` for optional with defaults
- Use `Optional[Type] = None` for truly optional fields
- Provide clear descriptions in Field()

### 6. Validation Rules
```python
class RequestModel(BaseModel):
    # String validation
    name: str = Field(..., min_length=1, max_length=100)
    
    # Numeric validation
    limit: int = Field(default=50, ge=1, le=100)
    
    # Pattern validation
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    # Custom validation
    @validator('field_name')
    def validate_field(cls, v):
        # Custom logic
        return v
```

### 7. Metadata Support
All request models SHOULD support optional metadata:
```python
metadata: Optional[Dict[str, Any]] = Field(
    default=None,
    description="Optional metadata for tracking/debugging"
)
```

### 8. Example Schemas
Include examples in model Config:
```python
class Config:
    json_schema_extra = {
        "example": {
            "content": "Hello, world",
            "role": "user",
            "metadata": {
                "source": "web_app"
            }
        }
    }
```

## Implementation Checklist

- [ ] All POST/PUT/PATCH use JSON bodies
- [ ] Pydantic models defined for all requests
- [ ] Validation rules appropriate
- [ ] Field descriptions provided
- [ ] Example schemas included
- [ ] Metadata field available where useful
- [ ] FastAPI `Body(...)` used in endpoint signature

## Anti-Patterns to Avoid

### ❌ Query Parameters for POST Data
```python
# DON'T DO THIS
@router.post("/conversations/start")
async def create(goal_id: str, text: str):
    pass
```

### ✅ Use JSON Body Instead
```python
# DO THIS
@router.post("/conversations/")
async def create(request: ConversationCreateRequest = Body(...)):
    pass
```

### ❌ Mixed Query and Body
```python
# DON'T MIX
@router.post("/resource")
async def create(id: str, request: RequestModel = Body(...)):
    pass
```

### ✅ Consistent Approach
```python
# Keep related data together
@router.post("/resource")
async def create(request: CompleteRequestModel = Body(...)):
    # Include id in request model if needed
    pass
```

## Response Models
Use the following response codes: 200, 201, 400, 401, 403, 404, 422, 429, 500 depending on the response from the service.

Always define response models too:
```python
class ResponseModel(BaseModel):
    id: str
    created_at: datetime
    # ... other fields
```

## Error Handling
Pydantic automatically validates and returns 422 for invalid requests:
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {
        "field": "content",
        "message": "Field required",
        "code": "MISSING"
      }
    ]
  }
}
```
For all other error cases, return the error in the following format:
```json
{
    "error": {
        "type": "invalid_request_error",
        "code": "resource_not_found",
        "message": "Resource not found",
        "details": []
    }
}
```

## Testing Requirements

- [ ] Test valid requests return expected response
- [ ] Test missing required fields return 422
- [ ] Test invalid field values return 422 with details
- [ ] Test optional fields can be omitted
- [ ] Test metadata is accepted and stored
- [ ] Verify Content-Type validation

## Migration from Query Parameters

If migrating from query params:
1. Create new endpoint with JSON body
2. Mark old endpoint as `deprecated=True`
3. Document migration in API docs
4. After grace period, remove old endpoint

## References
- OpenAI API: JSON bodies for all mutations
- Stripe API: JSON bodies for resource creation
- GitHub API: JSON bodies for POST/PUT/PATCH

