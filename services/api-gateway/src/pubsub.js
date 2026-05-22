/**
 * PubSub — In-memory event bus for GraphQL subscriptions.
 * Connects Kafka consumers to WebSocket clients.
 *
 * Topics:
 *   PATIENT_ALERT    — anomaly alerts from NLP service
 *   VITAL_UPDATE     — new vital signs from Kafka
 *   CAUSAL_DRIFT     — causal graph changes
 *   COLLAB_SESSION   — multi-doctor session events
 */

import { EventEmitter } from "events";

class PubSub {
  constructor() {
    this.emitter = new EventEmitter();
    this.emitter.setMaxListeners(100);
    this.subscriptions = new Map();
    this.counter = 0;
  }

  publish(topic, payload) {
    this.emitter.emit(topic, payload);
  }

  subscribe(topic, onMessage) {
    const id = ++this.counter;
    this.emitter.on(topic, onMessage);
    this.subscriptions.set(id, { topic, onMessage });
    return id;
  }

  unsubscribe(id) {
    const sub = this.subscriptions.get(id);
    if (sub) {
      this.emitter.off(sub.topic, sub.onMessage);
      this.subscriptions.delete(id);
    }
  }

  asyncIterator(topics) {
    const topicArray = Array.isArray(topics)
      ? topics
      : [topics];
    const queue = [];
    const listeners = [];
    let resolve = null;

    topicArray.forEach((topic) => {
      const listener = (payload) => {
        if (resolve) {
          resolve({ value: payload, done: false });
          resolve = null;
        } else {
          queue.push(payload);
        }
      };
      this.emitter.on(topic, listener);
      listeners.push({ topic, listener });
    });

    return {
      [Symbol.asyncIterator]() {
        return this;
      },
      next() {
        if (queue.length > 0) {
          return Promise.resolve({
            value: queue.shift(),
            done: false,
          });
        }
        return new Promise((res) => {
          resolve = res;
        });
      },
      return() {
        listeners.forEach(({ topic, listener }) => {
          this.emitter?.off(topic, listener);
        });
        return Promise.resolve({ done: true });
      },
    };
  }
}

export const pubsub = new PubSub();

export const TOPICS = {
  PATIENT_ALERT:  "PATIENT_ALERT",
  VITAL_UPDATE:   "VITAL_UPDATE",
  CAUSAL_DRIFT:   "CAUSAL_DRIFT",
  COLLAB_SESSION: "COLLAB_SESSION",
};