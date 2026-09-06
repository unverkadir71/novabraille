# Session Pydantic schemas
#
# Plan v9 referansı: Bölüm 1.8.1, 1.15.1.
# Server-side session — HttpOnly cookie ile taşınır, API yanıtlarında dönmez.

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    """Admin/yönetim panelinde görünen oturum bilgisi. Kullanıcıya gösterilmez."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    is_revoked: bool = False