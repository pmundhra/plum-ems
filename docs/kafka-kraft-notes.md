# Kafka KRaft Mode Notes

## Overview

We use **Kafka KRaft (Kafka Raft) mode** instead of the traditional Zookeeper-based setup. This simplifies our infrastructure and is the recommended approach for new deployments.

## What is KRaft?

KRaft (Kafka Raft) is a consensus protocol that eliminates the need for Apache Zookeeper by integrating metadata management directly into Kafka brokers. It was introduced as an experimental feature in Kafka 2.8.0 and became production-ready in Kafka 3.3.0.

## Advantages of KRaft Mode

1. **Simpler Infrastructure**
   - No need to run and maintain Zookeeper
   - One less service to monitor and manage
   - Reduced operational complexity

2. **Better Performance**
   - Lower latency for metadata operations
   - Faster controller failover (seconds vs minutes)
   - More efficient metadata replication

3. **Easier Operations**
   - Simpler deployment and configuration
   - Easier to scale and maintain
   - Better observability

4. **Future-Proof**
   - Zookeeper is deprecated in Kafka 3.5+
   - Zookeeper will be removed in Kafka 4.0+
   - KRaft is the future of Kafka

## Disadvantages / Considerations

1. **Newer Technology**
   - KRaft became production-ready in Kafka 3.3.0 (released in 2022)
   - Some older tooling might still expect Zookeeper
   - Most modern tools (including Confluent Platform 7.0+) support KRaft

2. **Migration Path**
   - If you have existing Zookeeper-based clusters, migration requires planning
   - For new deployments (like ours), this is not a concern

3. **Learning Curve**
   - Slightly different configuration parameters
   - Team needs to understand KRaft concepts (minimal difference)

## Our Configuration

We use **Confluent Platform 7.6.0** with KRaft mode enabled. The configuration:

- Single-node setup for local development
- Combined broker and controller roles (`KAFKA_PROCESS_ROLES: broker,controller`)
- Proper listener configuration for internal and external access
- Health checks to ensure Kafka is ready before starting the app
- **Auto-topic creation enabled**: Topics are automatically created when messages are produced to non-existent topics

### Auto-Topic Creation

We have enabled automatic topic creation with the following defaults:

- **`KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`**: Automatically creates topics when a producer sends a message to a non-existent topic
- **`KAFKA_NUM_PARTITIONS: 3`**: Default number of partitions for auto-created topics (good for development and small-scale production)
- **`KAFKA_DEFAULT_REPLICATION_FACTOR: 1`**: Default replication factor (appropriate for single-node local setup)
- **`KAFKA_LOG_RETENTION_HOURS: 168`**: Default retention of 7 days
- **`KAFKA_LOG_CLEANUP_POLICY: delete`**: Default cleanup policy (delete old messages)

**Note**: For production, you should explicitly create topics with appropriate configurations rather than relying on auto-creation. Auto-creation is convenient for development but may not meet production requirements for partitions, replication, and retention policies.

## Production Considerations

For production deployments:

1. **Multi-Node Setup**: Use separate controller and broker nodes for better scalability
2. **Replication**: Configure proper replication factors for topics
3. **Monitoring**: Use Kafka's built-in metrics and monitoring tools
4. **Backup**: Implement proper backup strategies for metadata and data

## References

- [Apache Kafka KRaft Documentation](https://kafka.apache.org/documentation/#kraft)
- [Confluent KRaft Guide](https://docs.confluent.io/platform/current/kafka/kraft/index.html)
- Kafka 3.3+ release notes for production-ready KRaft
