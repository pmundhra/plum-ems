"""Prometheus metrics definitions"""

from prometheus_client import Counter, Histogram, Gauge

# HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path", "method"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
)

# API Error Metrics
API_ERRORS_TOTAL = Counter(
    "api_errors_total",
    "Total API errors",
    ["error_type", "error_code", "path"],
)

# Endorsement Metrics
ENDORSEMENTS_CREATED_TOTAL = Counter(
    "endorsements_created_total",
    "Total endorsements created",
    ["type", "employer_id"],
)

ENDORSEMENTS_PROCESSED_TOTAL = Counter(
    "endorsements_processed_total",
    "Total endorsements processed",
    ["status", "type"],
)

ENDORSEMENT_PROCESSING_DURATION = Histogram(
    "endorsement_processing_duration_seconds",
    "Endorsement processing duration",
    ["type", "status"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

# Ledger Metrics
LEDGER_BALANCE = Gauge(
    "ledger_balance",
    "Current ledger balance",
    ["employer_id"],
)

LEDGER_TRANSACTIONS_TOTAL = Counter(
    "ledger_transactions_total",
    "Total ledger transactions",
    ["type", "status"],
)

LEDGER_LOW_BALANCE_ALERTS = Counter(
    "ledger_low_balance_alerts_total",
    "Total low balance alerts",
    ["employer_id"],
)

# Insurer Gateway Metrics
INSURER_REQUESTS_TOTAL = Counter(
    "insurer_requests_total",
    "Total insurer API requests",
    ["insurer_id", "protocol", "status"],
)

INSURER_REQUEST_DURATION = Histogram(
    "insurer_request_duration_seconds",
    "Insurer API request duration",
    ["insurer_id", "protocol"],
    buckets=[0.25, 0.5, 1, 2, 5, 10, 30],
)

INSURER_REQUEST_FAILURES = Counter(
    "insurer_request_failures_total",
    "Total insurer API failures",
    ["insurer_id", "protocol", "error_type"],
)

# Kafka Metrics
KAFKA_MESSAGES_PRODUCED = Counter(
    "kafka_messages_produced_total",
    "Total Kafka messages produced",
    ["topic"],
)

KAFKA_MESSAGES_CONSUMED = Counter(
    "kafka_messages_consumed_total",
    "Total Kafka messages consumed",
    ["topic", "consumer_group"],
)

KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag",
    ["topic", "consumer_group"],
)

# Database Metrics
DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["database", "operation"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["database", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1],
)

# WebSocket Metrics
WS_CONNECTIONS_ACTIVE = Gauge(
    "ws_connections_active",
    "Active WebSocket connections",
)

WS_MESSAGES_TOTAL = Counter(
    "ws_messages_total",
    "Total WebSocket messages",
    ["direction"],  # inbound, outbound
)

# Analytics Metrics
ANOMALY_DETECTIONS_TOTAL = Counter(
    "anomaly_detections_total",
    "Total anomaly detections",
    ["employer_id", "anomaly_type"],
)

CIRCUIT_BREAKER_TRIGGERED = Counter(
    "circuit_breaker_triggered_total",
    "Total circuit breaker triggers",
    ["employer_id", "service"],
)
