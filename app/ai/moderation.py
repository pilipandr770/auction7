"""KI-Moderation von Auktionslosen.

Prüft Titel/Beschreibung beim Erstellen einer Auktion auf:
  - verbotene Artikel (Waffen, Drogen, Fälschungen, illegale/Erwachsenen-Inhalte ...)
  - Betrugs-/Fake-Signale
  - offensichtlich unrealistischen Preis im Verhältnis zur Beschreibung

Ergebnis: decision = approve | flag | reject, plus Begründung.
Fail-open-Verhalten bei fehlendem Schlüssel/Fehler: status 'pending' (Admin prüft),
Erstellung wird NICHT blockiert — außer bei eindeutig verbotenen Inhalten.
"""
import os
import json

# Mögliche Entscheidungen
APPROVE = "approved"
FLAG = "flagged"
REJECT = "rejected"
PENDING = "pending"


def is_configured():
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key) and not key.startswith("sk-dummy")


_SYSTEM = (
    "Du bist ein Moderationssystem für einen EU-Marktplatz (Auktionen). "
    "Bewerte ein Inserat anhand von Titel und Beschreibung. "
    "Antworte AUSSCHLIESSLICH als JSON mit den Feldern: "
    "decision ('approve' | 'flag' | 'reject'), category (kurzes Schlagwort), "
    "reason (kurze Begründung auf Deutsch). "
    "'reject' NUR bei klar verbotenen Artikeln: Waffen, Munition, Drogen, "
    "Arzneimittel, gefälschte Markenware, Diebesgut, Tierprodukte (Elfenbein), "
    "Ausweise/Dokumente, sexuelle/jugendgefährdende Inhalte, illegale Dienste. "
    "'flag' bei Verdacht auf Betrug, vage/irreführende Angaben, unrealistischem Preis "
    "ODER wenn der Artikel gebraucht/benutzt/refurbished wirkt (nur NEUE, unbenutzte Ware erlaubt). "
    "Ansonsten 'approve'."
)


def moderate_listing(title, description, starting_price=None):
    """Gibt dict {status, reason, category} zurück. Wirft NICHT."""
    if not is_configured():
        return {"status": PENDING, "reason": "KI-Moderation nicht konfiguriert", "category": ""}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        user_content = (
            f"Titel: {title}\n"
            f"Beschreibung: {description}\n"
            f"Startpreis (EUR): {starting_price if starting_price is not None else 'n/a'}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        data = json.loads(resp.choices[0].message.content)
        decision = (data.get("decision") or "approve").lower()
        reason = data.get("reason", "")
        category = data.get("category", "")

        status = {"approve": APPROVE, "flag": FLAG, "reject": REJECT}.get(decision, FLAG)
        return {"status": status, "reason": reason, "category": category}

    except Exception as e:
        # Fail-open für Verfügbarkeit, aber zur Admin-Prüfung markieren
        print(f"[AI moderation error] {e}")
        return {"status": PENDING, "reason": "KI-Prüfung fehlgeschlagen", "category": ""}


_REVIEW_SYSTEM = (
    "Du prüfst eine Verkäuferbewertung auf einem Marktplatz auf Echtheit/Zulässigkeit. "
    "Antworte AUSSCHLIESSLICH als JSON: ok (true|false), reason (kurz, Deutsch). "
    "ok=false bei: Beleidigungen/Hassrede, Spam/Werbung, offensichtlich gefälschtem oder "
    "irrelevantem Inhalt, persönlichen Daten. Sonst ok=true."
)


def check_review(text):
    """Prüft Bewertungstext. Gibt {ok: bool, reason} zurück. Wirft NICHT.
    Ohne Schlüssel/bei Fehler: ok=True (fail-open)."""
    if not text or not text.strip():
        return {"ok": True, "reason": ""}
    if not is_configured():
        return {"ok": True, "reason": "KI-Prüfung nicht konfiguriert"}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _REVIEW_SYSTEM},
                {"role": "user", "content": text[:1000]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=120,
        )
        data = json.loads(resp.choices[0].message.content)
        return {"ok": bool(data.get("ok", True)), "reason": data.get("reason", "")}
    except Exception as e:
        print(f"[AI review check error] {e}")
        return {"ok": True, "reason": "KI-Prüfung fehlgeschlagen"}
