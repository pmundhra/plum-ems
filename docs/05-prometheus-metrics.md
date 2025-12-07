# Prometheus Metrics Guidelines

## Overview
Implement comprehensive metrics collection using Prometheus for observability, monitoring, and alerting. Track API performance, errors, and business metrics.

## Rules

### 1. Metrics Endpoint
Expose metrics at `/metrics`:
```python
from prometheus_client import make_asgi_app

# app/routers/metrics.py
metrics_app = make_asgi_app()
router = APIRouter()

@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 2. Core Metric Types

#### Counter - Monotonically Increasing
For counting events that only go up:
```python
from prometheus_client import Counter

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"]
)

# Usage
REQUEST_COUNT.labels(path="/v1/goals/", method="GET", status="200").inc()
```

#### Histogram - Distributions and Quantiles
For measuring durations and sizes:
```python
from prometheus_client import Histogram

LLM_LATENCY = Histogram(
    "groq_llm_latency_seconds",
    "Latency of Groq API calls",
    ["model", "stream_mode"],
    buckets=[0.25, 0.5, 1, 2, 5, 10]
)

# Usage
start = time.time()
# ... operation ...
duration = time.time() - start
LLM_LATENCY.labels(model="llama-3.1-8b", stream_mode="streaming").observe(duration)
```

#### Gauge - Up and Down Values
For values that can increase and decrease:
```python
from prometheus_client import Gauge

ACTIVE_CONVERSATIONS = Gauge(
    "active_conversations_total",
    "Number of active conversations"
)

# Usage
ACTIVE_CONVERSATIONS.inc()  # Increment
ACTIVE_CONVERSATIONS.dec()  # Decrement
ACTIVE_CONVERSATIONS.set(42)  # Set to specific value
```

#### Summary - Similar to Histogram
For calculating quantiles on client side:
```python
from prometheus_client import Summary

REQUEST_DURATION = Summary(
    "request_duration_seconds",
    "Request duration"
)

# Usage
with REQUEST_DURATION.time():
    # ... operation ...
    pass
```

### 3. Naming Conventions

#### Metric Names
- Use `snake_case`
- Include unit suffix: `_seconds`, `_bytes`, `_total`
- Start with domain: `http_`, `llm_`, `db_`, `ws_`

```python
# Good
http_requests_total
llm_latency_seconds
db_queries_total
ws_connections_active

# Bad
HTTPRequests
latency
requests
connection
```

#### Label Names
- Use lowercase
- Be specific but concise
- Avoid high cardinality (e.g., user_id, conversation_id)

```python
# Good
labels=["path", "method", "status_code"]

# Bad
labels=["conversation_id", "timestamp"]  # Too high cardinality
```

### 4. Essential Metrics to Track

#### HTTP Requests
```python
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["path", "method"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)
```

#### API Errors
```python
API_ERRORS_TOTAL = Counter(
    "api_errors_total",
    "Total API errors",
    ["error_type", "error_code", "path"]
)
```

#### LLM Metrics
```python
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "stream_mode", "status"]
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "LLM request latency",
    ["model", "stream_mode"],
    buckets=[0.25, 0.5, 1, 2, 5, 10]
)

LLM_TOKENS_USED = Counter(
    "llm_tokens_used_total",
    "Total tokens used",
    ["model", "type"]  # type: prompt, completion, total
)
```

#### WebSocket Metrics
```python
WS_CONNECTIONS_ACTIVE = Gauge(
    "ws_connections_active",
    "Active WebSocket connections"
)

WS_MESSAGES_TOTAL = Counter(
    "ws_messages_total",
    "Total WebSocket messages",
    ["direction"]  # inbound, outbound
)
```

#### Business Metrics
```python
CONVERSATIONS_CREATED = Counter(
    "conversations_created_total",
    "Total conversations created",
    ["goal_id"]
)

ESCALATIONS_TOTAL = Counter(
    "escalations_total",
    "Total conversation escalations",
    ["reason"]
)
```

### 5. Middleware Integration
Add metrics middleware to track all requests:
```python
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    
    # Track request
    REQUEST_COUNT.labels(
        path=request.url.path,
        method=request.method
    ).inc()
    
    # Process request
    response = await call_next(request)
    
    # Track duration
    duration = time.time() - start
    HTTP_REQUEST_DURATION.labels(
        path=request.url.path,
        method=request.method
    ).observe(duration)
    
    # Track status
    REQUEST_COUNT.labels(
        path=request.url.path,
        method=request.method,
        status=str(response.status_code)
    ).inc()
    
    return response
