"""Service de gestion des urgences de la copropriété et des astreintes 24/7."""

from config.settings import settings


class EmergencyService:
    @staticmethod
    def get_emergency_overview() -> str:
        """Texte récapitulatif des numéros d'urgence et consignes vitales."""
        return (
            "🚨 <b>NUMÉROS D'URGENCE & ASTREINTES 24/7</b> 🚨\n\n"
            f"🛗 <b>Ascensoriste (Dépannage / Personne bloquée) :</b>\n"
            f"📞 <code>{settings.EMERGENCY_ASCENSEUR_PHONE}</code>\n\n"
            f"🔥 <b>Chauffagiste (Panne générale de chauffage / eau chaude) :</b>\n"
            f"📞 <code>{settings.EMERGENCY_CHAUFFAGE_PHONE}</code>\n\n"
            f"💧 <b>Plomberie d'Urgence (Inondation parties communes) :</b>\n"
            f"📞 <code>{settings.EMERGENCY_PLOMBERIE_PHONE}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚰 <b>COUPURES GÉNÉRALES & VANNES D'ARRÊT :</b>\n"
            f"💧 <b>Vanne d'arrêt générale d'eau :</b>\n{settings.WATER_VALVE_LOCATION}\n\n"
            f"⚡ <b>Local TGBT (Électricité générale) :</b>\n{settings.ELECTRIC_ROOM_LOCATION}\n\n"
            f"🔥 <b>Vanne coupure générale Gaz :</b>\n{settings.GAS_VALVE_LOCATION}\n\n"
            "<i>⚠️ N'appelez les astreintes de nuit ou de week-end qu'en cas d'urgence réelle mettant en danger les personnes ou les biens.</i>"
        )

