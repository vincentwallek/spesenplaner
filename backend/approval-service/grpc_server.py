"""
Approval Service — gRPC Server Implementation.
Receives expense submissions from request-service via gRPC and processes them.
"""

import logging
from datetime import datetime, timezone

import grpc

import approval_pb2
import approval_pb2_grpc
from database import async_session
from crud import create_approval_record, get_record_by_expense

logger = logging.getLogger(__name__)


class ApprovalServiceServicer(approval_pb2_grpc.ApprovalServiceServicer):
    """gRPC service implementation for expense approval."""

    async def SubmitForApproval(self, request, context):
        """
        Process an incoming expense submission.
        Creates a pending approval record that requires manager decision.
        """
        logger.info(
            f"gRPC: Received approval request for expense {request.expense_id} "
            f"(amount: {request.amount} {request.currency})"
        )

        try:
            async with async_session() as session:
                existing = await get_record_by_expense(session, request.expense_id)
                if existing:
                    record = existing
                    # Reset decision if previously NEEDS_REVISION so manager can decide again
                    if record.decision == "NEEDS_REVISION":
                        record.decision = None
                        record.reason = None
                        record.decided_by = "auto-approver"
                        record.decided_at = None
                        await session.commit()
                        await session.refresh(record)
                else:
                    record = await create_approval_record(
                        session=session,
                        expense_id=request.expense_id,
                        title=request.title,
                        amount=request.amount,
                        currency=request.currency,
                        submitted_by=request.submitted_by,
                    )

                return approval_pb2.ApprovalResponse(
                    expense_id=record.expense_id,
                    status="SUBMITTED",
                    reason="Awaiting manager approval",
                    decided_by="",
                    decided_at="",
                )

        except Exception as e:
            logger.error(f"Error processing approval: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return approval_pb2.ApprovalResponse(
                expense_id=request.expense_id,
                status="ERROR",
                reason=str(e),
            )
