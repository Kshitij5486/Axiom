import sys
sys.path.insert(0, ".")
import grpc
import axiom_pb2
import axiom_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = axiom_pb2_grpc.CausalServiceStub(channel)

patient_id = "3319a93d-e164-4ef1-beb9-ac5803d9cf51"
print(f"Testing GetGraph for {patient_id[:8]}...")

response = stub.GetGraph(
    axiom_pb2.GetGraphRequest(patient_id=patient_id)
)

print(f"Success:    {response.success}")
print(f"Node count: {response.node_count}")
print(f"Edge count: {response.edge_count}")
print(f"ZK proof:   {response.zk_proof[:16]}...")
print(f"Edges sample:")
for edge in response.edges[:3]:
    print(f"  {edge.treatment}->{edge.outcome}: {edge.effect:.4f}")