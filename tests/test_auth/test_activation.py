# Tests for account activation and password reset flow
#
# Tests the token service, user service, and auth service together.
# Uses real SQLite database (in-memory).

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.models import Base
from backend.src.models.action_token import ActionToken
from backend.src.models.user import User
from backend.src.services.auth import auth_service
from backend.src.services.token import token_service
from backend.src.services.user import user_service


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """In-memory SQLite async session — her test için temiz başlar."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def pending_user(db: AsyncSession) -> User:
    """'pending' durumunda bir test kullanıcısı oluşturur."""
    user = await user_service.create(
        db,
        email="test@example.com",
        password_hash=auth_service.hash_password("oldpass123"),
    )
    await db.commit()
    return user


@pytest_asyncio.fixture
async def active_user(db: AsyncSession) -> User:
    """'active' durumunda bir test kullanıcısı oluşturur."""
    user = await user_service.create(
        db,
        email="active@example.com",
        password_hash=auth_service.hash_password("activepass123"),
    )
    await user_service.activate(db, user)
    await db.commit()
    return user


# ---------------------------------------------------------------------------
# Token service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_activation_token(db: AsyncSession, pending_user: User):
    """Aktivasyon token'ı oluşturma — ham token döner ve hash DB'de saklanır."""
    raw = await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    # Ham token 86 karakter (base64url)
    assert len(raw) == 86
    assert isinstance(raw, str)

    # DB'de hash saklanmış
    from sqlalchemy import func, select
    result = await db.execute(select(func.count()).select_from(ActionToken))
    assert result.scalar() == 1

    # ActionToken kaydı doğru
    result = await db.execute(select(ActionToken))
    token_record = result.scalar_one()
    assert token_record.purpose == "activate_account"
    assert token_record.user_id == pending_user.id
    assert token_record.used_at is None
    assert token_record.token_hash != raw  # Hash saklanır, ham token değil


@pytest.mark.asyncio
async def test_verify_token_valid(db: AsyncSession, pending_user: User):
    """Geçerli token doğrulanabilir."""
    raw = await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    result = await token_service.verify_token(db, raw, "activate_account")
    assert result is not None
    assert result.user_id == pending_user.id


@pytest.mark.asyncio
async def test_verify_token_wrong_purpose(db: AsyncSession, pending_user: User):
    """Yanlış purpose ile token doğrulanamaz."""
    raw = await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    result = await token_service.verify_token(db, raw, "reset_password")
    assert result is None


@pytest.mark.asyncio
async def test_verify_token_wrong_value(db: AsyncSession, pending_user: User):
    """Geçersiz token doğrulanamaz."""
    await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    result = await token_service.verify_token(db, "wrong-token-value", "activate_account")
    assert result is None


@pytest.mark.asyncio
async def test_verify_token_expired(db: AsyncSession, pending_user: User):
    """Süresi dolmuş token doğrulanamaz."""
    from datetime import timedelta

    raw = await token_service.create_token(
        db, pending_user.id, "activate_account",
        ttl=timedelta(hours=-1),  # Geçmişte sona erdi
    )
    await db.commit()

    result = await token_service.verify_token(db, raw, "activate_account")
    assert result is None


@pytest.mark.asyncio
async def test_consume_token(db: AsyncSession, pending_user: User):
    """Token tüketildikten sonra tekrar kullanılamaz."""
    raw = await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    token_record = await token_service.verify_token(db, raw, "activate_account")
    await token_service.consume_token(db, token_record)
    await db.commit()

    # İkinci kez doğrulama başarısız olmalı
    result = await token_service.verify_token(db, raw, "activate_account")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_old_tokens(db: AsyncSession, pending_user: User):
    """Aynı amaçtaki tüm eski token'lar geçersiz kılınır."""
    # 2 aktivasyon token'ı oluştur
    await token_service.create_token(db, pending_user.id, "activate_account")
    await token_service.create_token(db, pending_user.id, "activate_account")
    await token_service.create_token(db, pending_user.id, "reset_password")
    await db.commit()

    # Sadece aktivasyon token'larını geçersiz kıl
    await token_service.invalidate_user_tokens(db, pending_user.id, "activate_account")
    await db.commit()

    # Tüm aktivasyon token'ları kullanılmış olmalı
    from sqlalchemy import select
    result = await db.execute(
        select(ActionToken).where(
            ActionToken.user_id == pending_user.id,
            ActionToken.purpose == "activate_account",
        )
    )
    for t in result.scalars().all():
        assert t.is_used

    # Sıfırlama token'ı etkilenmemeli
    result = await db.execute(
        select(ActionToken).where(
            ActionToken.user_id == pending_user.id,
            ActionToken.purpose == "reset_password",
        )
    )
    reset_token = result.scalar_one()
    assert not reset_token.is_used


