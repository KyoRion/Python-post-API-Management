from datetime import datetime
from gettext import translation
from http.client import HTTPException
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.params import Body
from opentelemetry.trace import Status
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import time
from uuid6 import uuid7
from psycopg2.extras import Json
from slugify import slugify

app = FastAPI()

class PostTranslationCreate(BaseModel):
    locale: str
    title: str
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: dict[str, Any]

class PostSeoCreate(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_media_id: Optional[str] = None
    meta_robots_noindex: bool = False
    meta_robots_nofollow: bool = False

class PostCreate(BaseModel):
    author_id: str
    type: str = "post"
    status: str = "draft"
    visibility: str = "public"

    featured_media_id: Optional[str] = None
    content_intent: Optional[str] = None
    published_at: Optional[datetime] = None

    translation: PostTranslationCreate
    seo: PostSeoCreate

while True:
    try:
        conn = psycopg2.connect(
            host='localhost', 
            database='app', 
            user='postgres', 
            password='secret',
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        print("Database connection was successful!")
        break
    except Exception as error:
        print("Database connection failed!")
        print("Error:", error)
        time.sleep(2)

def get_connection():
    return psycopg2.connect(
            host='localhost', 
            database='app', 
            user='postgres', 
            password='secret',
            cursor_factory=RealDictCursor
        )

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/posts")
def get_posts():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""SELECT * FROM posts""")
    posts = cursor.fetchall()
    
    return {"data": posts}

@app.post("/posts", status_code=201)
def create_post(post: PostCreate):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # ========================================
        # Generate IDs
        # ========================================

        post_id = str(uuid7())
        translation_id = str(uuid7())
        seo_id = str(uuid7())

        # ========================================
        # Create post
        # ========================================

        cursor.execute(
            """
            INSERT INTO posts (
                id,
                author_id,
                type,
                status,
                visibility,
                featured_media_id,
                content_intent,
                published_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                post_id,
                str(post.author_id),
                post.type,
                post.status,
                post.visibility,
                str(post.featured_media_id) if post.featured_media_id else None,
                post.content_intent,
                post.published_at
            )
        )

        # ========================================
        # Generate base slug
        # ========================================

        base_slug = slugify(
            post.translation.slug
            if getattr(post.translation, "slug", None)
            else post.translation.title
        )

        slug_translation = base_slug

        # ========================================
        # Create translation
        # ========================================

        cursor.execute(
            """
            INSERT INTO post_translations (
                id,
                post_id,
                locale,
                title,
                slug,
                excerpt,
                content
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (locale, slug) DO NOTHING
            RETURNING id
            """,
            (
                translation_id,
                post_id,
                post.translation.locale,
                post.translation.title,
                slug_translation,
                post.translation.excerpt,
                Json(post.translation.content),
            )
        )

        translation = cursor.fetchone()

        # ========================================
        # Duplicate slug
        # ========================================

        if translation is None:
            slug_translation = (
                f"{base_slug}-{translation_id[-8:]}"
            )

            cursor.execute(
                """
                INSERT INTO post_translations (
                    id,
                    post_id,
                    locale,
                    title,
                    slug,
                    excerpt,
                    content
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    translation_id,
                    post_id,
                    post.translation.locale,
                    post.translation.title,
                    slug_translation,
                    post.translation.excerpt,
                    Json(post.translation.content),
                )
            )

        # ========================================
        # Create SEO
        # ========================================

        cursor.execute(
            """
            INSERT INTO post_seo (
                id,
                post_id,
                locale,
                meta_title,
                og_title,
                twitter_title,
                meta_description,
                og_description,
                twitter_description,
                og_media_id,
                twitter_media_id,
                robots_index,
                robots_follow
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                seo_id,
                post_id,
                post.translation.locale,

                post.seo.meta_title,
                post.seo.meta_title,
                post.seo.meta_title,

                post.seo.meta_description,
                post.seo.meta_description,
                post.seo.meta_description,

                (
                    str(post.seo.meta_media_id)
                    if post.seo.meta_media_id
                    else None
                ),
                (
                    str(post.seo.meta_media_id)
                    if post.seo.meta_media_id
                    else None
                ),

                not post.seo.meta_robots_noindex,
                not post.seo.meta_robots_nofollow,
            )
        )

        # ========================================
        # Commit transaction
        # ========================================

        conn.commit()

        return {
            "message": "Post created successfully",
            "data": {
                "post_id": post_id,
                "translation_id": translation_id,
                "seo_id": seo_id,
                "slug": slug_translation
            }
        }

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to create post",
                "error": str(e),
                "type": type(e).__name__
            }
        )

    finally:
        cursor.close()
        conn.close()
