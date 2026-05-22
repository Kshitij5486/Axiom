const url = "http://localhost:8081/causal/full/3319a93d-e164-4ef1-beb9-ac5803d9cf51";
console.log("Testing causal/full...");
try {
  const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
  console.log("Status:", res.status);
  const data = await res.json();
  console.log("Keys:", Object.keys(data));
  console.log("Has detail:", !!data.detail);
  console.log("causal_graph:", JSON.stringify(data.causal_graph).slice(0, 100));
  console.log("survival:", JSON.stringify(data.survival));
  console.log("recommendation:", JSON.stringify(data.recommendation));
} catch (err) {
  console.error("Error:", err.message);
}