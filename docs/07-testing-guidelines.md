# Testing Guidelines and Standards

## Overview
This document defines the testing strategy, conventions, and best practices for the Intelligence Engine API. Following these guidelines ensures comprehensive test coverage, maintainability, and reliability.

---

## Testing Philosophy

### Core Principles
1. **Tests should be reliable** - No flaky tests, consistent results
2. **Tests should be fast** - Unit tests < 1s, integration tests < 5s
3. **Tests should be isolated** - No dependencies between tests
4. **Tests should be clear** - Purpose obvious from test name
5. **Tests should be maintainable** - Easy to update when requirements change

### Test Pyramid
```
        /\
       /E2E\        <- Few (5-10%)
      /------\
     /Integration\ <- Some (20-30%)
    /------------\
   /    Unit      \ <- Many (60-70%)
  /--------------\
```

We follow the **test pyramid** approach:
- **Many Unit Tests** - Fast, isolated, test individual functions
- **Some Integration Tests** - Test component interactions
- **Few End-to-End Tests** - Test complete user flows

---

## Testing Framework Stack

### Required Tools
- **pytest** - Primary test framework
- **pytest-asyncio** - For async test support
- **httpx** - For HTTP client testing
- **pytest-cov** - For coverage reporting
- **pytest-mock** - For mocking

### Installation
```bash
pip install pytest pytest-asyncio httpx pytest-cov pytest-mock
```

---

## Test Organization

### Directory Structure
```
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_models.py         # Model validation tests
│   ├── test_pagination.py     # Pagination logic tests
│   └── test_errors.py         # Error model tests
├── integration/               # Integration tests
│   ├── test_api_goals.py      # Goals API tests
│   ├── test_api_conversations.py  # Conversations API tests
│   ├── test_api_pagination.py # Pagination endpoint tests
│   └── test_api_errors.py     # Error handling tests
├── e2e/                       # End-to-end tests
│   ├── test_conversation_flow.py  # Complete conversation flow
│   └── test_escalation_flow.py    # Escalation workflow
├── conftest.py                # Shared fixtures
└── README.md                  # Test documentation
```

### File Naming
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_api_<feature>.py`
- E2E tests: `test_<workflow>_flow.py`
- Fixtures: `conftest.py`

---

## Test Naming Conventions

### Function Names
Use descriptive names following this pattern:
```python
def test_<what>_<condition>_<expected>()
```

**Examples:**
```python
# ✅ Good - Clear and descriptive
def test_create_conversation_with_valid_goal_returns_201():
    pass

def test_create_conversation_with_invalid_goal_returns_404():
    pass

def test_list_conversations_with_pagination_returns_correct_count():
    pass

# ❌ Bad - Too vague
def test_conversation():
    pass

def test_create():
    pass
```

### Async Tests
Prefix async test functions with `async`:
```python
@pytest.mark.asyncio
async def test_async_operation_completes_successfully():
    result = await async_function()
    assert result is not None
```

---

## Test Structure (AAA Pattern)

Every test should follow **Arrange-Act-Assert**:

```python
async def test_create_conversation_returns_conversation_id():
    # Arrange - Setup test data and dependencies
    goal_id = "valid_goal_id"
    request_data = {"goal_id": goal_id}
    
    # Act - Execute the operation being tested
    response = await client.post("/v1/conversations/", json=request_data)
    
    # Assert - Verify the expected outcome
    assert response.status_code == 201
    assert "conversation_id" in response.json()
    assert response.json()["goal_id"] == goal_id
```

### Optional: Cleanup
Add cleanup if needed:
```python
async def test_resource_creation():
    # Arrange
    resource = create_resource()
    
    # Act
    result = await process(resource)
    
    # Assert
    assert result is not None
    
    # Cleanup (if needed)
    await delete_resource(resource.id)
```

---

## What to Test

### Unit Tests (60-70%)

#### 1. Model Validation
```python
# Test Pydantic models
def test_message_request_requires_content():
    with pytest.raises(ValidationError):
        MessageRequest()  # Missing required field

def test_message_request_validates_content_length():
    with pytest.raises(ValidationError):
        MessageRequest(content="a" * 10001)  # Exceeds max length

def test_pagination_params_limits_max_value():
    with pytest.raises(ValidationError):
        PaginationParams(limit=101)  # Exceeds max
```

#### 2. Business Logic
```python
# Test pure functions and logic
def test_build_link_header_includes_next_link():
    link = build_link_header("http://api/goals", total=100, limit=50, offset=0)
    assert 'rel="next"' in link
    assert 'offset=50' in link

def test_pagination_calculates_correct_page_numbers():
    result = PaginatedResponse.create(data=[], total=100, limit=50, offset=50)
    assert result.pagination.current_page == 2
    assert result.pagination.total_pages == 2
```

#### 3. Utility Functions
```python
# Test helpers and utilities
def test_get_request_id_extracts_from_header():
    request = Mock()
    request.headers = {"X-Request-ID": "req_123"}
    assert get_request_id(request) == "req_123"

def test_get_request_id_generates_when_missing():
    request = Mock()
    request.headers = {}
    request_id = get_request_id(request)
    assert request_id.startswith("req_")
