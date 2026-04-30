"""
Request Service — gRPC Client.
Sends expense submissions to the approval-service via gRPC.
"""

import os
import logging

import grpc

# gRPC generated stubs will be imported at runtime.
# They are generated from proto/approval.proto using:
#   python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/approval.proto
import approval_pb2
import approval_pb2_grpc

logger = logging.getLogger(__name__)

APPROVAL_GRPC_HOST = os.getenv("APPROVAL_GRPC_HOST", "localhost:50051")

# Global channel to reuse connection (best practice for gRPC in K8s)
_channel = None

def get_channel():
    global _channel
    if _channel is None:
        logger.info(f"Initializing persistent gRPC channel to {APPROVAL_GRPC_HOST}")
        # Relaxed keepalive settings to avoid 'too_many_pings' error from server
        _channel = grpc.aio.insecure_channel(
            APPROVAL_GRPC_HOST,
            options=[
                ('grpc.keepalive_time_ms', 30000),      # 30 seconds instead of 10
                ('grpc.keepalive_timeout_ms', 10000),   # 10 seconds timeout
                ('grpc.keepalive_permit_without_calls', False), # Only ping when active
            ]
        )
    return _channel


async def submit_for_approval(
    expense_id: str,
    title: str,
    amount: float,
    currency: str,
    description: str,
    submitted_by: str,
) -> dict:
    """
    Send an expense to the approval-service via gRPC.
    Uses a persistent channel to avoid connection setup latency.
    """
    try:
        channel = get_channel()
        stub = approval_pb2_grpc.ApprovalServiceStub(channel)

        request = approval_pb2.ApprovalRequest(
            expense_id=expense_id,
            title=title,
            amount=amount,
            currency=currency,
            description=description or "",
            submitted_by=submitted_by,
        )

        logger.info(f"Sending gRPC approval request for expense {expense_id} via persistent channel")
        # Set a shorter timeout since we expect a fast response from approval-service
        response = await stub.SubmitForApproval(request, timeout=10.0)

        return {
            "expense_id": response.expense_id,
            "status": response.status,
            "reason": response.reason,
            "decided_by": response.decided_by,
            "decided_at": response.decided_at,
        }
    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC call to approval-service failed: {e.code()} - {e.details()}")
        # If connection is broken, reset channel for next attempt
        if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
            global _channel
            _channel = None
        raise Exception(f"Approval service unavailable: {e.details()}")
    except Exception as e:
        logger.error(f"Unexpected error calling approval-service: {e}")
        raise
