"""
Unified entry point — starts both FastAPI and Telegram Bot concurrently.

Design Decision:
    We run FastAPI (via uvicorn) and the Telegram bot (via python-telegram-bot)
    in the SAME process using asyncio.gather(). This is the right approach
    for the MVP because:

    1. Single process deployment — simpler to run, debug, and deploy.
    2. Shared memory — bot handlers and API routes access the same session
       store without IPC or a database.
    3. Graceful shutdown — both services shut down together.

    For production scale-out, these could be split into separate services
    communicating via Redis or a message queue.

Usage:
    python run.py

    This will:
    - Start the FastAPI server on the configured host:port.
    - Start the Telegram bot in polling mode.
    - Both run concurrently until interrupted (Ctrl+C).
"""

import asyncio

import uvicorn
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.handlers import (
    candidate_report_handler,
    document_handler,
    help_handler,
    newjd_handler,
    process_handler,
    reset_handler,
    start_handler,
    unsupported_upload_handler,
)
from app.config.settings import settings
from app.extractor.jd_extractor import JobDescriptionExtractor
from app.extractor.resume_extractor import ResumeExtractor
from app.llm.client import LLMClient
from app.comparison.comparison_engine import ComparisonEngine
from app.extractor.resume_evaluator import ResumeEvaluator
from app.formatter.report_formatter import ReportFormatter
from app.main import create_app
from app.normalizer.document_normalizer import DocumentNormalizer
from app.parser.parser_factory import ParserFactory
from app.services.conversation_manager import ConversationStateManager
from app.services.document_intelligence_service import DocumentIntelligenceService
from app.services.upload_service import UploadService
from app.services.screening_service import ScreeningService
from app.scoring.scoring_engine import ScoringEngine
from app.ranking.ranking_engine import RankingEngine
from app.recommendation.recommendation_engine import RecommendationEngine
from app.utils.logger import get_logger, setup_root_logger

# Configure logging before anything else so all startup logs are captured
setup_root_logger(log_level=settings.log_level, log_dir=settings.log_dir)
settings.ensure_directories()

logger = get_logger(__name__)


def build_telegram_app() -> Application:
    """
    Build and configure the python-telegram-bot Application.

    Creates the Application instance with the configured token and
    registers all command handlers. Document handlers will be added
    in Phase 2.

    Returns:
        A configured python-telegram-bot Application ready to start polling.
    """
    logger.info("Building Telegram bot application")

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    upload_service = UploadService(
        upload_dir=settings.upload_dir,
        max_file_size_bytes=settings.max_file_size_bytes,
    )
    app.bot_data["upload_service"] = upload_service
    app.bot_data["conversation_manager"] = ConversationStateManager(upload_service)
    llm_client = LLMClient(settings)
    app.bot_data["document_intelligence_service"] = DocumentIntelligenceService(
        parser_factory=ParserFactory(),
        normalizer=DocumentNormalizer(),
        jd_extractor=JobDescriptionExtractor(llm_client),
        resume_extractor=ResumeExtractor(llm_client),
    )
    app.bot_data["screening_service"] = ScreeningService(
        comparison_engine=ComparisonEngine(),
        scoring_engine=ScoringEngine(settings),
        resume_evaluator=ResumeEvaluator(llm_client),
        recommendation_engine=RecommendationEngine(),
        ranking_engine=RankingEngine(),
    )
    app.bot_data["report_formatter"] = ReportFormatter()

    # --- Register Command Handlers ---
    # Each handler corresponds to a Telegram slash command.
    # Order does not matter — python-telegram-bot matches by command name.
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("newjd", newjd_handler))
    app.add_handler(CommandHandler("process", process_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, unsupported_upload_handler))
    app.add_handler(CallbackQueryHandler(candidate_report_handler, pattern=r"^candidate:\d+:\d+$"))

    logger.info("Registered upload workflow handlers")
    return app


async def run_fastapi() -> None:
    """
    Start the FastAPI server using uvicorn's async serve method.

    Uses uvicorn.Server with a programmatic Config instead of
    uvicorn.run() to allow async operation alongside the Telegram bot.
    """
    fastapi_app = create_app()
    config = uvicorn.Config(
        app=fastapi_app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    logger.info(
        "Starting FastAPI server on %s:%d",
        settings.api_host,
        settings.api_port,
    )
    await server.serve()


async def run_telegram_bot() -> None:
    """
    Start the Telegram bot in polling mode.

    Uses the async initialize/start/updater pattern instead of
    run_polling() to allow concurrent execution with FastAPI.

    Polling mode is used for development. For production, webhook
    mode should be configured via the FastAPI server.
    """
    app = build_telegram_app()
    logger.info("Starting Telegram bot in polling mode")

    # Initialize the application (sets up internal resources)
    await app.initialize()
    # Start processing updates
    await app.start()
    # Start polling for new updates from Telegram
    await app.updater.start_polling()

    logger.info("Telegram bot is now polling for updates")

    # Keep running until cancelled
    try:
        # Wait indefinitely — the bot processes updates via callbacks
        await asyncio.Event().wait()
    finally:
        # Graceful shutdown sequence
        logger.info("Stopping Telegram bot")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def main() -> None:
    """
    Run both FastAPI and Telegram bot concurrently.

    Uses asyncio.gather to run both services. If either service
    raises an exception, both are cancelled for a clean shutdown.
    """
    logger.info("=" * 60)
    logger.info("AI Resume Screening Bot — Starting")
    logger.info("=" * 60)

    await asyncio.gather(
        run_fastapi(),
        run_telegram_bot(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt — shutting down")
    except Exception as e:
        logger.critical("Fatal error during startup: %s", e, exc_info=True)
        raise
