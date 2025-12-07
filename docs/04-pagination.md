# Pagination Guidelines

## Overview
All list endpoints MUST support pagination to prevent large response payloads and ensure good performance. Follow GitHub/Stripe/OpenAI patterns.

## Rules

### 1. Pagination Response Format
ALL list endpoints MUST return this structure:
```json
{
  "object": "resource.list",
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true,
    "current_page": 1,
    "total_pages": 3
  }
}
```

### 2. Query Parameters
Standard pagination parameters:
- `limit` (integer, 1-100, default: 50) - Items per page
- `offset` (integer, >=0, default: 0) - Items to skip

```python
@router.get("/")
async def list_resources(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    # Implementation
```

### 3. Response Headers
Include pagination headers:
```python
# X-Total-Count header
response.headers["X-Total-Count"] = str(total)

# Link header (RFC 5988)
link_header = build_link_header(base_url, total, limit, offset)
if link_header:
    response.headers["Link"] = link_header
```

### 4. Link Header Format
Follow RFC 5988 for navigation links:
```http
Link: <url?limit=50&offset=0>; rel="first",
      <url?limit=50&offset=50>; rel="next",
      <url?limit=50&offset=100>; rel="last"
```

Relations:
- `rel="first"` - First page
- `rel="prev"` - Previous page (if not on first)
- `rel="next"` - Next page (if has_more)
- `rel="last"` - Last page

### 5. Using PaginatedResponse
Use the generic wrapper:
```python
from app.models.pagination import PaginatedResponse

return PaginatedResponse.create(
    data=items,
    total=total_count,
    limit=limit,
    offset=offset,
    object_type="conversation.list"
)
```

### 6. Limit Validation
Enforce reasonable limits:
- Minimum: 1 item
- Maximum: 100 items
- Default: 50 items

```python
limit: int = Query(50, ge=1, le=100, description="Items per page")
```

### 7. Filtering with Pagination
Filters MUST be applied before pagination:
```python
# 1. Get all items
all_items = await get_all()

# 2. Apply filters
if filter_param:
    filtered_items = [i for i in all_items if matches(i, filter_param)]

# 3. Get total of filtered results
total = len(filtered_items)

# 4. Apply pagination
paginated_items = filtered_items[offset:offset + limit]
```

### 8. Object Type Naming
Use consistent naming:
- `goal.list` for goals
- `conversation.list` for conversations
- `resource.list` for generic resources

### 9. Metadata Fields
Required pagination metadata:
- `total` - Total items across all pages
- `limit` - Current page size
- `offset` - Current offset
- `has_more` - Boolean for more pages
- `current_page` - 1-indexed page number
- `total_pages` - Total number of pages

### 10. Page Calculations
```python
current_page = (offset // limit) + 1 if limit > 0 else 1
total_pages = ceil(total / limit) if limit > 0 else 0
has_more = (offset + len(data)) < total
```

## Implementation Checklist

- [ ] All list endpoints use pagination
- [ ] Query parameters validated (limit 1-100)
- [ ] Returns PaginatedResponse format
- [ ] Includes X-Total-Count header
- [ ] Includes Link header with navigation
- [ ] Filtering works with pagination
- [ ] Object type consistently named
- [ ] Page calculations accurate

## Endpoint Pattern

```python
@router.get("/")
async def list_resources(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # Add filter parameters
    filter_field: str = Query(None, description="Filter by field")
):
    """List resources with pagination"""
    
    # 1. Get and filter data
    all_items = await repository.get_all()
    if filter_field:
        all_items = [i for i in all_items if i.field == filter_field]
    
    # 2. Calculate total
    total = len(all_items)
    
    # 3. Apply pagination
    paginated = all_items[offset:offset + limit]
    
    # 4. Build response
    data = [item.dict() for item in paginated]
    
    # 5. Add headers
    base_url = str(request.url).split('?')[0]
    link_header = build_link_header(base_url, total, limit, offset)
    if link_header:
        response.headers["Link"] = link_header
    response.headers["X-Total-Count"] = str(total)
    
    # 6. Return paginated response
    return PaginatedResponse.create(
        data=data,
        total=total,
        limit=limit,
        offset=offset,
        object_type="resource.list"
    )
```

## Client Usage Examples

### Python
```python
# Get first page
response = requests.get('http://api/v1/resources/', params={
    'limit': 50,
    'offset': 0
})
data = response.json()

# Navigate to next page
if data['pagination']['has_more']:
    next_offset = data['pagination']['offset'] + data['pagination']['limit']
    next_response = requests.get('http://api/v1/resources/', params={
        'limit': 50,
        'offset': next_offset
    })
```

### JavaScript
```javascript
// Fetch all pages
async function fetchAll() {
    let offset = 0;
    const limit = 50;
    const items = [];
    
    while (true) {
        const response = await fetch(`/v1/resources/?limit=${limit}&offset=${offset}`);
        const data = await response.json();
        
        items.push(...data.data);
        
        if (!data.pagination.has_more) break;
        offset += limit;
    }
    
    return items;
}
```

## Performance Considerations

### Database Pagination
For database-backed lists, push pagination to DB:
```python
# Good - paginate in database
items = await db.query(Model).offset(offset).limit(limit).all()
total = await db.query(Model).count()

# Bad - fetch all then paginate
all_items = await db.query(Model).all()  # Loads everything!
paginated = all_items[offset:offset + limit]
```

### Caching
Consider caching for stable datasets:
```python
@cache(ttl=300)  # 5 minute cache
async def get_goals_page(limit: int, offset: int):
    # Expensive operation
    return items
```

## Testing Requirements

- [ ] Test default pagination (limit=50, offset=0)
- [ ] Test custom limits (1, 10, 100)
- [ ] Test page navigation (offset=50, 100, etc.)
- [ ] Test limit > 100 returns 422
- [ ] Test offset < 0 returns 422
- [ ] Test Link header includes correct relations
- [ ] Test X-Total-Count matches total
- [ ] Test filtering works with pagination
- [ ] Test has_more is accurate
- [ ] Test page calculations are correct

## Common Pitfalls

### ❌ Forgetting to Count Before Filtering
```python
# Wrong - total is for all items, not filtered
total = len(all_items)
filtered = [i for i in all_items if matches(i)]
paginated = filtered[offset:offset + limit]
```

### ✅ Count After Filtering
```python
# Correct
filtered = [i for i in all_items if matches(i)]
total = len(filtered)  # Total of filtered results
paginated = filtered[offset:offset + limit]
```

### ❌ Inconsistent Ordering
```python
# Wrong - order may change between requests
items = set(all_items)  # Sets are unordered!
```

### ✅ Consistent Ordering
```python
# Correct - maintain consistent order
items = sorted(all_items, key=lambda x: x.created_at)
```

## Future: Cursor-Based Pagination

For real-time or very large datasets:
```json
{
  "object": "list",
  "data": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJpZCI6IjEyMyJ9"
  }
}
```

Models already exist in `app/models/pagination.py` for future implementation.

## References
- GitHub API: Link headers and X-Total-Count
- Stripe API: `has_more` and list object format
- OpenAI API: Similar list structure
- RFC 5988: Web Linking (Link header format)

