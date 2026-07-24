"""Telegram adapters for the document-upload and screening conversation."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.config.settings import settings
from app.formatter.report_formatter import ReportFormatter
from app.models.upload import ConversationState, UploadType
from app.services.conversation_manager import ConversationStateManager
from app.services.document_intelligence_service import DocumentIntelligenceService
from app.services.screening_service import ScreeningService
from app.services.upload_service import UploadService, UploadValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _conversation_manager(context: ContextTypes.DEFAULT_TYPE) -> ConversationStateManager:
    """Get the application-owned manager configured during bot startup."""
    return context.application.bot_data["conversation_manager"]


def _upload_service(context: ContextTypes.DEFAULT_TYPE) -> UploadService:
    """Get the application-owned upload service configured during bot startup."""
    return context.application.bot_data["upload_service"]


def _document_intelligence_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> DocumentIntelligenceService:
    """Get the application-owned processing service."""
    return context.application.bot_data["document_intelligence_service"]


def _screening_service(context: ContextTypes.DEFAULT_TYPE) -> ScreeningService:
    """Get the application-owned deterministic screening service."""
    return context.application.bot_data["screening_service"]


def _report_formatter(context: ContextTypes.DEFAULT_TYPE) -> ReportFormatter:
    """Get the report formatter used only to render stored screening results."""
    return context.application.bot_data["report_formatter"]


def _user_id(update: Update) -> int:
    """Return the Telegram user's stable identifier for session isolation."""
    if update.effective_user is None:
        raise ValueError("Telegram update did not include a user")
    return update.effective_user.id


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a clean upload session and ask the user for one JD."""
    user_id = _user_id(update)
    _conversation_manager(context).start_session(user_id)
    logger.info("Started upload session for user_id=%d", user_id)
    await update.effective_message.reply_text(
        "👋 Welcome to the *Hashira Resume Screening Bot*!\n\n"
        "Please upload one Job Description as a PDF or DOCX file to begin.\n\n"
        "Commands:\n"
        "/start - Start new session\n"
        "/newjd - Clear session and upload new Job Description\n"
        "/process - Begin screening uploaded resumes\n"
        "/reset - Clear all data\n"
        "/help - Show help",
        parse_mode="Markdown"
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain the upload and screening workflow."""
    await update.effective_message.reply_text(
        "📚 *Hashira Resume Screening Bot - Help*\n\n"
        "*Workflow:*\n"
        "1. Upload a Job Description (PDF or DOCX)\n"
        "2. Upload candidate resumes (PDF or DOCX)\n"
        "3. Run /process to screen and rank\n\n"
        "*Commands:*\n"
        "/start - Start new session\n"
        "/newjd - Clear session & upload new Job Description\n"
        "/process - Begin screening resumes\n"
        "/reset - Clear session and temporary files\n"
        "/help - Show this help message\n\n"
        f"Maximum file size: {settings.max_file_size_bytes // (1024 * 1024)} MB.\n"
        f"Maximum resumes per batch: {settings.max_resumes_per_session}.",
        parse_mode="Markdown"
    )


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete exactly the current user's temporary files and session state."""
    user_id = _user_id(update)
    _conversation_manager(context).reset_session(user_id)
    logger.info("Reset upload session for user_id=%d", user_id)
    await update.effective_message.reply_text(
        "🔄 Session reset. All uploaded files have been removed. Send /start to begin again."
    )


async def newjd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear entire session, clear uploaded JD & resumes, and reset state to WAITING_FOR_JD."""
    user_id = _user_id(update)
    _conversation_manager(context).start_session(user_id)
    logger.info("Cleared session via /newjd for user_id=%d", user_id)
    await update.effective_message.reply_text(
        "🆕 Previous session cleared.\n\nPlease upload the new Job Description."
    )


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Validate and store a JD or resume according to the user's current state."""
    if update.effective_message is None or update.effective_message.document is None:
        return

    user_id = _user_id(update)
    manager = _conversation_manager(context)
    session = manager.get_session(user_id)
    if session is None:
        await update.effective_message.reply_text("Send /start before uploading documents.")
        return

    if session.state is ConversationState.WAITING_FOR_JD:
        upload_type = UploadType.JOB_DESCRIPTION
    elif session.state in {
        ConversationState.WAITING_FOR_RESUMES,
        ConversationState.READY_TO_PROCESS,
    }:
        starting_new_batch = manager.has_screening_results(user_id)
        if not starting_new_batch and not manager.can_accept_resume(user_id, settings.max_resumes_per_session):
            await update.effective_message.reply_text(
                f"You can upload up to {settings.max_resumes_per_session} resumes in one session."
            )
            return
        upload_type = UploadType.RESUME
    else:
        await update.effective_message.reply_text("Send /start to begin a new upload session.")
        return

    try:
        upload = await _upload_service(context).save_file(
            bot=context.bot,
            document=update.effective_message.document,
            user_id=user_id,
            upload_type=upload_type,
        )
    except UploadValidationError as error:
        await update.effective_message.reply_text(str(error))
        return
    except Exception:
        logger.exception("Unable to save upload for user_id=%d", user_id)
        await update.effective_message.reply_text(
            "I could not save that file. Please try uploading it again."
        )
        return

    if upload_type is UploadType.JOB_DESCRIPTION:
        manager.record_job_description(user_id, upload)
        await update.effective_message.reply_text(
            "✅ Job Description received! Now upload one or more candidate resumes (PDF or DOCX)."
        )
        return

    updated_session = manager.record_resume(user_id, upload)
    await update.effective_message.reply_text(
        f"✅ Received resume ({len(updated_session.resumes)} total).\n\n"
        "Send /process whenever you are ready to screen."
    )


