# API Versioning Guidelines

## Overview
All API endpoints MUST use version prefixes to support backward compatibility and smooth migrations. We follow industry standards used by Stripe, GitHub, and OpenAI.

## Rules

### 1. Version Prefix Structure
- ✅ **DO:** Use `API_PREFIX="/api/v1"` in application configuration (`app.py`)
- ✅ **DO:** Define router prefixes without version (e.g., `APIRouter(prefix="/conversations")`)
- ✅ **DO:** Apply version prefix when including routers: `app.include_router(router, prefix=config.API_PREFIX)`
- ❌ **DON'T:** Include version in individual router prefixes
- ❌ **DON'T:** Use query parameters for versioning (`?version=1`)
- ❌ **DON'T:** Use custom headers for versioning (`X-API-Version`)

### 2. Versioned Endpoints
All endpoints MUST follow this pattern:
```
/v1/goals/
/v1/conversations/
/v1/conversations/{id}/messages
/v1/ws/conversation/{id}
```

### 3. Version Information
Provide version info at root endpoint:
```json
GET /
{
  "name": "Intelligence Engine API",
  "version": "0.5.0",
  "api_version": "v1",
  "status": "operational",
  "sha": "git-commit-sha"
}
```

### 4. Breaking Changes
When introducing breaking changes:
- Create new version directory: `/v2/`
- Maintain `/v1/` endpoints for at least 6 months
- Document migration path
- Add deprecation notices to old endpoints

### 5. Non-Breaking Changes
These can be added to current version:
- New optional fields
- New endpoints
- Additional response fields (additive)
- Query parameter additions (optional)

## Implementation Checklist

- [ ] `API_PREFIX` is configured in application settings (e.g., `/api/v1`)
- [ ] All routers are included with `prefix=config.API_PREFIX` in `app.py`
- [ ] Router prefixes don't include version (e.g., `/conversations` not `/v1/conversations`)
- [ ] Root endpoint returns version information
- [ ] WebSocket endpoints include version via `API_PREFIX`
- [ ] API documentation shows version in URL
- [ ] Version bumped in configuration when changes occur

## Example Implementation

```python
# ✅ Correct - Router definition (views.py)
router = APIRouter(
    prefix="/conversations",
    tags=["Conversations v1"]
)

# ✅ Correct - Router inclusion (app.py)
from app.conversation.views import router as conversation_router
app.include_router(conversation_router, prefix=config.API_PREFIX)
# Results in: /api/v1/conversations

# ❌ Incorrect - Don't include version in router prefix
router = APIRouter(
    prefix="/v1/conversations",  # Version should come from API_PREFIX
    tags=["Conversations v1"]
)
```

## Migration Strategy

### When to Create v2:
- Removing required fields
- Changing response structure
- Renaming endpoints
- Changing authentication method
- Breaking HTTP status code changes

### How to Migrate:
1. Create `/v2/` routers alongside `/v1/`
2. Update `main.py` to include both versions
3. Document differences in `/docs`
4. Set deprecation timeline for v1
5. Monitor v1 usage before removal

## Testing Requirements

- [ ] Test all versioned endpoints return correct data
- [ ] Verify version info at root endpoint
- [ ] Check API docs show version in paths
- [ ] Confirm multiple versions can coexist

## References
- Stripe API: `https://api.stripe.com/v1/`
- GitHub API: `https://api.github.com/v3/`
- OpenAI API: `https://api.openai.com/v1/`

