import { TOPICS } from "./pubsub.js";

// ── Service call helpers ──────────────────────────

async function serviceGet(url, fallback = null) {
  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

async function servicePost(url, fallback = null) {
  try {
    const res = await fetch(url, {
      method: "POST",
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

// ── Shape mappers ─────────────────────────────────

function mapCausalGraph(data, patientId) {
  if (!data || data.error) return null;

  const cg = data.causal_graph || data;
  const effectSizes = cg.effect_sizes || {};

  const edges = Object.entries(effectSizes).map(
    ([key, val]) => {
      const [source, target] = key.split("->");
      const effect = typeof val === "object"
        ? val.effect : val;
      return {
        source: source || key,
        target: target || "",
        effect: effect || 0,
        samples: val?.samples || 0,
        blended: val?.blended || false,
        nlpSource: val?.nlp_source || false,
        zkProven: !!cg.zk_integrity_proof,
      };
    }
  );

  const nodes = [...new Set(
    edges.flatMap(e => [e.source, e.target])
      .filter(Boolean)
  )].map(id => ({ id, label: id }));

  const topEffects = edges
    .sort((a, b) => Math.abs(b.effect) - Math.abs(a.effect))
    .slice(0, 3)
    .map(e => ({
      treatment: e.source,
      outcome: e.target,
      effect: e.effect,
      samples: e.samples,
      confidence: 0.9,
    }));

  return {
    patientId,
    graphId: cg.graph_id || null,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    nodes,
    edges,
    topEffects,
    zkProof: cg.zk_integrity_proof || null,
    builtAt: cg.built_at || null,
  };
}

function mapSurvival(data, patientId) {
  if (!data || data.error) return null;
  const probs = data.survival_probabilities || {};
  const bands = data.confidence_bands || {};

  return {
    patientId,
    riskScore: data.risk_score || null,
    medianSurvivalDays: data.median_survival_days || null,
    survivalCurve: {
      day30:  probs["30"]  || null,
      day60:  probs["60"]  || null,
      day90:  probs["90"]  || null,
      day180: probs["180"] || null,
      day365: probs["365"] || null,
    },
    confidenceBands: {
      day30:  bands["30"]  || null,
      day60:  bands["60"]  || null,
      day90:  bands["90"]  || null,
      day180: bands["180"] || null,
      day365: bands["365"] || null,
    },
  };
}

function mapRecommendation(data, patientId) {
  if (!data || data.error) return null;
  return {
    patientId,
    recommendedAction: data.recommended_action || null,
    targetVital: data.target_vital || null,
    policy: data.policy || "ppo",
    rankedActions: (data.ranked_actions || []).map(a => ({
      actionId: a.action_id,
      actionName: a.action_name,
      target: a.target,
      immediateReward: a.immediate_reward,
    })),
    zkProofHash: data.zk_proof_hash || null,
    zkProven: data.zk_proven || false,
    auditRecId: data.audit_rec_id || null,
    auditLogged: data.audit_logged || false,
  };
}

function mapAlert(a) {
  return {
    alertId:          a.alert_id,
    patientId:        a.patient_id,
    alertType:        a.alert_type,
    feature:          a.feature,
    currentValue:     a.current_value,
    threshold:        a.threshold,
    severity:         a.severity,
    message:          a.message,
    predictedValue2h: a.predicted_value_2h || null,
    zkProofHash:      a.zk_proof_hash || null,
    zkProven:         a.zk_proven || false,
    acknowledged:     a.acknowledged || false,
    createdAt:        a.created_at || null,
  };
}

function mapNLPEntity(e) {
  return {
    text:       e.text,
    label:      e.label,
    canonical:  e.canonical,
    confidence: e.confidence,
    model:      e.model || "dictionary",
  };
}

// ── Resolvers ─────────────────────────────────────

export const resolvers = {

  Query: {
    health: () => ({
      status: "healthy",
      service: "axiom-api-gateway",
      version: "0.7.0",
    }),

    fullAnalysis: async (_, { patientId }, { services }) => {
      // Parallel calls to avoid timeout
      const [graphData, survivalData, recData] = await Promise.all([
        serviceGet(`${services.causal}/causal/graph/${patientId}`),
        serviceGet(`${services.survival}/survival/predict/${patientId}`),
        serviceGet(`${services.survival}/survival/recommend/${patientId}`),
      ]);

      return {
        patientId,
        causalGraph: graphData ? {
          nodeCount: graphData.node_list?.length || Object.keys(graphData.effect_sizes || {}).length || 0,
          edgeCount: graphData.adjacency_json?.length || Object.keys(graphData.effect_sizes || {}).length || 0,
          zkProof:   graphData.zk_integrity_proof || null,
        } : null,
        survival: survivalData && !survivalData.error ? {
          riskScore:          survivalData.risk_score,
          medianSurvivalDays: survivalData.median_survival_days,
          survival30d: survivalData.survival_probabilities?.["30"] || null,
          survival90d: survivalData.survival_probabilities?.["90"] || null,
        } : null,
        recommendation: recData && !recData.error ? {
          action:      recData.recommended_action,
          target:      recData.target_vital,
          reward:      recData.ranked_actions?.[0]?.immediate_reward,
          zkProven:    recData.zk_proven || false,
          auditLogged: recData.audit_logged || false,
        } : null,
        pipeline: {
          causalEngine: "sprint2",
          zkLayer:      "sprint3",
          federated:    "sprint4",
          survivalCox:  "sprint5",
          treatmentPpo: "sprint5",
        },
      };
    },

    causalGraph: async (_, { patientId }, { services }) => {
      const data = await serviceGet(
        `${services.causal}/causal/graph/${patientId}`
      );
      return mapCausalGraph(data, patientId);
    },

    survival: async (_, { patientId }, { services }) => {
      const data = await serviceGet(
        `${services.survival}/survival/predict/${patientId}`
      );
      return mapSurvival(data, patientId);
    },

    recommendation: async (_, { patientId }, { services }) => {
      const data = await serviceGet(
        `${services.survival}/survival/recommend/${patientId}`
      );
      return mapRecommendation(data, patientId);
    },

    alerts: async (_, { patientId, limit = 10 }, { services }) => {
      const data = await serviceGet(
        `${services.nlp}/anomaly/alerts/${patientId}`
      );
      if (!data?.alerts) return [];
      return data.alerts.slice(0, limit).map(mapAlert);
    },

    nlpEntities: async (_, { patientId }, { services }) => {
      const data = await servicePost(
        `${services.nlp}/nlp/extract/${patientId}`
      );
      if (!data) return [];
      const entities = [];
      data.extractions?.forEach(ex => {
        entities.push(...(ex.entities || []));
      });
      return entities.map(mapNLPEntity);
    },

    nlpRelations: async (_, { patientId }, { services }) => {
      const data = await servicePost(
        `${services.nlp}/nlp/relations/${patientId}`
      );
      if (!data?.relations) return [];
      return data.relations.map(r => ({
        cause:      r.cause,
        effect:     r.effect,
        direction:  r.direction,
        confidence: r.confidence,
        nlpEffect:  r.nlp_effect,
        evidence:   r.evidence,
      }));
    },

    federatedStatus: async (_, __, { services }) => {
      const data = await serviceGet(
        `${services.federated}/federated/reputation`
      );
      if (!data) return null;
      return {
        totalRounds:   data.total_rounds,
        activeNodes:   data.active_nodes || [],
        excludedNodes: data.excluded_nodes || [],
        globalWeights: Object.entries(
          data.scores || {}
        ).map(([edge, weight]) => ({ edge, weight })),
      };
    },

    patient: async (_, { id }, { services }) => {
      // Parallel fetch all patient data
      const [fullData, alertData, nlpData] =
        await Promise.all([
          serviceGet(
            `${services.causal}/causal/full/${id}`
          ),
          serviceGet(
            `${services.nlp}/anomaly/alerts/${id}`
          ),
          servicePost(
            `${services.nlp}/nlp/extract/${id}`
          ),
        ]);

      const causalGraph = fullData
        ? mapCausalGraph(fullData.causal_graph, id)
        : null;

      const survival = fullData?.survival
        ? {
            patientId: id,
            riskScore: fullData.survival.risk_score,
            medianSurvivalDays:
              fullData.survival.median_survival_days,
            survivalCurve: {
              day30: fullData.survival.survival_30d,
              day90: fullData.survival.survival_90d,
            },
          }
        : null;

      const recommendation = fullData?.recommendation
        ? mapRecommendation(
            fullData.recommendation, id
          )
        : null;

      const activeAlerts = alertData?.alerts
        ? alertData.alerts.slice(0, 5).map(mapAlert)
        : [];

      const nlpEntities = [];
      nlpData?.extractions?.forEach(ex => {
        nlpEntities.push(...(ex.entities || []));
      });

      return {
        id,
        name: null,
        fhirId: id,
        causalGraph,
        survival,
        recommendation,
        activeAlerts,
        nlpEntities: nlpEntities.map(mapNLPEntity),
        vitals: null,
      };
    },
  },

  Mutation: {
    buildCausalGraph: async (
      _, { patientId }, { services }
    ) => {
      const data = await servicePost(
        `${services.causal}/causal/build/${patientId}`
      );
      return mapCausalGraph(data, patientId);
    },

    enrichFromNotes: async (
      _, { patientId }, { services }
    ) => {
      const data = await servicePost(
        `${services.nlp}/nlp/enrich/${patientId}`
      );
      if (!data) return {
        patientId, notesProcessed: 0,
        relationsExtracted: 0, dagUpdates: 0, newEdges: 0,
      };
      return {
        patientId,
        notesProcessed:     data.notes_processed || 0,
        relationsExtracted: data.relations_extracted || 0,
        dagUpdates:         data.dag_update?.updates || 0,
        newEdges:           data.dag_update?.new_edges || 0,
      };
    },

    runAnomalyScan: async (
      _, { patientId }, { services }
    ) => {
      const data = await servicePost(
        `${services.nlp}/anomaly/scan/${patientId}`
      );
      if (!data) return {
        patientId, anomalyDetected: false,
        alertsFired: 0, alerts: [],
      };
      return {
        patientId,
        anomalyDetected: data.anomaly_detected || false,
        alertsFired:     data.alerts_fired || 0,
        alerts: (data.alerts || []).map(mapAlert),
      };
    },

    runFederatedRound: async (_, __, { services }) => {
      const data = await servicePost(
        `${services.federated}/federated/round`
      );
      if (!data) return null;
      return {
        roundNumber:      data.round_number,
        consensusReached: data.consensus_reached,
        acceptedNodes:    data.accepted_nodes || [],
        rejectedNodes:    data.rejected_nodes || [],
      };
    },
  },

  Subscription: {
    patientAlerts: {
      subscribe: (_, { patientId }, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.PATIENT_ALERT]),
      resolve: (payload) => {
        const a = payload.patientAlerts;
        return mapAlert(a);
      },
    },
    vitalUpdates: {
      subscribe: (_, __, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.VITAL_UPDATE]),
      resolve: (payload) => payload.vitalUpdates,
    },
    causalDrift: {
      subscribe: (_, __, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.CAUSAL_DRIFT]),
      resolve: (payload) => payload.causalDrift,
    },
    collaborativeSession: {
      subscribe: (_, __, { pubsub }) =>
        pubsub.asyncIterator([TOPICS.COLLAB_SESSION]),
      resolve: (payload) => payload.collaborativeSession,
    },
  },
};