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
        ]

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        models_to_try = [self.primary_model] + self.fallback_models

        for model in models_to_try:
            try:
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                resp = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048,
                )
                content = resp.choices[0].message.content or ""
                logger.info(f"LLM success: model={model}, tokens={resp.usage.total_tokens if resp.usage else 'N/A'}")
                return content
            except Exception as e:
                last_error = e
                logger.warning(f"LLM fallback from {model}: {e}")
                continue

        logger.error(f"All LLM models failed: {last_error}")
        raise last_error

    async def stream_generate(self, prompt: str, system_prompt: str | None = None) -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        models_to_try = [self.primary_model] + self.fallback_models

        for model in models_to_try:
            try:
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Stream fallback from {model}: {e}")
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

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        for m in self.all_models:
            if m["model"] == model:
                return (input_tokens * m["cost_per_1k_input"] + output_tokens * m["cost_per_1k_output"]) / 1000
        return 0.0
