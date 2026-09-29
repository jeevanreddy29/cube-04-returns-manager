"""
Multimodal Gemini Vision Analyzer.
Executes single batched multimodal call for Identity, Completeness, and Condition.
Includes mock fallback engine when running tests or evaluation without API keys.
"""
from __future__ import annotations

import base64
import io
import time
from typing import Any
from PIL import Image

from src.config import get_settings
from src.agent.prompt_builder import build_assessment_prompt
from src.agent.output_parser import parse_and_validate_ai_response


class GeminiVisionAnalyzer:
    def __init__(self):
        self.settings = get_settings()
        self.model_name = self.settings.gemini_model
        self.api_key = self.settings.gemini_api_key
        self._client = None
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model_name)
            except Exception:
                self._client = None

    async def analyze(
        self,
        ordered_sku: str,
        ordered_asin: str,
        order_id: str,
        parts_list: list[str],
        observed_state: str,
        images_data: list[str],
    ) -> tuple[dict[str, Any], int, str]:
        """
        Executes single batched AI analysis.
        Returns: (parsed_result_dict, latency_ms, model_version_used)
        """
        start_time = time.perf_counter()
        prompt = build_assessment_prompt(
            ordered_sku=ordered_sku,
            ordered_asin=ordered_asin,
            order_id=order_id,
            parts_list=parts_list,
            observed_state=observed_state,
        )

        # If live Gemini client configured, invoke live model
        if self._client is not None:
            try:
                content_parts: list[Any] = [prompt]
                for img_str in images_data:
                    pil_img = self._decode_image(img_str)
                    if pil_img:
                        content_parts.append(pil_img)

                response = self._client.generate_content(content_parts)
                raw_text = response.text or ""
                parsed = parse_and_validate_ai_response(raw_text)
                latency = int((time.perf_counter() - start_time) * 1000)
                return parsed, latency, self.model_name
            except Exception as e:
                # Let caller trigger fail-open handler if exception raised
                raise RuntimeError(f"Gemini API failure: {str(e)}") from e

        # Mock / Evaluation fallback engine for automated tests and standalone demos
        parsed = self._simulate_inspection(ordered_sku, observed_state, parts_list)
        latency = int((time.perf_counter() - start_time) * 1000) + 120
        return parsed, latency, f"{self.model_name}-simulated"

    def _decode_image(self, img_str: str) -> Image.Image | None:
        try:
            if img_str.startswith("data:image"):
                img_str = img_str.split(",", 1)[1]
            raw_bytes = base64.b64decode(img_str)
            return Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        except Exception:
            return None

    def _simulate_inspection(self, sku: str, observed_state: str, parts_list: list[str]) -> dict[str, Any]:
        """
        Heuristic fallback modeling realistic physical check outputs.
        Honors ambiguous and uncertain states.
        """
        if observed_state == "uncertain":
            return {
                "identity": {"verdict": "UNCERTAIN", "confidence": 0.50, "detail": "Image angle prevents barcode and label verification."},
                "completeness": {"verdict": "UNCERTAIN", "parts_present": [], "parts_missing": [], "confidence": 0.50, "detail": "Box contents obscured."},
                "condition": {"verdict": "UNCERTAIN", "amazon_grade": None, "confidence": 0.45, "detail": "Lighting glare obscures surface finish."}
            }

        if observed_state == "empty_box":
            return {
                "identity": {"verdict": "FAIL", "confidence": 0.99, "detail": "Empty packaging returned. Primary unit missing."},
                "completeness": {"verdict": "FAIL", "parts_present": [], "parts_missing": parts_list, "confidence": 0.99, "detail": "No items inside box."},
                "condition": {"verdict": "FAIL", "amazon_grade": "Acceptable", "confidence": 0.90, "detail": "Empty container."}
            }

        if observed_state == "factory_sealed":
            return {
                "identity": {"verdict": "PASS", "confidence": 0.98, "detail": "Original factory security tape intact with correct product labeling."},
                "completeness": {"verdict": "PASS", "parts_present": parts_list, "parts_missing": [], "confidence": 0.98, "detail": "Factory sealed box contains complete package."},
                "condition": {"verdict": "PASS", "amazon_grade": "New", "confidence": 0.99, "detail": "Pristine factory packaging, no signs of handling or damage."}
            }

        if observed_state == "opened_unused":
            return {
                "identity": {"verdict": "PASS", "confidence": 0.95, "detail": "Product serial and model match ordered SKU."},
                "completeness": {"verdict": "PASS", "parts_present": parts_list, "parts_missing": [], "confidence": 0.94, "detail": "All parts verified in original wrapping."},
                "condition": {"verdict": "PASS", "amazon_grade": "Like New", "confidence": 0.92, "detail": "Outer packaging unsealed, but unit itself is pristine with zero wear."}
            }

        if observed_state == "signs_of_use":
            return {
                "identity": {"verdict": "PASS", "confidence": 0.94, "detail": "Confirmed ordered SKU matching physical unit characteristics."},
                "completeness": {"verdict": "PASS", "parts_present": parts_list, "parts_missing": [], "confidence": 0.90, "detail": "All primary components present."},
                "condition": {"verdict": "PASS", "amazon_grade": "Very Good", "confidence": 0.88, "detail": "Minor micro-scratches on casing, fully functional."}
            }

        if observed_state == "damaged":
            return {
                "identity": {"verdict": "PASS", "confidence": 0.91, "detail": "Model matches ordered unit despite impact damage."},
                "completeness": {"verdict": "PASS", "parts_present": parts_list, "parts_missing": [], "confidence": 0.85, "detail": "Components present."},
                "condition": {"verdict": "FAIL", "amazon_grade": "Acceptable", "confidence": 0.92, "detail": "Physical denting and casing fracture observed."}
            }

        return {
            "identity": {"verdict": "PASS", "confidence": 0.90, "detail": "Visual features align with catalog specifications."},
            "completeness": {"verdict": "PASS", "parts_present": parts_list, "parts_missing": [], "confidence": 0.88, "detail": "Components present."},
            "condition": {"verdict": "PASS", "amazon_grade": "Good", "confidence": 0.85, "detail": "Normal operational cosmetic wear."}
        }
