"""CaseCardService — High-level interface for case card extraction and management.

Wraps ReadingService and provides CRUD operations for CaseCard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.case_card import CaseCard
from app.services.llm.factory import get_llm_provider
from app.services.reading.reading_service import ReadingService
from app.services.version_manager import VersionManager

if TYPE_CHECKING:
    pass


class CaseCardService:
    """Service for case card extraction, retrieval, and management."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.
        
        Args:
            db: AsyncSession for database operations.
        """
        self.db = db
        self._version_manager = VersionManager(CaseCard)
        self._provider = get_llm_provider()
        self._reading_service = ReadingService(self._provider)

    async def extract_and_store_card(
        self,
        case_id: UUID,
        notice_html: str | None = None,
        spec_pdf_url: str | None = None,
        *,
        force: bool = False,
    ) -> CaseCard:
        """Extract case card via ReadingService and store in database.
        
        Args:
            case_id: The case to extract card for.
            notice_html: Optional notice HTML (fetched if not provided).
            spec_pdf_url: Optional spec PDF URL (fetched if not provided).
            force: If True, re-extract even if hash unchanged.
        
        Returns:
            The created CaseCard.
        
        Raises:
            ValueError: If case not found.
        """
        case = await self.db.get(Case, case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Use ReadingService to extract
        scope = "force" if force else "soft"
        card = await self._reading_service.process_case(self.db, case, scope=scope)
        return card

    async def get_current_card(self, case_id: UUID) -> CaseCard | None:
        """Get the current (is_current=True) card for a case.
        
        Args:
            case_id: The case ID.
        
        Returns:
            The current CaseCard or None if not found.
        """
        return await self._version_manager.get_current(self.db, case_id=case_id)

    async def get_all_cards(self, case_id: UUID) -> list[CaseCard]:
        """Get all card versions for a case.
        
        Args:
            case_id: The case ID.
        
        Returns:
            List of all CaseCard versions (ordered by version DESC).
        """
        return await self._version_manager.get_all_versions(self.db, case_id=case_id)

    async def mark_reviewed(self, card_id: UUID, reviewed_by: str = "kaneko") -> CaseCard:
        """Mark a card as reviewed.
        
        Args:
            card_id: The card ID.
            reviewed_by: User who reviewed (default: 'kaneko' for Phase 1).
        
        Returns:
            Updated CaseCard.
        
        Raises:
            ValueError: If card not found.
        """
        card = await self.db.get(CaseCard, card_id)
        if not card:
            raise ValueError(f"CaseCard {card_id} not found")

        from datetime import UTC, datetime
        card.reviewed_at = datetime.now(UTC)
        card.reviewed_by = reviewed_by
        await self.db.commit()
        return card

    async def delete_card(self, card_id: UUID) -> None:
        """Delete a card (and all versions if no other versions remain).
        
        Args:
            card_id: The card ID to delete.
        
        Raises:
            ValueError: If card not found.
        """
        card = await self.db.get(CaseCard, card_id)
        if not card:
            raise ValueError(f"CaseCard {card_id} not found")

        await self.db.delete(card)
        await self.db.commit()

        # If no versions remain for this case, no special cleanup needed
        # (FK constraint handled by PostgreSQL)
