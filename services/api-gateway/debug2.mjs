// Test simpler causal endpoint
const url1 = "http://localhost:8081/causal/graph/3319a93d-e164-4ef1-beb9-ac5803d9cf51";
const url2 = "http://localhost:8082/survival/predict/3319a93d-e164-4ef1-beb9-ac5803d9cf51";

console.log("Testing causal/graph...");
try {
  const res = await fetch(url1, { signal: AbortSignal.timeout(5000) });
  console.log("causal/graph status:", res.status);
} catch (err) {
  console.log("causal/graph error:", err.message);
}

console.log("Testing survival/predict...");
try {
  const res = await fetch(url2, { signal: AbortSignal.timeout(5000) });
  console.log("survival/predict status:", res.status);
  const d = await res.json();
  console.log("survival data:", JSON.stringify(d).slice(0, 100));
} catch (err) {
  console.log("survival/predict error:", err.message);
}