import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
except Exception as e:
    # Eğer paketler yoksa değerlendirme atlanabilir; açıklayıcı hata verilir.
    AutoTokenizer = None  # type: ignore
    AutoModelForCausalLM = None  # type: ignore
    torch = None  # type: ignore
    logger.info("transformers/torch yüklenmedi: %s", e)


class MedGemmaEvaluator:
    def __init__(self, model_name: str = "google/medgemma-27b-text-it"):
        if AutoTokenizer is None or AutoModelForCausalLM is None or torch is None:
            logger.warning(
                "transformers/torch yüklü değil; MedGemma devre dışı bırakıldı. "
                "Kurmak için: pip install transformers torch accelerate"
            )
            # işaretle, fonksiyonlar çağrıldığında güvenli fallback versin
            self._available = False
            return
        self._available = True
        self.model_name = model_name

        # Basit cihaz seçimi
        if torch.cuda.is_available():
            device_map = "auto"
            dtype = torch.bfloat16 if hasattr(torch, "bfloat16") else torch.float16
        else:
            device_map = None
            dtype = torch.float32

        logger.info("MedGemma yükleniyor: %s (device_map=%s)", model_name, device_map)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map=device_map,
        )
        # Eğer CPU ise model.to('cpu') gerekebilir, transformers zaten hallediyor.
        logger.info("MedGemma yüklendi: %s", model_name)

    def evaluate_student_response(self, case_context: str, student_answer: str, scoring_criteria: str) -> Dict[str, Any]:
        # Eğer evaluator kullanılamıyorsa güvenli fallback dön
        if not getattr(self, "_available", True):
            return {"puan": 0, "geri_bildirim": "MedGemma devre dışı bırakıldı (paketler eksik)."}
        prompt = f"""
You are an expert clinical educator. Evaluate the student answer for the case below and return JSON with keys "puan" (0-100) and "geri_bildirim" (detailed feedback).

PUANLAMA KRİTERLERİ:
{scoring_criteria}

VAKA BİLGİLERİ:
{case_context}

ÖĞRENCİNİN CEVABI:
{student_answer}

OUTPUT MUST BE STRICT JSON:
{{ "puan": <int>, "geri_bildirim": "<text>" }}
"""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=256, do_sample=False)
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # JSON kısmını ayıkla
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("JSON bulunamadı")
            json_part = text[start:end+1]
            parsed = json.loads(json_part)
            # normalize keys to expected types
            if "puan" in parsed:
                try:
                    parsed["puan"] = int(parsed["puan"])
                except Exception:
                    parsed["puan"] = 0
            return parsed
        except Exception as e:
            logger.exception("MedGemma çıktısı ayrıştırılamadı: %s", e)
            return {"puan": 0, "geri_bildirim": "Değerlendirme sırasında hata oluştu veya model JSON üretmedi."}