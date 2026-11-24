"""Boletín semanal para el restaurante, redactado por un modelo de lenguaje.

Si no hay API key o la llamada falla, se arma un boletín con plantilla
para que el producto nunca se quede sin mensaje.
"""
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from src.lista import recommendation
from src.model.tracking import llm_span

SYSTEM = """Eres el asistente de compras de AgroPrecio. Escribes para dueños de
restaurantes pequeños de Cali que compran en la central mayorista Cavasa.
Reglas:
- Español sencillo, tono cercano, sin tecnicismos.
- Máximo 180 palabras.
- Usa solo los productos y cifras que vienen en los datos. No inventes precios.
- Empieza por lo que conviene comprar ya, luego lo que conviene esperar.
- Cierra con una frase corta recordando que es una estimación."""


def build_prompt(alerts):
    rows = [
        {
            "producto": r["producto"],
            "precio_kg": int(r["precio"]),
            "cambio_semana_pasada_pct": round(r["cambio_1s"] * 100, 1),
            "prediccion": r["prediccion"] if r.get("senal", "clara") == "clara" else "sin señal clara",
            "confianza_pct": round(r["confianza"] * 100),
        }
        for _, r in alerts.iterrows()
    ]
    week = str(alerts["semana_inicio"].iloc[0])[:10]
    return (f"Semana que inicia el {week}. Predicciones para la próxima semana en Cavasa:\n"
            f"{json.dumps(rows, ensure_ascii=False, indent=1)}\n\n"
            "Escribe el boletín de esta semana.")


def template_bulletin(alerts):
    rec = recommendation(alerts)
    buy = alerts[rec == "sube"]["producto"].tolist()
    wait = alerts[rec == "baja"]["producto"].tolist()
    parts = ["Boletín AgroPrecio de la semana."]
    if buy:
        parts.append("Conviene comprar ya: " + ", ".join(buy) + ". Se espera que suban.")
    if wait:
        parts.append("Puedes esperar con: " + ", ".join(wait) + ". Se espera que bajen.")
    parts.append("En el resto no hay una señal clara: compra como siempre. Son estimaciones con datos del SIPSA - DANE.")
    return " ".join(parts)


def numbers_are_grounded(text, alerts):
    """Revisa que los números grandes del texto (precios) existan en los datos."""
    allowed = {int(p) for p in alerts["precio"]}
    found = [int(n.replace(".", "")) for n in re.findall(r"\d{1,3}(?:\.\d{3})+|\d{4,}", text)]
    return all(any(abs(n - a) <= 1 for a in allowed) for n in found if n > 300)


def generate_bulletin(alerts, cfg, logger):
    with llm_span("boletin_semanal", logger) as span:
        bulletin, record = _generate(alerts, cfg, logger)
        span.set_inputs({"system": SYSTEM, "prompt": record["prompt"]})
        span.set_outputs({"texto": bulletin["texto"], "fuente": bulletin["fuente"]})
        span.set_attributes({k: v for k, v in record.items() if k not in ("prompt", "respuesta")})
        return bulletin


def _generate(alerts, cfg, logger):
    prompt = build_prompt(alerts)
    record = {"fecha": datetime.now().isoformat(timespec="seconds"),
              "modelo": cfg["llm"]["model"], "prompt": prompt}
    text, source = None, "plantilla"

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()
            start = time.time()
            resp = client.messages.create(
                model=cfg["llm"]["model"],
                max_tokens=cfg["llm"]["max_tokens"],
                output_config={"effort": "low"},
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            record["latencia_s"] = round(time.time() - start, 2)
            record["tokens_entrada"] = resp.usage.input_tokens
            record["tokens_salida"] = resp.usage.output_tokens
            record["stop_reason"] = resp.stop_reason
            if resp.stop_reason == "end_turn":
                text = "".join(b.text for b in resp.content if b.type == "text").strip()
                source = "llm"
        except Exception as e:
            logger.warning("Falló la llamada al LLM, se usa plantilla: %s", e)
            record["error"] = str(e)

    if text and not numbers_are_grounded(text, alerts):
        logger.warning("El boletín del LLM trae cifras que no están en los datos; se usa plantilla")
        record["descartado"] = text
        text, source = None, "plantilla"

    if not text:
        text = template_bulletin(alerts)

    record["fuente"] = source
    record["respuesta"] = text
    log_path = Path(cfg["paths"]["logs"]) / "llm.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"fecha": record["fecha"], "semana_inicio": str(alerts["semana_inicio"].iloc[0])[:10],
            "fuente": source, "texto": text}, record
