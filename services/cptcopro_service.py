"""Service de passerelle financière avec le projet CPTCOPRO."""


from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config.settings import settings


class CptCoproService:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        if settings.cptcopro_database_url:
            try:
                self._engine = create_async_engine(
                    settings.cptcopro_database_url,
                    pool_pre_ping=True,
                    echo=False
                )
            except Exception as e:
                logger.warning(f"Impossible de connecter la BDD CPTCOPRO : {e}")

    async def get_user_charges(self, lot_number: str) -> dict:
        """Récupère la situation comptable d'un lot depuis CPTCOPRO."""
        if not self._engine:
            return {
                "connected": False,
                "lot": lot_number,
                "balance": "N/D",
                "message": "Base de données CPTCOPRO non connectée. Renseignez CPTCOPRO_DB_NAME dans votre .env."
            }

        try:
            async with self._engine.connect() as conn:
                # Requête sur les tables de charges de CPTCOPRO
                query = text("""
                    SELECT SOLDE_ACTUEL, DATE_SITUATION, STATUT_COMPTE
                    FROM SITUATION_LOTS
                    WHERE NUM_LOT = :lot
                    LIMIT 1
                """)
                res = await conn.execute(query, {"lot": lot_number})
                row = res.fetchone()

                if row:
                    return {
                        "connected": True,
                        "lot": lot_number,
                        "balance": f"{row[0]:.2f} €",
                        "date": str(row[1]),
                        "status": str(row[2])
                    }
                else:
                    return {
                        "connected": True,
                        "lot": lot_number,
                        "balance": "0.00 €",
                        "message": "Aucune écriture comptable en attente pour ce lot."
                    }
        except Exception as e:
            logger.error(f"Erreur requête CPTCOPRO pour le lot {lot_number} : {e}")
            return {
                "connected": False,
                "lot": lot_number,
                "balance": "Erreur",
                "message": f"Erreur de lecture : {e!s}"
            }

    async def get_cs_financial_summary(self) -> dict:
        """Synthèse financière globale pour le Conseil Syndical."""
        if not self._engine:
            return {
                "connected": False,
                "total_unpaid": "Non connecté",
                "lots_in_debt": 0,
                "message": "Connectez la base CPTCOPRO pour voir la balance des impayés et la trésorerie."
            }

        try:
            async with self._engine.connect() as conn:
                query = text("""
                    SELECT
                        COALESCE(SUM(CASE WHEN SOLDE_ACTUEL < 0 THEN ABS(SOLDE_ACTUEL) ELSE 0 END), 0) AS TOTAL_IMPAYES,
                        COUNT(CASE WHEN SOLDE_ACTUEL < 0 THEN 1 END) AS LOTS_DEBITEURS,
                        COALESCE(SUM(SOLDE_ACTUEL), 0) AS TRESORERIE_GLOBALE
                    FROM SITUATION_LOTS
                """)
                res = await conn.execute(query)
                row = res.fetchone()

                return {
                    "connected": True,
                    "total_unpaid": f"{row[0]:.2f} €" if row else "0.00 €",
                    "lots_in_debt": row[1] if row else 0,
                    "treasury": f"{row[2]:.2f} €" if row else "0.00 €"
                }
        except Exception as e:
            logger.error(f"Erreur bilan financier CPTCOPRO : {e}")
            return {
                "connected": False,
                "total_unpaid": "Erreur SQL",
                "message": str(e)
            }


# Instance partagée
cptcopro_service = CptCoproService()
