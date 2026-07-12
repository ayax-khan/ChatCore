import json
import logging
from typing import AsyncGenerator, Optional
import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.primary_model = settings.OPENAI_CHAT_MODEL
        self.fallback_models = ["gpt-4o-mini", "gpt-3.5-turbo"]
        self.all_models = [
            {"provider": "openai", "model": settings.OPENAI_CHAT_MODEL, "cost_per_1k_input": 0.00125, "cost_per_1k_output": 0.01},
            {"provider": "openai", "model": "gpt-4o-mini", "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006},
            {"provider": "openai", "model": "gpt-4.1", "cost_per_1k_input": 0.002, "cost_per_1k_output": 0.008},
            {"provider": "gemini", "model": "gemini-2.0-flash", "cost_per_1k_input": 0.0001, "cost_per_1k_output": 0.0004},
            {"provider": "claude", "model": "claude-3-sonnet-20240229", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
            {"provider": "openrouter", "model": "openai/gpt-4o-mini", "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006},
        ]

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        fallback_chain = [
            ("openai", self.primary_model),
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-3.5-turbo"),
            ("gemini", "gemini-2.0-flash"),
            ("claude", "claude-3-sonnet-20240229"),
            ("openrouter", "openai/gpt-4o-mini"),
        ]

        for provider, model in fallback_chain:
            try:
                if provider == "openai":
                    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    resp = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=2048,
                    )
                    content = resp.choices[0].message.content or ""
                    logger.info(f"LLM success: provider={provider}, model={model}, tokens={resp.usage.total_tokens if resp.usage else 'N/A'}")
                    return content
                elif provider == "gemini":
                    return await self._call_gemini(prompt, model)
                elif provider == "claude":
                    return await self._call_claude(prompt, model)
                elif provider == "openrouter":
                    return await self._call_openrouter(prompt, model)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM fallback from {provider}/{model}: {e}")
                continue

        logger.error(f"All LLM models failed: {last_error}")
        raise last_error

    async def stream_generate(self, prompt: str, system_prompt: str | None = None) -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        fallback_chain = [
            ("openai", self.primary_model),
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-3.5-turbo"),
            ("gemini", "gemini-2.0-flash"),
            ("claude", "claude-3-sonnet-20240229"),
            ("openrouter", "openai/gpt-4o-mini"),
        ]

        for provider, model in fallback_chain:
            try:
                if provider == "openai":
                    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    stream = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=2048,
                        stream=True,
                    )
                    async for chunk in stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            yield delta.content
                    return
                elif provider == "gemini":
                    async for token in self._stream_gemini(prompt, model):
                        yield token
                    return
                elif provider == "claude":
                    async for token in self._stream_claude(prompt, model):
                        yield token
                    return
                elif provider == "openrouter":
                    async for token in self._stream_openrouter(prompt, model):
                        yield token
                    return
            except Exception as e:
                last_error = e
                logger.warning(f"Stream fallback from {provider}/{model}: {e}")
                continue

        yield f"Error: All models failed - {last_error}"

    async def generate_with_provider(
        self,
        prompt: str,
        provider: str = "openai",
        model: str | None = None,
    ) -> str:
        if provider == "openai":
            return await self.generate(prompt)
        elif provider == "gemini":
            return await self._call_gemini(prompt, model or "gemini-2.0-flash")
        elif provider == "claude":
            return await self._call_claude(prompt, model or "claude-3-sonnet-20240229")
        elif provider == "openrouter":
            return await self._call_openrouter(prompt, model or "openai/gpt-4o-mini")
        else:
            return await self.generate(prompt)

    async def _call_gemini(self, prompt: str, model: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gen_model = genai.GenerativeModel(model)
            resp = await gen_model.generate_content_async(prompt)
            return resp.text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            raise

    async def _stream_gemini(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gen_model = genai.GenerativeModel(model)
            resp = await gen_model.generate_content_async(prompt, stream=True)
            async for chunk in resp:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini stream failed: {e}")
            raise

    async def _call_claude(self, prompt: str, model: str) -> str:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = await client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text if resp.content else ""
        except Exception as e:
            logger.error(f"Claude call failed: {e}")
            raise

    async def _stream_claude(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            async with client.messages.stream(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude stream failed: {e}")
            raise

    async def _call_openrouter(self, prompt: str, model: str) -> str:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2048,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}")
            raise

    async def _stream_openrouter(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2048,
                        "stream": True,
                    },
                    timeout=60,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                return
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                if delta.get("content"):
                                    yield delta["content"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"OpenRouter stream failed: {e}")
            raise

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        for m in self.all_models:
            if m["model"] == model:
                return (input_tokens * m["cost_per_1k_input"] + output_tokens * m["cost_per_1k_output"]) / 1000
        return 0.0