async def unsupported_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Give photo uploads a direct answer instead of silently ignoring them."""
    if update.effective_message is not None:
        await update.effective_message.reply_text("Only PDF and DOCX files are supported.")


async def process_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract documents and retain completed screening results for inline reports."""
    user_id = _user_id(update)
    manager = _conversation_manager(context)
    session = manager.get_session(user_id)

    if session is None or session.job_description is None:
        await update.effective_message.reply_text("Upload a Job Description first by sending /start or /newjd.")
        return
    elif not session.resumes:
        await update.effective_message.reply_text("Upload at least one resume before sending /process.")
        return

    progress_msg = await update.effective_message.reply_text("📄 Parsing documents...")

    async def progress_callback(stage_text: str) -> None:
        try:
            await progress_msg.edit_text(stage_text)
        except Exception as e:
            logger.debug("Progress edit skipped: %s", e)

    try:
        await _document_intelligence_service(context).process(session, progress_callback=progress_callback)
        rankings = await _screening_service(context).screen(session, progress_callback=progress_callback)
    except Exception:
        logger.exception("Processing failed for user_id=%d", user_id)
        await progress_msg.edit_text("❌ I could not process the uploaded documents. Please check the files and try again.")
        return

    summary_text = _report_formatter(context).summary_report(rankings)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"View {candidate.rank}: {candidate.candidate_name}",
                    callback_data=f"candidate:{session.report_batch_id}:{candidate.candidate_index}",
                )
            ]
            for candidate in rankings
        ]
    )

    try:
        await progress_msg.edit_text(summary_text, reply_markup=keyboard)
    except Exception:
        await update.effective_message.reply_text(summary_text, reply_markup=keyboard)

    completion_msg = (
        "✅ Screening complete.\n\n"
        "Use the View Candidate buttons to reopen reports at any time.\n\n"
        "Upload a resume to begin a new batch with the current Job Description."
    )
    await update.effective_message.reply_text(completion_msg)


async def candidate_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the stored detailed report selected by an inline ranking button."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    user_id = _user_id(update)
    session = _conversation_manager(context).get_session(user_id)
    try:
        _, callback_batch_id, callback_candidate_index = query.data.split(":", maxsplit=2)
        candidate_index = int(callback_candidate_index)
        if session is None:
            logger.info("Callback report lookup failed: no active session for user_id=%d", user_id)
            raise ValueError("No active session")
        logger.info(
            "Callback report lookup: scores=%d comparisons=%d evals=%d recs=%d rankings=%d batch=%d callback_batch=%s candidate_index=%d",
            len(session.candidate_scores),
            len(session.comparisons),
            len(session.candidate_evaluations),
            len(session.course_recommendations),
            len(session.ranked_candidates),
            session.report_batch_id,
            callback_batch_id,
            candidate_index,
        )
        if int(callback_batch_id) != session.report_batch_id:
            raise ValueError("Candidate report belongs to a previous batch")
        report = _report_formatter(context).detailed_candidate_report(
            session.candidate_scores[candidate_index],
            session.comparisons[candidate_index],
            session.candidate_evaluations[candidate_index],
            session.course_recommendations[candidate_index],
        )
    except (ValueError, IndexError):
        await query.message.reply_text("That candidate report is no longer available. Upload new resumes and send /process again.")
        return
    logger.info("Generated detailed report for user_id=%d candidate_index=%d", user_id, candidate_index)
    await query.message.reply_text(report)
