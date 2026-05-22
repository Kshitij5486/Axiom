const content = require("fs").readFileSync("src/resolvers.js", "utf8");

const old = `    fullAnalysis: async (_, { patientId }, { services }) => {
      const data = await serviceGet(
        \`\${services.causal}/causal/full/\${patientId}\`
      );
      if (!data || data.detail) return null;

      return {
        patientId,
        causalGraph: {
          nodeCount: data.causal_graph?.node_count || 0,
          edgeCount: data.causal_graph?.edge_count || 0,
          zkProof:   data.causal_graph?.zk_integrity_proof,
        },
        survival: {
          riskScore:          data.survival?.risk_score,
          medianSurvivalDays: data.survival?.median_survival_days,
          survival30d:        data.survival?.survival_30d,
          survival90d:        data.survival?.survival_90d,
        },
        recommendation: {
          action:      data.recommendation?.action,
          target:      data.recommendation?.target,
          reward:      data.recommendation?.reward,
          zkProven:    data.recommendation?.zk_proven || false,
          auditLogged: data.recommendation?.audit_logged || false,
        },
        pipeline: data.pipeline || null,
      };
    },`;

const newCode = `    fullAnalysis: async (_, { patientId }, { services }) => {
      // Parallel calls to avoid timeout
      const [graphData, survivalData, recData] = await Promise.all([
        serviceGet(\`\${services.causal}/causal/graph/\${patientId}\`),
        serviceGet(\`\${services.survival}/survival/predict/\${patientId}\`),
        serviceGet(\`\${services.survival}/survival/recommend/\${patientId}\`),
      ]);

      return {
        patientId,
        causalGraph: graphData ? {
          nodeCount: graphData.node_count || 0,
          edgeCount: graphData.edge_count || 0,
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
    },`;

if (content.includes('const data = await serviceGet')) {
  const fixed = content.replace(old, newCode);
  require("fs").writeFileSync("src/resolvers.js", fixed);
  console.log("Fixed");
} else {
  console.log("Pattern not found");
}