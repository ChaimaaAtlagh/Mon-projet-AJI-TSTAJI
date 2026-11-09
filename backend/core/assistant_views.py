"""Authenticated Groq relay so the Desktop package never contains an API key."""

import os

from openai import OpenAI
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


SYSTEM_INSTRUCTIONS = (
    "Tu es l'assistant IA de AJI TSTAJI, une application qui aide les étudiants "
    "à rechercher des stages et des emplois, surtout en informatique, "
    "intelligence artificielle et Data à Marrakech. Réponds en français simple "
    "ou en darija marocaine selon la langue de l'utilisateur. Donne des conseils "
    "concrets et faciles à suivre. N'invente jamais des offres d'emploi, des "
    "entreprises ou des coordonnées. Si tu ne connais pas une information, "
    "précise-le. Le nom de l'application est AJI TSTAJI."
)


class AssistantChatView(APIView):
    """Forward a bounded conversation to Groq using a server-side credential."""

    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "assistant"
    max_messages = 24
    max_message_chars = 30000
    max_total_chars = 50000

    def post(self, request):
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return Response(
                {"detail": "L'assistant IA n'est pas configuré sur le serveur."},
                status=503,
            )

        messages = request.data.get("messages")
        if not isinstance(messages, list) or not 1 <= len(messages) <= self.max_messages:
            return Response({"detail": "Historique de conversation invalide."}, status=400)

        normalized = []
        total_chars = 0
        for item in messages:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                return Response({"detail": "Message de conversation invalide."}, status=400)
            content = item.get("content")
            if not isinstance(content, str):
                return Response({"detail": "Contenu de message invalide."}, status=400)
            content = content.strip()
            if not content or len(content) > self.max_message_chars:
                return Response({"detail": "La taille d'un message est invalide."}, status=400)
            total_chars += len(content)
            if total_chars > self.max_total_chars:
                return Response({"detail": "La conversation est trop longue."}, status=413)
            normalized.append({"role": item["role"], "content": content})

        if normalized[-1]["role"] != "user":
            return Response({"detail": "Le dernier message doit venir de l'utilisateur."}, status=400)

        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=25.0,
            )
            result = client.chat.completions.create(
                model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip(),
                messages=[{"role": "system", "content": SYSTEM_INSTRUCTIONS}, *normalized],
                max_completion_tokens=700,
            )
            reply = result.choices[0].message.content
            if not isinstance(reply, str) or not reply.strip():
                return Response(
                    {"detail": "L'assistant IA n'a pas retourné de réponse."},
                    status=502,
                )
            return Response({"reply": reply.strip()})
        except Exception as exc:
            if getattr(exc, "status_code", None) == 429:
                return Response(
                    {"detail": "La limite d'utilisation de l'assistant IA est atteinte."},
                    status=429,
                )
            # Do not return provider exception details; they can include request
            # metadata that must remain on the server.
            return Response(
                {"detail": "L'assistant IA est temporairement indisponible."},
                status=502,
            )
