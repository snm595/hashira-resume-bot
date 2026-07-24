"""Regression tests for retaining reports after screening."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.bot.handlers import candidate_report_handler, newjd_handler
from app.models.upload import ConversationState, UploadMetadata, UploadSession, UploadType
from app.services.conversation_manager import ConversationStateManager


def _upload(name: str, upload_type: UploadType) -> UploadMetadata:
    return UploadMetadata(
        original_filename=name,
        stored_filename=name,
        mime_type="application/pdf",
        size=1,
        file_path=f"/tmp/{name}",
        upload_type=upload_type,
        telegram_file_id=name,
    )


class SessionReportLifecycleTests(unittest.TestCase):
    """Keep reports addressable until a new resume batch or /newjd replaces them."""

    def setUp(self) -> None:
        self.upload_service = MagicMock()
        self.manager = ConversationStateManager(self.upload_service)
        self.session = self.manager.start_session(123)
        self.manager.record_job_description(123, _upload("jd.pdf", UploadType.JOB_DESCRIPTION))
        self.manager.record_resume(123, _upload("first.pdf", UploadType.RESUME))
        # These stored results represent a successfully completed /process command.
        self.session.comparisons = [object()]
        self.session.candidate_scores = [object()]
        self.session.candidate_evaluations = [object()]
        self.session.course_recommendations = [[]]
        self.session.ranked_candidates = [object()]

    def _callback_context(self, callback_data: str) -> tuple[SimpleNamespace, SimpleNamespace, MagicMock]:
        formatter = MagicMock()
        formatter.detailed_candidate_report.return_value = "Candidate report"
        message = AsyncMock()
        query = SimpleNamespace(data=callback_data, answer=AsyncMock(), message=message)
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))
        context = SimpleNamespace(
            application=SimpleNamespace(
                bot_data={"conversation_manager": self.manager, "report_formatter": formatter}
            )
        )
        return update, context, message

    def test_reports_remain_available_for_repeated_view_clicks(self) -> None:
        update, context, message = self._callback_context("candidate:0:0")

        asyncio.run(candidate_report_handler(update, context))
        asyncio.run(candidate_report_handler(update, context))

        self.assertEqual(message.reply_text.await_count, 2)
        message.reply_text.assert_awaited_with("Candidate report")
        self.assertEqual(len(self.session.candidate_scores), 1)

    def test_first_resume_of_new_batch_clears_old_reports_and_invalidates_buttons(self) -> None:
        update, context, message = self._callback_context("candidate:0:0")

        self.manager.record_resume(123, _upload("second.pdf", UploadType.RESUME))

        self.assertEqual(self.session.resumes[0].original_filename, "second.pdf")
        self.assertEqual(self.session.candidate_scores, [])
        self.assertEqual(self.session.ranked_candidates, [])
        self.assertEqual(self.session.report_batch_id, 1)
        self.assertEqual(self.session.state, ConversationState.READY_TO_PROCESS)

        asyncio.run(candidate_report_handler(update, context))
        message.reply_text.assert_awaited_once_with(
            "That candidate report is no longer available. Upload new resumes and send /process again."
        )

    def test_newjd_clears_the_entire_session(self) -> None:
        message = AsyncMock()
        update = SimpleNamespace(effective_user=SimpleNamespace(id=123), effective_message=message)
        context = SimpleNamespace(
            application=SimpleNamespace(bot_data={"conversation_manager": self.manager})
        )

        asyncio.run(newjd_handler(update, context))

        new_session = self.manager.get_session(123)
        self.assertIsNotNone(new_session)
        self.assertIsNone(new_session.job_description)
        self.assertIsNone(new_session.extracted_job_description)
        self.assertEqual(new_session.resumes, [])
        self.assertEqual(new_session.extracted_resumes, [])
        self.assertEqual(new_session.candidate_scores, [])
        self.assertEqual(new_session.ranked_candidates, [])
        self.assertEqual(new_session.report_batch_id, 1)
        self.assertEqual(new_session.state, ConversationState.WAITING_FOR_JD)


if __name__ == "__main__":
    unittest.main()
