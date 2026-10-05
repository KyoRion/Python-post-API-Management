from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
)

from pydantic import BaseModel

from slugify import slugify

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uuid6 import uuid7

from . import models
from .database import get_db


app = FastAPI(
    title="Post API Management",
    version="1.0.0",
)


# ============================================================
# Request Schemas
# ============================================================

class PostTranslationCreate(BaseModel):
    locale: Literal["vi", "en"]

    title: str

    slug: Optional[str] = None

    excerpt: Optional[str] = None

    content: dict[str, Any]


class PostSeoCreate(BaseModel):
    meta_title: Optional[str] = None

    meta_description: Optional[str] = None

    meta_media_id: Optional[UUID] = None

    canonical_url: Optional[str] = None

    meta_robots_noindex: bool = False

    meta_robots_nofollow: bool = False

    schema_type: Optional[str] = None

    schema_data: Optional[dict[str, Any]] = None


class PostCreate(BaseModel):
    author_id: UUID

    type: str = "post"

    status: str = "draft"

    visibility: str = "public"

    featured_media_id: Optional[UUID] = None

    content_intent: Optional[str] = None

    published_at: Optional[datetime] = None

    scheduled_at: Optional[datetime] = None

    translation: PostTranslationCreate

    seo: PostSeoCreate


# ============================================================
# Helpers
# ============================================================

def generate_unique_slug(
    db: Session,
    locale: str,
    title: str,
    custom_slug: Optional[str],
    translation_id: UUID,
) -> str:
    """
    Generate slug.

    First post:
        photobook-la-gi

    Duplicate:
        photobook-la-gi-a85f52db
    """

    base_slug = slugify(
        custom_slug or title
    )

    if not base_slug:
        base_slug = "post"

    existing_slug = (
        db.query(
            models.PostTranslation.id
        )
        .filter(
            models.PostTranslation.locale == locale,
            models.PostTranslation.slug == base_slug,
        )
        .first()
    )

    if not existing_slug:
        return base_slug

    identifier = (
        str(translation_id)
        .replace("-", "")[-8:]
    )

    return f"{base_slug}-{identifier}"


# ============================================================
# Health
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Post API Management"
    }


@app.get("/sqlalchemy")
def test_sqlalchemy(
    db: Session = Depends(get_db),
):
    return {
        "status": "success"
    }


# ============================================================
# Get Posts
# ============================================================

@app.get("/posts")
def get_posts(
    db: Session = Depends(get_db),
):
    posts = (
        db.query(models.Post)
        .order_by(
            models.Post.created_at.desc()
        )
        .all()
    )

    return {
        "data": [
            {
                "id": str(post.id),
                "author_id": str(post.author_id),

                "type": post.type,

                "status": post.status,

                "visibility": post.visibility,

                "featured_media_id": (
                    str(post.featured_media_id)
                    if post.featured_media_id
                    else None
                ),

                "content_intent": post.content_intent,

                "published_at": post.published_at,

                "scheduled_at": post.scheduled_at,

                "created_at": post.created_at,

                "updated_at": post.updated_at,
            }
            for post in posts
        ]
    }


# ============================================================
# Create Post
# ============================================================

@app.post(
    "/posts",
    status_code=201,
)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
):
    try:
        # ====================================================
        # Generate UUIDv7
        # ====================================================

        post_id = uuid7()

        translation_id = uuid7()

        seo_id = uuid7()


        # ====================================================
        # Generate translation slug
        # ====================================================

        slug_translation = generate_unique_slug(
            db=db,
            locale=post.translation.locale,
            title=post.translation.title,
            custom_slug=post.translation.slug,
            translation_id=translation_id,
        )


        # ====================================================
        # Create Post
        # ====================================================

        db_post = models.Post(
            id=post_id,

            author_id=post.author_id,

            type=post.type,

            status=post.status,

            visibility=post.visibility,

            featured_media_id=post.featured_media_id,

            content_intent=post.content_intent,

            published_at=post.published_at,

            scheduled_at=post.scheduled_at,
        )


        # ====================================================
        # Create Translation
        # ====================================================

        db_translation = models.PostTranslation(
            id=translation_id,

            post_id=post_id,

            locale=post.translation.locale,

            title=post.translation.title,

            slug=slug_translation,

            excerpt=post.translation.excerpt,

            content=post.translation.content,
        )


        # ====================================================
        # Create SEO
        #
        # User chỉ cần nhập:
        #
        # meta_title
        # meta_description
        # meta_media_id
        #
        # Backend tự đồng bộ sang OG + Twitter
        # ====================================================

        db_seo = models.PostSEO(
            id=seo_id,

            post_id=post_id,

            locale=post.translation.locale,


            # ================================================
            # Standard Meta
            # ================================================

            meta_title=post.seo.meta_title,

            meta_description=(
                post.seo.meta_description
            ),

            canonical_url=(
                post.seo.canonical_url
            ),


            # ================================================
            # Open Graph
            # ================================================

            og_title=post.seo.meta_title,

            og_description=(
                post.seo.meta_description
            ),

            og_media_id=(
                post.seo.meta_media_id
            ),


            # ================================================
            # Twitter / X
            # ================================================

            twitter_title=(
                post.seo.meta_title
            ),

            twitter_description=(
                post.seo.meta_description
            ),

            twitter_media_id=(
                post.seo.meta_media_id
            ),


            # ================================================
            # Robots
            # ================================================

            robots_index=(
                not post.seo.meta_robots_noindex
            ),

            robots_follow=(
                not post.seo.meta_robots_nofollow
            ),


            # ================================================
            # Schema.org
            # ================================================

            schema_type=(
                post.seo.schema_type
            ),

            schema_data=(
                post.seo.schema_data
            ),
        )


        # ====================================================
        # Add all
        # ====================================================

        db.add_all(
            [
                db_post,
                db_translation,
                db_seo,
            ]
        )


        # ====================================================
        # Commit ONE transaction
        # ====================================================

        db.commit()


        return {
            "message": "Post created successfully",

            "data": {
                "post_id": str(post_id),

                "translation_id": str(
                    translation_id
                ),

                "seo_id": str(seo_id),

                "slug": slug_translation,

                "locale": (
                    post.translation.locale
                ),
            },
        }


    # ========================================================
    # DB constraint error
    # ========================================================

    except IntegrityError as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Database constraint violation"
                ),

                "error": str(e.orig),

                "type": type(e).__name__,
            },
        )


    # ========================================================
    # Other error
    # ========================================================

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Failed to create post"
                ),

                "error": str(e),

                "type": type(e).__name__,
            },
        )