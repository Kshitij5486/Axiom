export const typeDefs = `#graphql

  # ── Core Patient Types ─────────────────────────

  type Patient {
    id:           ID!
    name:         String
    fhirId:       String
    causalGraph:  CausalGraph
    survival:     SurvivalAnalysis
    recommendation: Recommendation
    activeAlerts: [Alert!]
    nlpEntities:  [NLPEntity!]
    vitals:       VitalSigns
  }

  type VitalSigns {
    glucose:      Float
    creatinine:   Float
    heartRate:    Float
    systolicBp:   Float
    spo2:         Float
    recordedAt:   String
  }

  # ── Causal Graph Types ──────────────────────────

  type CausalGraph {
    patientId:    String!
    graphId:      String
    nodeCount:    Int
    edgeCount:    Int
    nodes:        [CausalNode!]
    edges:        [CausalEdge!]
    topEffects:   [CausalEffect!]
    zkProof:      String
    builtAt:      String
  }

  type CausalNode {
    id:           String!
    label:        String!
  }

  type CausalEdge {
    source:       String!
    target:       String!
    effect:       Float
    samples:      Int
    blended:      Boolean
    nlpSource:    Boolean
    zkProven:     Boolean
  }

  type CausalEffect {
    treatment:    String!
    outcome:      String!
    effect:       Float!
    samples:      Int
    confidence:   Float
  }

  # ── Survival Analysis Types ─────────────────────

  type SurvivalAnalysis {
    patientId:        String!
    riskScore:        Float
    medianSurvivalDays: Int
    survivalCurve:    SurvivalCurve
    confidenceBands:  ConfidenceBands
  }

  type SurvivalCurve {
    day30:    Float
    day60:    Float
    day90:    Float
    day180:   Float
    day365:   Float
  }

  type ConfidenceBands {
    day30:  ConfidenceInterval
    day60:  ConfidenceInterval
    day90:  ConfidenceInterval
    day180: ConfidenceInterval
    day365: ConfidenceInterval
  }

  type ConfidenceInterval {
    lower: Float
    upper: Float
  }

  # ── Treatment Recommendation Types ─────────────

  type Recommendation {
    patientId:        String!
    recommendedAction: String
    targetVital:      String
    policy:           String
    rankedActions:    [RankedAction!]
    zkProofHash:      String
    zkProven:         Boolean
    auditRecId:       String
    auditLogged:      Boolean
  }

  type RankedAction {
    actionId:        Int
    actionName:      String!
    target:          String
    immediateReward: Float
  }

  # ── Alert Types ─────────────────────────────────

  type Alert {
    alertId:          String!
    patientId:        String!
    alertType:        String!
    feature:          String!
    currentValue:     Float
    threshold:        Float
    severity:         String!
    message:          String
    predictedValue2h: Float
    zkProofHash:      String
    zkProven:         Boolean
    acknowledged:     Boolean
    createdAt:        String
  }

  # ── NLP Types ───────────────────────────────────

  type NLPEntity {
    text:        String!
    label:       String!
    canonical:   String!
    confidence:  Float
    model:       String
  }

  type NLPRelation {
    cause:      String
    effect:     String!
    direction:  String!
    confidence: Float!
    nlpEffect:  Float
    evidence:   String
  }

  # ── Federated Types ─────────────────────────────

  type FederatedStatus {
    totalRounds:   Int
    activeNodes:   [String!]
    excludedNodes: [String!]
    globalWeights: [WeightEntry!]
  }

  type WeightEntry {
    edge:   String!
    weight: Float!
  }

  # ── Full Analysis Type ───────────────────────────

  type FullAnalysis {
    patientId:    String!
    causalGraph:  CausalGraphSummary
    survival:     SurvivalSummary
    recommendation: RecommendationSummary
    pipeline:     PipelineStatus
  }

  type CausalGraphSummary {
    nodeCount:    Int
    edgeCount:    Int
    zkProof:      String
  }

  type SurvivalSummary {
    riskScore:          Float
    medianSurvivalDays: Int
    survival30d:        Float
    survival90d:        Float
  }

  type RecommendationSummary {
    action:      String
    target:      String
    reward:      Float
    zkProven:    Boolean
    auditLogged: Boolean
  }

  type PipelineStatus {
    causalEngine: String
    zkLayer:      String
    federated:    String
    survivalCox:  String
    treatmentPpo: String
  }

  # ── Queries ─────────────────────────────────────

  type Query {
    health: Health!

    patient(id: ID!): Patient

    fullAnalysis(patientId: ID!): FullAnalysis

    causalGraph(patientId: ID!): CausalGraph

    survival(patientId: ID!): SurvivalAnalysis

    recommendation(patientId: ID!): Recommendation

    alerts(patientId: ID!, limit: Int): [Alert!]

    nlpEntities(patientId: ID!): [NLPEntity!]

    nlpRelations(patientId: ID!): [NLPRelation!]

    federatedStatus: FederatedStatus
  }

  # ── Mutations ───────────────────────────────────

  type Mutation {
    buildCausalGraph(patientId: ID!): CausalGraph

    enrichFromNotes(patientId: ID!): EnrichResult

    runAnomalyScan(patientId: ID!): AnomalyScanResult

    acknowledgeAlert(alertId: ID!): Alert

    runFederatedRound: FederatedRoundResult
  }

  type EnrichResult {
    patientId:          String!
    notesProcessed:     Int
    relationsExtracted: Int
    dagUpdates:         Int
    newEdges:           Int
  }

  type AnomalyScanResult {
    patientId:       String!
    anomalyDetected: Boolean!
    alertsFired:     Int!
    alerts:          [Alert!]
  }

  type FederatedRoundResult {
    roundNumber:     Int
    consensusReached: Boolean
    acceptedNodes:   [String!]
    rejectedNodes:   [String!]
  }

  # ── Subscriptions ───────────────────────────────

  type Subscription {
    patientAlerts(patientId: ID!): Alert

    vitalUpdates(patientId: ID!): VitalUpdate

    causalDrift(patientId: ID!): CausalDriftEvent

    collaborativeSession(sessionId: ID!): SessionEvent
  }

  type VitalUpdate {
    patientId: String!
    feature:   String!
    value:     Float!
    timestamp: String
  }

  type CausalDriftEvent {
    patientId:   String!
    edge:        String!
    oldEffect:   Float
    newEffect:   Float
    driftPct:    Float
    significant: Boolean
    timestamp:   String
  }

  type SessionEvent {
    sessionId:  String!
    doctorId:   String!
    eventType:  String!
    payload:    String
    timestamp:  String
  }

  # ── Utility Types ────────────────────────────────

  type Health {
    status:  String!
    service: String!
    version: String!
  }
`;