/**
 * Axiom API Gateway
 * Node.js + Apollo GraphQL Server (standalone)
 * Port 4000
 */

import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import { typeDefs } from "./schema.js";
import { resolvers } from "./resolvers.js";
import { pubsub } from "./pubsub.js";
import { createKafkaConsumer } from "./kafka.js";

const PORT = 4000;

export const SERVICES = {
  causal:    "http://localhost:8081",
  survival:  "http://localhost:8082",
  nlp:       "http://localhost:8083",
  zk:        "http://localhost:8084",
  federated: "http://localhost:8085",
  fhir:      "http://localhost:8080",
};

const server = new ApolloServer({ typeDefs, resolvers });

const { url } = await startStandaloneServer(server, {
  listen: { port: PORT },
  context: async () => ({ services: SERVICES, pubsub }),
});

console.log(`Axiom API Gateway running at ${url}`);
console.log(`Health: http://localhost:${PORT}/health`);

// Start Kafka consumer
try {
  await createKafkaConsumer(pubsub);
  console.log("Kafka consumer started");
} catch (err) {
  console.warn("Kafka unavailable:", err.message);
}