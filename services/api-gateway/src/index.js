/**
 * Axiom API Gateway
 * Apollo GraphQL Server 5 (standalone) + WebSocket
 * Port 4000
 */

import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import { makeExecutableSchema } from "@graphql-tools/schema";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { useServer } from "graphql-ws/use/ws";

import { typeDefs } from "./schema.js";
import { resolvers } from "./resolvers.js";
import { pubsub } from "./pubsub.js";
import { createKafkaConsumer } from "./kafka.js";

const PORT = 4000;
const WS_PORT = 4001;

export const SERVICES = {
  causal:    "http://localhost:8081",
  survival:  "http://localhost:8082",
  nlp:       "http://localhost:8083",
  zk:        "http://localhost:8084",
  federated: "http://localhost:8085",
};

// ── GraphQL HTTP server (port 4000) ───────────────
const schema = makeExecutableSchema({ typeDefs, resolvers });

const apolloServer = new ApolloServer({ schema });

const { url } = await startStandaloneServer(apolloServer, {
  listen: { port: PORT },
  context: async () => ({ services: SERVICES, pubsub }),
});

console.log(`GraphQL: ${url}`);

// ── WebSocket server for subscriptions (port 4001) 
const wsHttpServer = createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({
      status:    "healthy",
      service:   "axiom-api-gateway",
      version:   "0.7.0",
      graphql:   `http://localhost:${PORT}/`,
      websocket: `ws://localhost:${WS_PORT}/graphql`,
      timestamp: new Date().toISOString(),
    }));
    return;
  }
  if (req.method === "POST" && req.url?.startsWith("/test/alert/")) {
    const patientId = req.url.split("/test/alert/")[1];
    pubsub.publish("PATIENT_ALERT", {
      patientAlerts: {
        alertId:      "test-" + Date.now(),
        patientId,
        alertType:    "PREDICTIVE",
        feature:      "creatinine",
        currentValue: 4.0,
        threshold:    3.5,
        severity:     "WARNING",
        message:      "Test: creatinine rising",
        zkProofHash:  null,
        zkProven:     false,
        acknowledged: false,
        createdAt:    new Date().toISOString(),
      },
    });
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ published: true, patientId }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const wsServer = new WebSocketServer({
  server: wsHttpServer,
  path: "/graphql",
});

useServer(
  {
    schema,
    context: () => ({ services: SERVICES, pubsub }),
  },
  wsServer
);

wsHttpServer.listen(WS_PORT, () => {
  console.log(`WebSocket: ws://localhost:${WS_PORT}/graphql`);
  console.log(`Health:    http://localhost:${WS_PORT}/health`);
});

// ── Kafka consumer ────────────────────────────────
try {
  await createKafkaConsumer(pubsub);
  console.log("Kafka consumer started");
} catch (err) {
  console.warn("Kafka unavailable:", err.message);
}