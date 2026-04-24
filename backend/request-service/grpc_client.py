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

    Returns:
        dict with keys: expense_id, status, reason, decided_by, decided_at
    """
    try:
        async with grpc.aio.insecure_channel(APPROVAL_GRPC_HOST) as channel:
            stub = approval_pb2_grpc.ApprovalServiceStub(channel)

            request = approval_pb2.ApprovalRequest(
                expense_id=expense_id,
                title=title,
                amount=amount,
                currency=currency,
                description=description or "",
                submitted_by=submitted_by,
            )

            logger.info(f"Sending gRPC approval request for expense {expense_id}")
            response = await stub.SubmitForApproval(request)

            return {
                "expense_id": response.expense_id,
                "status": response.status,
                "reason": response.reason,
                "decided_by": response.decided_by,
                "decided_at": response.decided_at,
            }
    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC call to approval-service failed: {e.code()} - {e.details()}")
        raise Exception(f"Approval service unavailable: {e.details()}")
    except Exception as e:
        logger.error(f"Unexpected error calling approval-service: {e}")
        raise