```

### Integration Tests (20-30%)

#### 1. API Endpoints
```python
# Test endpoint behavior
@pytest.mark.asyncio
async def test_get_goals_returns_paginated_response(client):
    response = await client.get("/v1/goals/?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "object" in data
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 10

@pytest.mark.asyncio
async def test_create_conversation_with_invalid_goal_returns_404(client):
    response = await client.post(
        "/v1/conversations/",
        json={"goal_id": "nonexistent"}
    )
    
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"
    assert error["code"] == "resource_not_found"
```

#### 2. Error Handling
```python
# Test error scenarios
@pytest.mark.asyncio
async def test_missing_required_field_returns_422(client):
    response = await client.post("/v1/conversations/", json={})
    
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert len(error["details"]) > 0

@pytest.mark.asyncio
async def test_invalid_limit_returns_422(client):
    response = await client.get("/v1/goals/?limit=150")
    assert response.status_code == 422
```

#### 3. Response Headers
```python
# Test headers
@pytest.mark.asyncio
async def test_pagination_includes_link_header(client):
    response = await client.get("/v1/goals/?limit=1")
    assert "link" in response.headers
    assert 'rel="next"' in response.headers["link"]

@pytest.mark.asyncio
async def test_pagination_includes_total_count_header(client):
    response = await client.get("/v1/goals/")
    assert "x-total-count" in response.headers
```

### E2E Tests (5-10%)

#### Complete User Flows
```python
@pytest.mark.asyncio
async def test_complete_conversation_flow(client):
    """Test entire conversation lifecycle"""
    
    # 1. Create conversation
    create_response = await client.post(
        "/v1/conversations/",
        json={"goal_id": "valid_goal_id"}
    )
    assert create_response.status_code == 201
    conv_id = create_response.json()["conversation_id"]
    
    # 2. Send message
    msg_response = await client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"content": "Hello", "role": "user"}
    )
    assert msg_response.status_code == 200
    assert msg_response.json()["message_count"] == 2
    
    # 3. Get conversation
    get_response = await client.get(f"/v1/conversations/{conv_id}")
    assert get_response.status_code == 200
    
    # 4. List conversations
    list_response = await client.get("/v1/conversations/")
    assert list_response.status_code == 200
```

---

## Fixtures and Test Data

### Shared Fixtures (conftest.py)
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    """HTTP client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def valid_goal_id():
    """Return a valid goal ID for testing"""
    return "55qZMH6L4bM006573"

@pytest.fixture
async def created_conversation(client, valid_goal_id):
    """Create a conversation for testing"""
    response = await client.post(
        "/v1/conversations/",
        json={"goal_id": valid_goal_id}
    )
    return response.json()["conversation_id"]
```

### Test Data Best Practices
- Use fixtures for reusable test data
- Keep test data minimal and relevant
- Use factories for complex objects
- Avoid hardcoding IDs (except in fixtures)

---

## Assertions

### Good Assertions
```python
# ✅ Specific assertions
assert response.status_code == 200
assert "conversation_id" in data
assert data["pagination"]["has_more"] is True
assert len(data["data"]) == 10

# ✅ Multiple related assertions
response = await client.get("/v1/goals/")
assert response.status_code == 200
data = response.json()
assert "object" in data
assert data["object"] == "goal.list"
assert isinstance(data["data"], list)

# ✅ Error assertions
with pytest.raises(ValidationError) as exc_info:
    Model(invalid_field="value")
assert "field" in str(exc_info.value)
```

### Avoid These
```python
# ❌ Too broad
assert response

# ❌ Testing implementation details
assert len(internal_cache) == 5

# ❌ Multiple unrelated assertions
assert response.status_code == 200 and user.name == "John" and config.debug is False
```

---

## Mocking

### When to Mock
- External API calls (Groq, handoff service)
- Database operations (in unit tests)
- Time-dependent operations
- File I/O operations
- Redis connections

### How to Mock
```python
# Mock external API
@pytest.mark.asyncio
async def test_llm_call_tracks_latency(mocker):
    mock_groq = mocker.patch("app.services.llm_client.Groq")
    mock_groq.return_value.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Response"))]
    )
    
    result = await llm_client.generate("prompt", [])
    assert result == "Response"
    assert mock_groq.called

# Mock database
@pytest.mark.asyncio
async def test_session_manager_creates_session(mocker):
    mock_redis = mocker.patch("app.services.session_manager.redis")
    result = await session_manager.create_session("goal_id")
    assert result.id is not None
```

### Don't Over-Mock
```python
# ❌ Bad - Testing the mock, not the code
def test_function_calls_another_function(mocker):
    mock = mocker.patch("module.function")
    my_function()
    assert mock.called  # Only tests that it was called

# ✅ Good - Test actual behavior
def test_function_returns_correct_result():
    result = my_function(input_data)
    assert result == expected_output
```

---

## Test Coverage

### Coverage Goals
- **Overall:** 80%+ coverage
- **Critical paths:** 95%+ coverage (auth, payments, data mutations)
- **Models:** 90%+ coverage
- **Utilities:** 85%+ coverage

