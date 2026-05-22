import { TOPICS } from "./pubsub.js";

export const resolvers = {
  Query: {
    health: () => ({
      status: "healthy",
      service: "axiom-api-gateway",
      version: "0.7.0",
    }),
    patient: async (_, { id }, { services }) => {
      try {
        const res = await fetch(
          `${services.causal}/causal/full/${id}`
        );
        const data = await res.json();
        return {
          id,
          name: data.patient_id || id,
          fhirId: data.patient_id,
        };
      } catch {
        return { id, name: null, fhirId: null };
      }
    },
  },

  Subscription: {
    patientAlerts: {
      subscribe: (_, { patientId }, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.PATIENT_ALERT]),
      resolve: (payload) => payload.patientAlerts,
    },
    vitalUpdates: {
      subscribe: (_, { patientId }, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.VITAL_UPDATE]),
      resolve: (payload) => payload.vitalUpdates,
    },
  },
};