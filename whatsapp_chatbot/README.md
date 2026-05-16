# Chatbot WhatsApp Flask avec BSP

Ce projet fournit un webhook Flask pour recevoir des messages WhatsApp via un BSP comme `respond.io`, `WATI`, ou un tunnel local `ngrok` en mode simulation.

## Installation

```powershell
cd "C:\Users\aa\Documents\New project 2\whatsapp_chatbot"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Pour tester depuis Internet en local:

```powershell
ngrok http 5000
```

Configure ensuite l'URL webhook de ton BSP vers:

```text
https://TON-SOUS-DOMAINE.ngrok-free.app/webhook
```

## Endpoints utiles

- `POST /webhook`: reception des messages entrants du BSP.
- `POST /absence/on`: active le mode absent manuel.
- `POST /absence/off`: desactive le mode absent manuel.
- `GET /status`: verifie les horaires, le mode absent et les timeouts en attente.
- `POST /followup`: exemple de relance business-initiated avec template Meta pre-approuve.

## Points critiques WhatsApp

- Le bot ignore les messages envoyes par toi-meme avec `if message.get("from_me"): continue`.
- Les IDs de chat individuels sont normalises au format `{phone}@s.whatsapp.net`.
- Les reponses automatiques apres message client utilisent `sendMessageText` seulement si la fenetre client de 24h est ouverte.
- Les relances initiees par l'entreprise utilisent `sendTemplateMessage`, jamais un texte libre hors session 24h.

## Exemple de webhook local

```powershell
Invoke-RestMethod -Method Post http://localhost:5000/webhook `
  -ContentType "application/json" `
  -Body '{"messages":[{"id":"m1","chat_id":"33612345678@s.whatsapp.net","from":"+33612345678","from_me":false,"type":"text","text":"Bonjour"}]}'
```

En mode `BSP_PROVIDER=mock`, les envois sont simplement affiches dans la console.
