"""
CausalService gRPC Server
Port 50051

Exposes causal engine functionality via gRPC
for high-performance inter-service communication.

Services:
  BuildGraph: trigger causal graph rebuild
  GetGraph:   fetch existing graph
  GetEffects: fetch specific edge effects
"""

import json
import logging
import time
from concurrent import futures

import grpc
import axiom_pb2
import axiom_pb2_grpc

logger = logging.getLogger("axiom.grpc.causal")


class CausalServiceServicer(
    axiom_pb2_grpc.CausalServiceServicer
):
    """gRPC implementation of CausalService."""

    def BuildGraph(self, request, context):
        """Trigger causal graph build for a patient."""
        patient_id = request.patient_id
        logger.info(
            "gRPC BuildGraph: patient=%s",
            patient_id[:8],
        )
        try:
            from db import load_causal_graph
            from causal_graph_builder import (
                PatientCausalGraphBuilder,
            )

            builder = PatientCausalGraphBuilder(
                patient_id
            )
            result = builder.build()

            if not result or result.get("empty"):
                return axiom_pb2.GraphResponse(
                    patient_id=patient_id,
                    success=False,
                    error="Graph empty or build failed",
                )

            edges = self._effects_to_edges(
                result.get("effect_sizes", {})
            )

            return axiom_pb2.GraphResponse(
                patient_id=patient_id,
                graph_id=result.get("graph_id", ""),
                node_count=result.get("node_count", 0),
                edge_count=result.get("edge_count", 0),
                edges=edges,
                zk_proof=result.get(
                    "zk_integrity_proof", ""
                ),
                built_at=result.get("built_at", ""),
                success=True,
            )
        except Exception as e:
            logger.error("BuildGraph error: %s", e)
            return axiom_pb2.GraphResponse(
                patient_id=patient_id,
                success=False,
                error=str(e),
            )

    def GetGraph(self, request, context):
        """Fetch existing causal graph."""
        patient_id = request.patient_id
        logger.info(
            "gRPC GetGraph: patient=%s",
            patient_id[:8],
        )
        try:
            from db import load_causal_graph
            graph = load_causal_graph(patient_id)

            if not graph:
                return axiom_pb2.GraphResponse(
                    patient_id=patient_id,
                    success=False,
                    error="No graph found",
                )

            effect_sizes = graph.get("effect_sizes", {})
            if isinstance(effect_sizes, str):
                effect_sizes = json.loads(effect_sizes)

            node_list = graph.get("node_list", [])
            if isinstance(node_list, str):
                node_list = json.loads(node_list)

            edges = self._effects_to_edges(effect_sizes)

            return axiom_pb2.GraphResponse(
                patient_id=patient_id,
                graph_id=str(
                    graph.get("graph_id", "")
                ),
                node_count=len(node_list),
                edge_count=len(edges),
                edges=edges,
                zk_proof=graph.get(
                    "zk_integrity_proof", ""
                ) or "",
                success=True,
            )
        except Exception as e:
            logger.error("GetGraph error: %s", e)
            return axiom_pb2.GraphResponse(
                patient_id=patient_id,
                success=False,
                error=str(e),
            )

    def GetEffects(self, request, context):
        """Fetch specific causal effects."""
        patient_id = request.patient_id
        try:
            from db import load_causal_graph
            graph = load_causal_graph(patient_id)

            if not graph:
                return axiom_pb2.EffectsResponse(
                    patient_id=patient_id,
                    success=False,
                )

            effect_sizes = graph.get("effect_sizes", {})
            if isinstance(effect_sizes, str):
                effect_sizes = json.loads(effect_sizes)

            edges = self._effects_to_edges(effect_sizes)

            # Filter by requested keys
            if request.edge_keys:
                edges = [
                    e for e in edges
                    if f"{e.treatment}->{e.outcome}"
                    in request.edge_keys
                ]

            return axiom_pb2.EffectsResponse(
                patient_id=patient_id,
                effects=edges,
                success=True,
            )
        except Exception as e:
            return axiom_pb2.EffectsResponse(
                patient_id=patient_id,
                success=False,
            )

    def _effects_to_edges(
        self, effect_sizes: dict
    ) -> list:
        """Convert effect_sizes dict to CausalEdge list."""
        edges = []
        for key, val in effect_sizes.items():
            if "->" not in key:
                continue
            treatment, outcome = key.split("->", 1)
            if isinstance(val, dict):
                effect = float(val.get("effect", 0.0))
                samples = int(val.get("samples", 0))
                blended = bool(val.get("blended", False))
                nlp_source = bool(
                    val.get("nlp_source", False)
                )
            else:
                effect = float(val)
                samples = 0
                blended = False
                nlp_source = False

            edges.append(axiom_pb2.CausalEdge(
                treatment=treatment,
                outcome=outcome,
                effect=effect,
                samples=samples,
                blended=blended,
                nlp_source=nlp_source,
            ))
        return edges


def serve(port: int = 50051):
    """Start the gRPC server."""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )
    axiom_pb2_grpc.add_CausalServiceServicer_to_server(
        CausalServiceServicer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(
        "CausalService gRPC server started on port %d",
        port,
    )
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = serve(50051)
    print("CausalService gRPC running on port 50051")
    print("Press Ctrl+C to stop")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)