```

### 6. Time to First Token (TTFT)
For streaming responses, track TTFT:
```python
start_time = time.time()
first_token_time = None

for chunk in stream:
    if first_token_time is None:
        first_token_time = time.time() - start_time
        TTFT_HISTOGRAM.labels(model=model).observe(first_token_time)
```

### 7. Bucket Configuration
Choose appropriate histogram buckets:

```python
# Fast operations (< 1 second)
buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1]

# Medium operations (1-10 seconds)
buckets=[0.25, 0.5, 1, 2, 5, 10]

# Slow operations (10+ seconds)
buckets=[1, 5, 10, 30, 60, 120]
```

### 8. Integration with Logging
Combine metrics with structured logging:
```python
start = time.time()
logger.info("llm_request_started", model=model)

try:
    result = await llm.generate(...)
    duration = time.time() - start
    
    # Record metric
    LLM_LATENCY.labels(model=model).observe(duration)
    
    # Log success
    logger.info("llm_request_completed", model=model, latency=duration)
    
except Exception as e:
    # Record error metric
    LLM_ERRORS.labels(model=model, error=type(e).__name__).inc()
    
    # Log error
    logger.error("llm_request_failed", model=model, error=str(e))
    raise
```

## Implementation Checklist

- [ ] Prometheus client library installed
- [ ] `/metrics` endpoint exposed
- [ ] HTTP request metrics tracked
- [ ] Error metrics tracked
- [ ] LLM latency metrics tracked
- [ ] WebSocket metrics tracked (if applicable)
- [ ] Business metrics tracked
- [ ] Appropriate labels used (low cardinality)
- [ ] Histogram buckets appropriate for operation
- [ ] Middleware captures all requests

## Querying Metrics

### Prometheus Query Examples

```promql
# Request rate per second
rate(http_requests_total[5m])

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(api_errors_total[5m]) / rate(http_requests_total[5m])

# LLM time to first token
histogram_quantile(0.95, rate(llm_ttft_seconds_bucket[5m]))
```

## Grafana Dashboard

Create dashboards to visualize:
- Request rate and latency
- Error rates by type
- LLM performance (latency, TTFT)
- Active connections
- Business metrics (conversations, escalations)

## Alerting Rules

```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API latency is high"
          
      - alert: LLMServiceDown
        expr: rate(llm_requests_total[5m]) == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "LLM service appears to be down"
```

## Testing Requirements

- [ ] `/metrics` endpoint returns Prometheus format
- [ ] Metrics increment correctly
- [ ] Labels are applied correctly
- [ ] Histograms record in appropriate buckets
- [ ] Gauges increase and decrease correctly
- [ ] No high-cardinality labels used

## Anti-Patterns to Avoid

### ❌ High Cardinality Labels
```python
# DON'T - Too many unique values
METRIC = Counter("requests", "Requests", ["user_id", "conversation_id"])
```

### ❌ Including Timestamps
```python
# DON'T - Prometheus adds timestamps
METRIC = Counter("requests", "Requests", ["timestamp"])
```

### ❌ Using Gauges for Counters
```python
# DON'T - Use Counter instead
REQUESTS = Gauge("requests_total", "Requests")
REQUESTS.inc()  # Wrong metric type
```

### ✅ Correct Patterns
```python
# DO - Low cardinality labels
METRIC = Counter("requests", "Requests", ["path", "method", "status"])

# DO - Use appropriate metric types
REQUESTS = Counter("requests_total", "Total requests")
LATENCY = Histogram("request_duration_seconds", "Request duration")
ACTIVE = Gauge("active_connections", "Active connections")
```

## Performance Impact

- Metrics collection is fast (< 1ms overhead)
- Use sampling for very high-frequency events
- Avoid too many labels or metric instances
- Keep histogram buckets reasonable (< 20 buckets)

## References
- Prometheus Documentation: https://prometheus.io/docs/
- Best Practices: https://prometheus.io/docs/practices/naming/
- Histograms: https://prometheus.io/docs/practices/histograms/
- Python Client: https://github.com/prometheus/client_python

