// Quick debug - test fetch directly
const url = "http://localhost:8085/federated/reputation";
console.log("Testing fetch to:", url);
try {
  const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
  console.log("Status:", res.status);
  const data = await res.json();
  console.log("Data:", JSON.stringify(data).slice(0, 200));
} catch (err) {
  console.error("Fetch error:", err.message);
}