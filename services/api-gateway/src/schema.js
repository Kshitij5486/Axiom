export const typeDefs = `#graphql

  type Health {
    status: String!
    service: String!
    version: String!
  }

  type Patient {
    id: ID!
    name: String
    fhirId: String
  }

  type Query {
    health: Health!
    patient(id: ID!): Patient
  }

  type Subscription {
    patientAlerts(patientId: ID!): Alert
    vitalUpdates(patientId: ID!): VitalUpdate
  }

  type Alert {
    alertId: String
    patientId: String
    alertType: String
    feature: String
    currentValue: Float
    threshold: Float
    severity: String
    message: String
    zkProofHash: String
    zkProven: Boolean
    timestamp: String
  }

  type VitalUpdate {
    patientId: String
    feature: String
    value: Float
    timestamp: String
  }
`;