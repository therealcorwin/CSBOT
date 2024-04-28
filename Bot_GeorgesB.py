import configparser
import html
import json
import traceback
from datetime import datetime, timedelta
from logging import getLogger
from logging.config import fileConfig
from os import path

import mysql.connector as mariadb
from telegram import (Bot, ChatJoinRequest, ChatInviteLink, InlineKeyboardButton,
                      InlineKeyboardMarkup, ParseMode, PhotoSize, Update)
from telegram.ext import (CallbackContext, CallbackQueryHandler, ChatJoinRequestHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from Class_Bot import MessageUtilisateurChannel as MUC
from Class_Bot import MessageUtilisateurPrivate as MUP

""" 

   INITIALISATION LOGGING

"""
# Enable logging
if path.exists("Logging.conf"):
    fileConfig("Logging.conf", encoding="utf_8")
    botlog = getLogger("BOTLOG")
    dbchecklog = getLogger("DBCHECK")
    dbdatalog = getLogger("DBDATA")
    botlog.info("Lecture du fichier de configuration de la journalisation")
else:
    exit("Le fichier Logging.conf n'existe pas")

"""

    LECTURE FICHIER DE CONFIGURATION DU BOT

"""
if path.exists("config.ini"):
    botlog.info("Lecture du fichier de configuration")
    config_bot = configparser.ConfigParser()
    config_bot.read_file(open("config.ini", "r"))
else: 
   botlog.critical("Le fichier config.ini n'existe pas")
   exit("Le fichier config.ini n'existe pas")

""" 

    INITIALISATION VARIABLES

"""
ETAGE, APPT, COURRIEL, NOM, INVITATION, DATA_END, END_CONV = range(7)
DICO_COPRO = {"COPRO_NOM": "None", "COPRO_COURRIEL": "None", "COPRO_APPT": "None", "COPRO_ETAGE": "None"}
TOKEN_BOT_TELEGRAM = config_bot["TELEGRAM"]["TOKEN_BOT"]
CHATID_COPRO = config_bot["CHAT_COPRO_INFO"]["CHAT_COPRO_ID"]
updater = Updater(TOKEN_BOT_TELEGRAM)
dispatcher = updater.dispatcher

"""
    
    CONNEXION A LA BDD

"""
def connexion_to_database() -> mariadb.Connection:
    try:
        mariadb_cnx = mariadb.connect(
            user=config_bot["DATABASE"]["USER"],
            password=config_bot["DATABASE"]["PASSWORD"],
            host=config_bot["DATABASE"]["HOST"],
            port=config_bot["DATABASE"]["PORT"],
            database=config_bot["DATABASE"]["DATABASE"],
            autocommit=True
        )
        dbdatalog.info("Connexion à la base de données réussie")
        return mariadb_cnx
    except Exception as e:
        dbdatalog.critical("Impossible de se connecter à la base de données")
        dbdatalog.critical(e)
        return False

def check_database_connnexion(mariadb_cnx: mariadb.Connection) -> bool:
    if mariadb_cnx.is_connected():
        dbchecklog.info("Check database : ONLINE")
        return True
    else:
        dbchecklog.critical("Check database : OFFLINE")
        return False

MARIADB_CNX = connexion_to_database()

def get_mariadb_cursor() -> mariadb.Cursor:
    if MARIADB_CNX and not MARIADB_CNX.is_closed():
        cursor = MARIADB_CNX.cursor()
        return cursor
    else:
        dbdatalog.critical("Impossible de récupérer un curseur de base de données, la connexion est fermée")
        return False

def push_data_stats(mariadb_cnx: mariadb.Connection, mariadb_cursor: mariadb.Cursor, user_id: int,
                    telegram_user_name: str, user_firstname: str, user_lastname: str,
                    user_fullname: str, type_message: str, user_last_message_time: datetime) -> None:
    if check_database_connnexion(mariadb_cnx) == False:
        dbdatalog.info("Tentative de reconnection à la base de données")
        connexion_to_database()
    else:
        DATA_STATS = 'INSERT INTO STATS (USER_ID, TELEGRAM_USER_NAME, USER_FIRSTNAME, USER_LASTNAME, USER_FULLNAME, TYPE_MESSAGE, USER_LAST_MESSAGE_TIME) VALUES (%s,%s,%s,%s,%s,%s,%s)'
        DATA_STATS_DATA = (user_id, telegram_user_name, user_firstname, user_lastname, user_fullname, type_message, user_last_message_time)
        try:
            mariadb_cursor.execute(DATA_STATS, DATA_STATS_DATA)
            dbdatalog.info("Insertion Statistics en BDD : OK")
        except Exception as e:
            dbdatalog.critical("Impossible d'inserer les données en base, vérifier la connexion au serveur de base de données")
            dbdatalog.critical(e)

def push_data_copro(mariadb_cnx: mariadb.Connection, mariadb_cursor: mariadb.Cursor, user_id: int,
                    telegram_user_name: str, copro_name: str, copro_etage: str, copro_appt: str,
                    copro_courriel: str, copro_telephone: str) -> None:
    if check_database_connnexion(mariadb_cnx) == False:
        dbchecklog.info("Tentative de reconnection à la base de données")
        connexion_to_database()
    else:
        DATA_COPRO = 'INSERT IGNORE INTO COPRO (USER_ID, TELEGRAM_USER_NAME, NOM, ETAGE, APPT, COURRIEL, TELEPHONE) VALUES (%s,%s,%s,%s,%s,%s,%s)'
        DATA_COPRO_DATA = (user_id, telegram_user_name, copro_name, copro_etage, copro_appt, copro_courriel, copro_telephone)
        try:
            mariadb_cursor.execute(DATA_COPRO, DATA_COPRO_DATA)
            dbdatalog.info("Insertion Copro en BDD : OK")
        except Exception as e:
            dbdatalog.critical("Impossible d'inserer les données en base, vérifier la connexion au serveur de base de données")
            dbdatalog.critical(e)

"""

    CODE BOT

"""
botcopro = Bot(TOKEN_BOT_TELEGRAM)
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text("Plop Ici Georges ")

def help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("""
    
    /start
    /help
    /contact
    /contenu

    """)

def contact(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /contact is issued."""
    update.message.reply_text("Contact ")

def contenu(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /contenu is issued."""
    update.message.reply_text("contenu ")

def recup_message_user(update: Update, context: CallbackContext) -> None:
    """Store user's message in the database."""
    print(update)
    if update.effective_message.chat.type == "private":
        botlog.info("Creation d'un objet MUP")
        plop = MUP(
            message_text=update.effective_message.text,
            message_type=update.effective_message.chat.type,
            message_id=update.effective_message.message_id,
            message_telegram_user_name=update.effective_message.chat.username,
            message_date=update.effective_message.date,
            message_author_id=update.effective_message.chat.id,
            message_author_first_name=update.effective_message.chat.first_name,
            message_author_last_name=update.effective_message.chat.last_name
        )
        push_data_stats(MARIADB_CNX, get_mariadb_cursor(), plop.message_author_id,
                        plop.message_telegram_user_name, plop.message_author_first_name,
                        plop.message_author_last_name, plop.message_full_authorname,
                        update.effective_message.chat.type, plop.message_date)
    elif update.effective_message.chat.type == "channel":
        botlog.info("Creation d'un objet MUC")
        plip = MUC(
            message_text=update.effective_message.text,
            message_type=update.effective_message.chat.type,
            message_id=update.effective_message.message_id,
            message_date=update.effective_message.date,
            message_from_chat=update.effective_message.chat.title,
            message_from_chat_id=update.effective_message.chat.id,
            message_full_authorname=update.effective_message.author_signature
        )
        push_data_stats(MARIADB_CNX, get_mariadb_cursor(), plip.message_full_authorname,
                        "", "", "", plip.message_full_authorname,
                        update.effective_message.chat.type, plip.message_date)
    else:
        botlog.info("Aucune creation d'objet")

def hello_copro(update: Update, context: CallbackContext) -> int:
    """Start the copro inscription conversation."""
    botlog.info(f"Initialisation inscription chat copro pour le user : {update.effective_user.id}")
    botcopro.get_user_profile_photos(config_bot["BOT_INFO"]["BOT_ID"])
    taille = PhotoSize(config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID"],
                       config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID_UNIQUE"],
                       "50", "50")
    botcopro.send_photo(chat_id=update.effective_message.chat.id, photo=taille,
                        caption="Bonjour, je suis Georges Bot, l'assitant virtuel de la copro.\n\nAfin de mieux répondre à vos demandes, je vais vous demander quelques informations.\n\nVous étes libre de ne pas répondre.\n\n")
    keyboard = [
        [
            InlineKeyboardButton("Etage 1", callback_data='1'),
            InlineKeyboardButton("Etage 2", callback_data='2'),
            InlineKeyboardButton("Etage 3", callback_data='3'),
            InlineKeyboardButton("Etage 4", callback_data='4')

        ],
        [
            InlineKeyboardButton("Ne pas répondre", callback_data='NSP'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('A quel étage habitez vous ? :', reply_markup=reply_markup)
    return ETAGE

def creer_don_copro(update: Update, context: CallbackContext) -> None:
    """Create a new don for the copro."""
    update.message.reply_text("Creer don copro ")

def liste_don_copro(update: Update, context: CallbackContext) -> None:
    """List all dons for the copro."""
    update.message.reply_text("Liste don copro ")

def get_copro_etage(update: Update, context: CallbackContext) -> int:
    """Get the user's selected etage."""
    query = update.callback_query
    query.answer()
    botlog.info(f"le user : {update.effective_user.id} à choisit Etage : {query.data}")
    DICO_COPRO["COPRO_ETAGE"] = query.data
    print(DICO_COPRO["COPRO_ETAGE"])
    query.edit_message_text(text="Quel est le numéro de votre appartement ?\n Pour passer, tapez /suivant")

    return APPT

def get_copro_appt(update: Update, context: CallbackContext) -> int:
    """Get the user's selected appartement."""
    DICO_COPRO["COPRO_APPT"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} a saisi Appartement : {update.message.text}")
    print(DICO_COPRO["COPRO_APPT"])
    update.message.reply_text("Quel est votre courriel ? :\n Pour passer, tapez /suivant")
    return COURRIEL

def next_get_copro_appt(update: Update, context: CallbackContext) -> int:
    """Skip the appartement question."""
    DICO_COPRO["COPRO_APPT"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} a saisi Appartement : NSP")
    print(DICO_COPRO["COPRO_APPT"])
    update.message.reply_text("Quel est votre courriel ? :\n Pour passer, tapez /suivant")
    return COURRIEL

def get_copro_courriel(update: Update, context: CallbackContext) -> int:
    """Get the user's email address."""
    DICO_COPRO["COPRO_COURRIEL"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} a saisi Courriel : {update.message.text}")
    print(DICO_COPRO["COPRO_COURRIEL"])
    update.message.reply_text("Quel est votre nom ? :\n Pour passer, tapez /suivant")
    return NOM

def next_get_copro_courriel(update: Update, context: CallbackContext) -> int:
    """Skip the email question."""
    DICO_COPRO["COPRO_COURRIEL"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} a saisi Courriel : NSP")
    print(DICO_COPRO["COPRO_COURRIEL"])
    update.message.reply_text("Quel est votre nom ? :\n Pour passer, tapez /suivant")
    return NOM

def get_copro_nom(update: Update, context: CallbackContext) -> int:
    """Get the user's name."""
    DICO_COPRO["COPRO_NOM"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} a saisi Nom : {update.message.text}")
    print(DICO_COPRO["COPRO_NOM"])
    update.message.reply_text("/creer  :)")
    return INVITATION

def next_get_copro_nom(update: Update, context: CallbackContext) -> int:
    """Skip the name question."""
    DICO_COPRO["COPRO_NOM"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} a saisi Nom : NSP")
    print(DICO_COPRO["COPRO_NOM"])
    update.message.reply_text("/creer  :)")
    return INVITATION

def get_copro_end_conv(update: Update, context: CallbackContext) -> None:
    """End the copro inscription conversation."""
    update.message.reply_text("Quel est votre courriel :\n Pour passer, tapez /suivant")
    return END_CONV

def invitation_copro_to_chat(update: Update, context: CallbackContext) -> None:
    """Invite the user to the copro chat."""
    print("plop")
    copro_bio = "bla bla bla"
    try:
        USER_ID = 1
        invite_link = botcopro.export_chat_invite_link(CHATID_COPRO)
        botcopro.send_message(chat_id=CHATID_COPRO, text=f"@{update.effective_user.username}, bienvenue dans le chat de la copro !\n\n{copro_bio}")
        push_data_copro(MARIADB_CNX, get_mariadb_cursor(), update.effective_message.chat.id,
                        update.effective_message.chat.first_name, DICO_COPRO["COPRO_NOM"],
                        DICO_COPRO["COPRO_ETAGE"], DICO_COPRO["COPRO_APPT"],
                        DICO_COPRO["COPRO_COURRIEL"], DICO_COPRO["COPRO_TEL"])
    except Exception as e:
        print(e)

def accept_invitation_copro(update: Update) -> None:
    """Accept the invitation to the copro chat."""
    print("accepte")
    update.approve()
    botcopro.approve_chat_join_request(CHATID_COPRO, user_id=update.effective_user.id)
    update.message.reply_text("Vous avez accepté l'invitation")

def don_copro(update: Update, context: CallbackContext) -> int:
    """Start the don copro conversation."""
    botlog.info(f"Initialisation du don pour la copro : {update.effective_user.id}")
    botcopro.get_user_profile_photos(config_bot["BOT_INFO"]["BOT_ID"])
    taille = PhotoSize(config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID"],
                       config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID_UNIQUE"],
                       "50", "50")
    botcopro.send_photo(chat_id=update.effective_message.chat.id, photo=taille,
                        caption="Bonjour, je suis Georges Bot, l'assitant virtuel de la copro.\n\nAfin de mieux répondre à vos demandes, je vais vous demander quelques informations.\n\nVous étes libre de ne pas répondre.\n\n")
    keyboard = [
        [
            InlineKeyboardButton("Faire Don", callback_data='1'),
            InlineKeyboardButton("Lister Don", callback_data='2'),
            InlineKeyboardButton("Supprimer Don", callback_data='3'),
            InlineKeyboardButton("Etage 4", callback_data='4')

        ],
        [
            InlineKeyboardButton("Annuler", callback_data='NSP'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Voullez vous faire un don à la copro ? :", reply_markup=reply_markup)
    return ETAGE

def faire_don_copro(update: Update, context: CallbackContext) -> int:
    """Handle the user's request to make a donation."""
    print("toto")
    return END_CONV

def liste_don_copro(update: Update, context: CallbackContext) -> int:
    """Handle the user's request to list donations."""
    print("toto")
    return END_CONV

def suppr_don_copro(update: Update, context: CallbackContext) -> int:
    """Handle the user's request to delete a donation."""
    print("toto")
    return END_CONV

def main() -> None:
    """Start the bot."""
    conv_inscription_handler = ConversationHandler(
        entry_points=[CommandHandler("copro", hello_copro)],
        states={
            ETAGE: [CallbackQueryHandler(get_copro_etage)],
            APPT: [
                MessageHandler(Filters.text & ~Filters.command, get_copro_appt),
                CommandHandler('suivant', next_get_copro_appt)
            ],
            COURRIEL: [
                MessageHandler(Filters.text & ~Filters.command, get_copro_courriel),
                CommandHandler('suivant', next_get_copro_courriel)
            ],
            NOM: [
                MessageHandler(Filters.text & ~Filters.command, get_copro_nom),
                CommandHandler('suivant', next_get_copro_nom)
            ],
            INVITATION: [
                CommandHandler('creer', invitation_copro_to_chat)
            ],
            END_CONV: [CommandHandler('Quitter', get_copro_end_conv)]
        },
        per_user=True
    )

    dispatcher.add_handler(conv_inscription_handler)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("contact", contact))
    dispatcher.add_handler(CommandHandler("contenu", contenu))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, recup_message_user))
    dispatcher.add_handler(ChatJoinRequestHandler(join))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
