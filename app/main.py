from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException
from psycopg2 import IntegrityError
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slugify import slugify
from uuid6 import uuid7

from . import models
from .database import get_db

app = FastAPI()

class PostTranslationCreate(BaseModel):
    locale: Literal["en", "vi"]
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

    translation: PostTranslationCreate
    seo: PostSeoCreate

# Functionally
def generate_unique_slug(
    db: Session,
    locale: str,
    title: str,
    custom_slug: str | None,
    translation_id,
) -> str:
    base_slug = slugify(custom_slug or title)

    exists = (
        db.query(models.PostTranslation.id)
        .filter(
            models.PostTranslation.locale == locale,
            models.PostTranslation.slug == base_slug
        )
        .first()
    )

    if not exists:
        return base_slug

    suffix = str(translation_id).replace("-", "")[-8:]

    return f"{base_slug}-{suffix}"

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(models.Post).all()

    return {"data": posts}

@app.post("/posts", status_code=201)
def create_post(
    post: PostCreate, 
    db: Session = Depends(get_db)
):
    try: 
        # ========================================
        # Generate IDs
        # ========================================

        post_id = str(uuid7())
        translation_id = str(uuid7())
        seo_id = str(uuid7())

        # ========================================
        # Generate slug
        # ========================================

        base_slug = slugify(
            post.translation.slug
            or post.translation.title
        )

        existing_slug = (
            db.query(models.PostTranslation.id)
            .filter(
                models.PostTranslation.locale
                == post.translation.locale,

                models.PostTranslation.slug
                == base_slug
            )
            .first()
        )

        slug_translation = (
            f"{base_slug}-{str(translation_id).replace('-', '')[-8:]}"
            if existing_slug
            else base_slug
        )

        # ========================================
        # Create Post
        # ========================================

        db_post = models.Post(
            id=post_id,
            author_id=post.author_id,
            type=post.type,
            status=post.status,
            visibility=post.visibility,
            featured_media_id=post.featured_media_id,
            content_intent=post.content_intent,
            published_at=post.published_at,
        )

        # ========================================
        # Create Translation
        # ========================================

        db_translation = models.PostTranslation(
            id=translation_id,
            post_id=post_id,
            locale=post.translation.locale,
            title=post.translation.title,
            slug=slug_translation,
            excerpt=post.translation.excerpt,
            content=post.translation.content,
        )

        # ========================================
        # Create SEO
        # ========================================

        db_seo = models.PostSEO(
            id=seo_id,
            post_id=post_id,
            locale=post.translation.locale,

            # Standard SEO
            meta_title=post.seo.meta_title,
            meta_description=post.seo.meta_description,
            canonical_url=post.seo.canonical_url,

            # Open Graph
            og_title=post.seo.meta_title,
            og_description=post.seo.meta_description,
            og_media_id=post.seo.meta_media_id,

            # Twitter / X
            twitter_title=post.seo.meta_title,
            twitter_description=post.seo.meta_description,
            twitter_media_id=post.seo.meta_media_id,

            # Robots
            robots_index=not post.seo.meta_robots_noindex,
            robots_follow=not post.seo.meta_robots_nofollow,

            # Structured data
            schema_type=post.seo.schema_type,
            schema_data=post.seo.schema_data,
        )

        # ========================================
        # Commit all 3 tables
        # ========================================

        db.add_all([
            db_post,
            db_translation,
            db_seo,
        ])

        db.commit()

        return {
            "message": "Post created successfully",
            "data": {
                "post_id": str(post_id),
                "translation_id": str(translation_id),
                "seo_id": str(seo_id),
                "slug": slug_translation,
            }
        }

    except IntegrityError as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail={
                "message": "Post conflicts with existing data",
                "error": str(e.orig),
            }
        )

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to create post",
                "error": str(e),
                "type": type(e).__name__,
            }
        )

