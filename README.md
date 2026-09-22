# CSBOT — Assistant Virtuel de Copropriété & Outils pour le Conseil Syndical

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue?logo=python&logoColor=white)
![Framework](https://img.shields.io/badge/Telegram-aiogram%20v3-2CA5E0?logo=telegram&logoColor=white)
![Database](https://img.shields.io/badge/Database-MariaDB%20%2F%20SQLAlchemy%202.0-003545?logo=mariadb&logoColor=white)
![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20%26%20Mistral%20AI-4285F4?logo=google&logoColor=white)
![Automation](https://img.shields.io/badge/Automation-n8n%20Webhooks-EA4B71?logo=n8n&logoColor=white)
![Financial Integration](https://img.shields.io/badge/Finance-CPTCOPRO%20Connector-00C853)
![Container](https://img.shields.io/badge/Docker-Docker%20Compose-2496ED?logo=docker&logoColor=white)

**Solution moderne et complète pour assister les copropriétaires, sécuriser l'accès au chat de la résidence et doter le Conseil Syndical d'une boîte à outils de gestion opérationnelle.**

</div>

---

## 🌟 Fonctionnalités Clés

### 1. 🛡️ Inscription (Onboarding) & Accès Sécurisé
- **Vérification préalable obligatoire** : Chaque résident démarre le bot en privé (`/start`) et remplit sa fiche : *Nom, Prénom, Numéro de lot / Appartement, Bâtiment, Étage, Statut (Copropriétaire occupant / Locataire / Copropriétaire bailleur), Téléphone, Courriel*.
- **Validation interactive par le Conseil Syndical** : La fiche est automatiquement transmise dans le groupe privé du CS avec boutons interactifs `[✅ Valider]` / `[❌ Refuser]`.
- **Anti-fuite de lien** : Le bot gère les demandes d'adhésion natives (`ChatJoinRequest`) et n'approuve l'entrée dans le groupe de la copropriété que pour les résidents validés.
- **Gestion des départs / Déménagements** : Commande `/demenager` pour libérer l'appartement dans la base de données et révoquer automatiquement l'accès au chat de la copro (avec checklist de départ : badges, pré-état daté, compteurs d'eau).

### 2. 🔧 Gestion des Pannes & Tickets par Lot
- **Signalement guidé rattaché à l'appartement** : Choix de catégorie (*Ascenseur, Plomberie, Électricité, Parking, Accès Vigik*), description et photo optionnelle.
- **Pré-filtrage par l'IA** : Détecte si le problème est déjà connu (ex: technicien déjà prévu) ou s'il s'agit d'une question résolue par le règlement avant d'ouvrir un ticket doublon.
- **Tableau de bord interactif pour le CS** : Fiche ticket transmise dans le groupe CS avec boutons de suivi d'avancement (`[📞 Transmis Syndic]`, `[🔧 En cours]`, `[✅ Résolu]`). Chaque mise à jour notifie en direct le résident déclarant.
- **Relances automatiques du syndic (via n8n)** : Détection des tickets sans retour après 7 jours pour déclencher un e-mail de relance pré-rédigé.

### 3. 🚨 Urgences 24/7 & Sécurité
- **Bouton « Urgence Résidence 24/7 »** : Accès direct en 1 clic aux numéros d'astreinte sous contrat (*Ascensoriste, Chauffagiste, Plomberie d'urgence*).
- **Consignes vitales immédiates** : Emplacement exact des vannes d'arrêt générales d'eau, du coffret gaz et du local électrique TGBT.
- **Alerte prioritaire CS** : Possibilité d'alerter instantanément le groupe du Conseil Syndical en cas de sinistre grave.

### 4. 📢 Communication & Outils Conseil Syndical
- **Diffusion d'annonces officielles** : Rédaction assistée avec niveau d'urgence (*Info, Important, Urgent*), prévisualisation, publication soignée dans le chat de la copropriété et épinglage automatique.
- **Recherche d'occupants** : Commande `/lot <numéro>` pour connaître instantanément les occupants, coordonnées et statut d'un appartement.
- **Sondages officiels certifiés** : Consultation garantissant strictement **1 vote par appartement** (évite les votes multiples entre conjoints ou colocataires) avec suivi de participation pour le CS.
- **Carnet de passage des prestataires** : Commande `/prestataire <Nom> - <Raison>` pour tracer les interventions techniques dans l'immeuble.

### 5. 🤖 Moteur Multi-LLM & Intelligence Artificielle
- **Google Gemini (2.5 Flash)** : Capacité d'ingérer l'intégralité d'épais règlements de copropriété en PDF sans découpage complexe.
- **Mistral AI** : Pour les analyses de textes juridiques, la rédaction et la synergie avec `CPTCOPRO`.
- **RAG documentaire** : Réponses immédiates et sourcées aux résidents sur les horaires de bruit, règles de climatisation, locaux communs, encombrants, etc.

### 6. 💶 Synergies CPTCOPRO & n8n
- **Passerelle CPTCOPRO** : Connexion directe à la base de données de `CPTCOPRO` pour consulter les soldes comptables de charges par lot et la balance des impayés pour le CS.
- **Intégration n8n** : Client et serveur de webhooks pour déclencher des actions externes (*Trello, Jira, relances e-mails, alertes de fuites d'eau anormales*).

### 7. 🤝 Entraide & Démocratie Participative
- **Voisins Solidaires** : Petites annonces de dons et de prêts de matériel (*perceuse, escabeau, diable pour déménagement, cartons*).
- **Boîte à idées AG & Bourse aux pouvoirs** : Soumission de propositions de résolutions tout au long de l'année et facilitation de la délégation de pouvoirs pour atteindre le quorum en AG.

---

## 🏗️ Architecture Technique

```
CSBOT/
├── config/                  # Configuration centralisée via Pydantic Settings
│   └── settings.py
├── database/                # ORM SQLAlchemy 2.0 asynchrone (MariaDB / MySQL)
│   ├── models.py            # User, Apartment, Occupant, Ticket, Poll, etc.
│   └── session.py           # Moteur asynchrone et gestion des sessions
├── middlewares/             # Middlewares aiogram (Session BDD, Détection rôles)
│   ├── db_middleware.py
│   └── role_middleware.py
├── keyboards/               # Ergonomie 100% menus (Reply & Inline Keyboards)
│   ├── menu_kb.py
│   ├── onboarding_kb.py
│   ├── incident_kb.py
│   ├── cs_kb.py
│   └── emergency_kb.py
├── services/                # Logique métier et passerelles
│   ├── llm/                 # Multi-LLM (Gemini 2.5 Flash, Mistral AI, Manager RAG)
│   ├── user_service.py      # Onboarding, validation, départs
│   ├── ticket_service.py    # Cycle de vie des tickets et sync n8n
│   ├── emergency_service.py # Astreintes et consignes 24/7
│   ├── cptcopro_service.py  # Pont financier avec CPTCOPRO
│   ├── n8n_service.py       # Webhooks et recherche documentaire étendue
│   └── poll_service.py      # Sondages certifiés (1 vote par lot)
├── routers/                 # Routeurs aiogram v3 par domaine fonctionnel
│   ├── common.py            # Accueil, aide et navigation menus
│   ├── onboarding.py        # Machine à états FSM pour l'inscription
│   ├── incidents.py         # Signalement des pannes avec photo et suivi
│   ├── assistant.py         # Questions libres aux documents via IA
│   ├── emergency.py         # Page des urgences et astreintes
│   ├── cs_announcements.py  # Annonces officielles dans le chat copro
│   ├── cs_tools.py          # Validations, /lot, carnet prestataires
│   ├── finances.py          # Consultation financière (CPTCOPRO)
│   ├── polls.py             # Sondages officiels
│   ├── ag_router.py         # Boîte à idées et pouvoirs d'AG
│   ├── solidarity.py        # Voisins solidaires (dons / prêts)
│   └── join_requests.py     # Sécurisation des adhésions au groupe Telegram
├── api/                     # Serveur HTTP aiohttp pour alertes n8n / CPTCOPRO
│   └── webhook_server.py
├── scheduler/               # Planificateur de tâches APScheduler
│   └── tasks.py
├── data/documents/          # Dossier de dépôt des PDF (règlement, PV d'AG)
├── main.py                  # Point d'entrée principal (Long-Polling aiogram)
├── pyproject.toml           # Gestion des dépendances Poetry
└── docker-compose.yml       # Stack conteneurisée avec MariaDB
```

---

## 🚀 Démarrage Rapide

### 1. Prérequis
- Python 3.11, 3.12 ou 3.14
- [Poetry](https://python-poetry.org/) installé
- Un token de bot Telegram (obtenu auprès de [@BotFather](https://t.me/BotFather))
- Un serveur MariaDB ou MySQL (local ou via Docker)

### 2. Installation des Dépendances
```bash
poetry install
```

### 3. Configuration de l'Environnement
Copiez le fichier d'exemple et renseignez vos informations :
```bash
cp .env.example .env
```

Variables indispensables :
```ini
BOT_TOKEN="votre_token_telegram_bot_ici"
COPRO_CHAT_ID=-100xxxxxxxxxx     # ID du groupe public de la copro
CS_GROUP_ID=-100yyyyyyyyyy        # ID du groupe privé du Conseil Syndical
ADMIN_IDS=[votre_id_telegram]             # Votre ID Telegram pour les droits Super-Admin

# Base de données MariaDB
DB_USER="csbot_user"
DB_PASSWORD="csbot_password"
DB_HOST="localhost"
DB_NAME="csbot"

# Clés IA (au choix ou les deux)
GEMINI_API_KEY="AIzaSy..."
MISTRAL_API_KEY="..."
```

### 4. Dépôt des Documents de Copropriété
Déposez simplement vos fichiers PDF (ex: `reglement_copro.pdf`, `pv_ag_2025.pdf`) ou textes dans le dossier `data/documents/`. Le bot les indexera automatiquement pour répondre aux questions des résidents.

### 5. Lancement du Bot
```bash
poetry run python main.py
```

---

## 🐳 Déploiement avec Docker Compose

Pour déployer le bot en conteneur avec sa propre base MariaDB 11 :

```bash
docker compose up -d --build
```

Pour consulter les logs en temps réel :
```bash
docker compose logs -f csbot
```

---

## 🧪 Exécution des Tests

Les tests unitaires utilisent une base de données SQLite en mémoire ultra-rapide :

```bash
poetry run pytest
```