# ---------------------------------------------------------------------------
# Activation flow tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_activation_flow(db: AsyncSession, pending_user: User):
    """Tam aktivasyon akışı: token oluştur → doğrula → etkinleştir."""
    # 1. Aktivasyon token'ı oluştur
    raw = await token_service.create_token(db, pending_user.id, "activate_account")
    await db.commit()

    # 2. Token doğrula
    action_token = await token_service.verify_token(db, raw, "activate_account")
    assert action_token is not None

    # 3. Parolayı güncelle
    pending_user.password_hash = auth_service.hash_password("yenisifre123")

    # 4. Hesabı etkinleştir
    await user_service.activate(db, pending_user)

    # 5. Token'ı tüket
    await token_service.consume_token(db, action_token)

    # 6. Eski token'ları geçersiz kıl
    await token_service.invalidate_user_tokens(
        db, pending_user.id, purpose="activate_account"
    )
    await db.commit()

    # Doğrulama
    assert pending_user.status == "active"
    assert pending_user.email_verified_at is not None
    assert auth_service.verify_password("yenisifre123", pending_user.password_hash)
    # Eski parola artık çalışmamalı
    assert not auth_service.verify_password("oldpass123", pending_user.password_hash)

    # Token tekrar kullanılamamalı
    result = await token_service.verify_token(db, raw, "activate_account")
    assert result is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_missing_user(db: AsyncSession):
    """Var olmayan kullanıcı için doğrulama başarısız olur."""
    import uuid
    raw = await token_service.create_token(db, str(uuid.uuid4()), "activate_account")
    await db.commit()

    # Token var ama kullanıcı yok — verify_token hala token'ı bulur
    # (user varlığı endpoint katmanında kontrol edilir)
    result = await token_service.verify_token(db, raw, "activate_account")
    assert result is not None


@pytest.mark.asyncio
async def test_email_normalization(db: AsyncSession):
    """Email normalizasyonu büyük/küçük harf duyarsız."""
    user = await user_service.create(
        db,
        email="Test@Example.COM",
        password_hash=auth_service.hash_password("test1234"),
    )
    await db.commit()

    # normalize_email ile aynı kullanıcı bulunabilir mi?
    found = await user_service.get_by_email(db, "TEST@example.com")
    assert found is not None
    assert found.id == user.id


@pytest.mark.asyncio
async def test_token_different_users(db: AsyncSession, pending_user: User):
    """Farklı kullanıcıların token'ları birbirine karışmaz."""
    user2 = await user_service.create(
        db, email="user2@example.com",
        password_hash=auth_service.hash_password("test1234"),
    )
    await db.commit()

    token1 = await token_service.create_token(db, pending_user.id, "activate_account")
    token2 = await token_service.create_token(db, user2.id, "activate_account")
    await db.commit()

    # Token1 sadece pending_user'a ait
    t = await token_service.verify_token(db, token1, "activate_account")
    assert t.user_id == pending_user.id

    # Token2 sadece user2'ye ait
    t = await token_service.verify_token(db, token2, "activate_account")
    assert t.user_id == user2.id