from uuid6 import uuid7

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)

from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
    JSONB,
)

from sqlalchemy.orm import relationship

from .database import Base


# ============================================================
# POST
# ============================================================

class Post(Base):
    __tablename__ = "posts"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    author_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    type = Column(
        String(50),
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
    )

    visibility = Column(
        String(30),
        nullable=False,
        server_default=text("'public'"),
    )

    featured_media_id = Column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    content_intent = Column(
        String(100),
        nullable=True,
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    translations = relationship(
        "PostTranslation",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    seo_entries = relationship(
        "PostSEO",
        back_populates="post",
        cascade="all, delete-orphan",
    )


# ============================================================
# POST TRANSLATION
# ============================================================

class PostTranslation(Base):
    __tablename__ = "post_translations"

    __table_args__ = (
        UniqueConstraint(
            "locale",
            "slug",
            name="post_translations_locale_slug_unique",
        ),
    )

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "posts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    locale = Column(
        String(16),
        nullable=False,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    slug = Column(
        String(255),
        nullable=False,
    )

    excerpt = Column(
        Text,
        nullable=True,
    )

    content = Column(
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    post = relationship(
        "Post",
        back_populates="translations",
    )


# ============================================================
# POST SEO
# ============================================================

class PostSEO(Base):
    __tablename__ = "post_seo"

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "locale",
            name="post_seo_post_id_locale_unique",
        ),
    )

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "posts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    locale = Column(
        String(16),
        nullable=False,
        index=True,
    )

    # Standard SEO
    meta_title = Column(
        String,
        nullable=True,
    )

    meta_description = Column(
        Text,
        nullable=True,
    )

    canonical_url = Column(
        String(2048),
        nullable=True,
    )

    # Open Graph
    og_title = Column(
        String,
        nullable=True,
    )

    og_description = Column(
        Text,
        nullable=True,
    )

    # PostgreSQL đã có FK do Laravel migration quản lý.
    # Không khai ForeignKey("media.id") tại đây vì
    # SQLAlchemy chưa map Media model.
    og_media_id = Column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Twitter / X
    twitter_title = Column(
        String,
        nullable=True,
    )

    twitter_description = Column(
        Text,
        nullable=True,
    )

    twitter_media_id = Column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Robots
    robots_index = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    robots_follow = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    # Schema.org
    schema_type = Column(
        String,
        nullable=True,
    )

    schema_data = Column(
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    post = relationship(
        "Post",
        back_populates="seo_entries",
    )