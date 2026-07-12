import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.stream_manager import manager, ChatStreamService
from app.services.chat_service import ChatPersistenceService
from app.core.security import decode_token

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: str = Query(...),
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(token)
        business_id = payload.business_id or 1
        user_id = int(payload.sub)
    except Exception as e:
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": "Invalid authentication token"})
        await websocket.close()
        return

    await manager.connect(websocket, session_id, {
        "business_id": business_id,
        "user_id": user_id,
        "site_id": site_id,
    })

    stream_service = ChatStreamService()
    persistence = ChatPersistenceService()

    try:
        chat_session = await persistence.get_or_create_session(
            db, business_id, session_id, user_id
        )

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await manager.send_message(session_id, {"type": "pong"})
                continue

            if msg_type == "message":
                question = data.get("content", "").strip()
                if not question:
                    await manager.send_message(session_id, {"type": "error", "content": "Empty question"})
                    continue

                await persistence.save_message(db, chat_session.id, "user", question)

                history = await persistence.get_session_history(db, session_id)

                await manager.send_message(session_id, {"type": "typing", "content": True})

                full_answer = ""
                sources_list = []

                try:
                    from app.services.rag import RAGService
                    rag = RAGService()
                    chunks = await rag.retrieve_chunks(site_id, question)

                    if not chunks:
                        await manager.send_message(session_id, {
                            "type": "token", "content": "I cannot answer based on the provided information."
                        })
                        full_answer = "I cannot answer based on the provided information."
                        await manager.send_message(session_id, {
                            "type": "done", "answer": full_answer
                        })
                        await persistence.save_message(db, chat_session.id, "ai", full_answer)
                        await manager.send_message(session_id, {"type": "typing", "content": False})
                        continue

                    context = "\n\n".join(
                        f"[{i+1}] {ch['content']}" for i, ch in enumerate(chunks)
                    )
                    sources_list = [
                        {"url": ch.get("metadata", {}).get("url", ""), "snippet": ch["content"][:200], "score": ch.get("score", 0)}
                        for ch in chunks
                    ]

                    await manager.send_message(session_id, {"type": "sources", "sources": sources_list})

                    prompt = rag._build_prompt(question, context, history)

                    from app.services.llm_service import LLMService
                    llm = LLMService()

                    async for token in llm.stream_generate(prompt):
                        full_answer += token
                        await manager.send_message(session_id, {"type": "token", "content": token})

                    confidence = rag._calculate_confidence(chunks)

                    await persistence.save_message(db, chat_session.id, "ai", full_answer)
                    await persistence.save_sources(db, chat_session.id, sources_list)

                    await manager.send_message(session_id, {"type": "confidence", "confidence": confidence})
                    await manager.send_message(session_id, {"type": "done", "answer": full_answer})

                except Exception as e:
                    logger.error(f"Chat error: {e}", exc_info=True)
                    await manager.send_message(session_id, {
                        "type": "error", "content": f"An error occurred: {str(e)}"
                    })

                await manager.send_message(session_id, {"type": "typing", "content": False})

            elif msg_type == "close":
                await persistence.close_session(db, session_id)
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(session_id)
