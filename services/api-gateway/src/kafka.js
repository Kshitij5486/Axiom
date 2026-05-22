/**
 * Kafka Consumer for GraphQL Subscriptions
 *
 * Consumes from:
 *   alerts.clinical  → PATIENT_ALERT topic
 *   patient.vitals   → VITAL_UPDATE topic
 *
 * Publishes to PubSub which delivers to
 * WebSocket clients via GraphQL subscriptions.
 */

import { Kafka } from "kafkajs";
import { TOPICS } from "./pubsub.js";

const kafka = new Kafka({
  clientId: "axiom-api-gateway",
  brokers: ["localhost:9094"],
  retry: { retries: 3 },
});

export async function createKafkaConsumer(pubsub) {
  const consumer = kafka.consumer({
    groupId: "api-gateway-group",
  });

  await consumer.connect();

  await consumer.subscribe({
    topics: ["alerts.clinical", "patient.vitals"],
    fromBeginning: false,
  });

  await consumer.run({
    eachMessage: async ({ topic, message }) => {
      try {
        const payload = JSON.parse(
          message.value.toString()
        );

        if (topic === "alerts.clinical") {
          pubsub.publish(TOPICS.PATIENT_ALERT, {
            patientAlerts: {
              ...payload,
              subscriptionTopic: "patientAlerts",
            },
          });
        } else if (topic === "patient.vitals") {
          pubsub.publish(TOPICS.VITAL_UPDATE, {
            vitalUpdates: {
              ...payload,
              subscriptionTopic: "vitalUpdates",
            },
          });
        }
      } catch (err) {
        console.error("Kafka message parse error:", err);
      }
    },
  });

  console.log("Kafka consumer subscribed to topics");
  return consumer;
}