### Running Coverage
```bash
# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Coverage for specific module
pytest --cov=app.routers --cov-report=term
```

### What NOT to Test
- Third-party library internals
- Framework code (FastAPI, Pydantic)
- Configuration files
- Simple getters/setters
- Trivial pass-through functions
- Underlying adapter code (database, API, etc.)

---

## Test Performance

### Speed Guidelines
- Unit test: < 0.1s per test
- Integration test: < 1s per test
- E2E test: < 5s per test
- Full suite: < 30s

### Making Tests Faster
```python
# ✅ Use in-memory databases
@pytest.fixture
async def test_db():
    db = await create_in_memory_db()
    yield db
    await db.close()

# ✅ Mock slow operations
@pytest.mark.asyncio
async def test_operation(mocker):
    mocker.patch("slow_operation", return_value="instant")
    
# ✅ Run tests in parallel
pytest -n auto  # Using pytest-xdist
```

---

## Continuous Integration

### Pre-commit Checks
```bash
# Run these before committing
pytest                          # All tests pass
pytest --cov=app --cov-fail-under=80  # Coverage above 80%
pytest --lf                     # Re-run last failed
```

### CI Pipeline
```yaml
# .github/workflows/tests.yml
- name: Run Tests
  run: |
    pytest --cov=app --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

---

## Testing Checklist

### For Every New Feature
- [ ] Unit tests for models and logic
- [ ] Integration tests for API endpoints
- [ ] Test success scenarios
- [ ] Test error scenarios
- [ ] Test edge cases
- [ ] Test validation rules
- [ ] Update fixtures if needed
- [ ] Coverage stays above 80%

### For Every Bug Fix
- [ ] Write test that reproduces the bug
- [ ] Verify test fails before fix
- [ ] Fix the bug
- [ ] Verify test passes after fix
- [ ] Add regression test

---

## Common Patterns

### Testing Pagination
```python
@pytest.mark.asyncio
async def test_pagination_returns_correct_structure(client):
    response = await client.get("/v1/resources/?limit=10&offset=0")
    data = response.json()
    
    assert "object" in data
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["offset"] == 0
    assert "has_more" in data["pagination"]
```

### Testing Error Responses
```python
@pytest.mark.asyncio
async def test_error_has_standard_format(client):
    response = await client.get("/v1/resources/nonexistent")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    
    error = data["error"]
    assert "type" in error
    assert "code" in error
    assert "message" in error
    assert "request_id" in error
    assert "timestamp" in error
```

### Testing WebSockets
```python
@pytest.mark.asyncio
async def test_websocket_connection(client):
    async with client.websocket_connect("/v1/ws/conversation/123") as ws:
        # Send message
        await ws.send_json({"content": "Hello"})
        
        # Receive response
        response = await ws.receive_json()
        assert response["type"] == "message"
```

---

## Anti-Patterns to Avoid

### ❌ Brittle Tests
```python
# Don't test exact strings or implementation details
assert response.text == "User created at 2025-10-24 10:00:00"

# Do test structure and behavior
assert response.status_code == 201
assert "created_at" in response.json()
```

### ❌ Dependent Tests
```python
# Don't rely on test execution order
def test_create():
    global user_id
    user_id = create_user()

def test_update():
    update_user(user_id)  # Depends on test_create
```

### ❌ Unclear Tests
```python
# Don't use magic numbers or unclear names
def test_api():
    r = await c.post("/api/res", json={"a": "b"})
    assert r.status_code == 201
```

---

## Why These Conventions Are Better

### 1. **Clear Organization**
- **Problem:** Mixed unit/integration/e2e tests hard to run selectively
- **Solution:** Separate directories for each test type
- **Benefit:** Run only what you need (`pytest tests/unit/`)

### 2. **Descriptive Names**
- **Problem:** `test_conversation()` tells you nothing
- **Solution:** `test_create_conversation_with_valid_goal_returns_201()`
- **Benefit:** Failures immediately show what broke

### 3. **AAA Pattern**
- **Problem:** Hard to understand what test is doing
- **Solution:** Clear Arrange-Act-Assert sections
- **Benefit:** Easy to read and maintain

### 4. **Test Pyramid**
- **Problem:** Only E2E tests are slow and brittle
- **Solution:** Many fast unit tests, few slow E2E tests
- **Benefit:** Fast feedback loop, reliable tests

### 5. **Fixtures**
- **Problem:** Repeated setup code in every test
- **Solution:** Reusable fixtures in conftest.py
- **Benefit:** DRY principle, easier maintenance

### 6. **Coverage Goals**
- **Problem:** Don't know what's tested
- **Solution:** Measure and enforce coverage minimums
- **Benefit:** Confidence in code quality

### 7. **Speed Requirements**
- **Problem:** Slow tests discourage running them
- **Solution:** Performance guidelines and optimization
- **Benefit:** Tests run frequently, catch bugs early

---

## References

- pytest Documentation: https://docs.pytest.org/
- Test Pyramid: Martin Fowler
- AAA Pattern: Arrange-Act-Assert
- Test Coverage: pytest-cov
- Async Testing: pytest-asyncio

