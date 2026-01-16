import json
from typing import Any, Optional

from psycopg import AsyncConnection
from psycopg.types.json import Json


async def setup_audit_tables(db_uri: str) -> None:
    """Cria tabelas de auditoria se ainda não existirem."""
    async with await AsyncConnection.connect(db_uri) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    thread_id TEXT PRIMARY KEY,
                    requester_id TEXT,
                    input_text TEXT,
                    status TEXT NOT NULL,
                    last_node TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS request_events (
                    id BIGSERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES requests(thread_id)
                        ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    payload JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        await conn.commit()


async def upsert_request(
    db_uri: str,
    thread_id: str,
    requester_id: Optional[str],
    input_text: Optional[str],
    status: str,
    last_node: Optional[str],
) -> None:
    """Insere ou atualiza o resumo de negócio da requisição."""
    async with await AsyncConnection.connect(db_uri) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO requests (
                    thread_id, requester_id, input_text, status, last_node
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (thread_id)
                DO UPDATE SET
                    requester_id = COALESCE(EXCLUDED.requester_id, requests.requester_id),
                    input_text = COALESCE(EXCLUDED.input_text, requests.input_text),
                    status = EXCLUDED.status,
                    last_node = EXCLUDED.last_node,
                    updated_at = NOW();
                """,
                (thread_id, requester_id, input_text, status, last_node),
            )
        await conn.commit()


async def insert_event(
    db_uri: str,
    thread_id: str,
    event_type: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    """Registra um evento de auditoria relacionado à requisição."""
    async with await AsyncConnection.connect(db_uri) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO request_events (thread_id, event_type, payload)
                VALUES (%s, %s, %s);
                """,
                (thread_id, event_type, Json(payload) if payload is not None else None),
            )
        await conn.commit()
