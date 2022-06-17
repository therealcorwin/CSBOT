from datetime import datetime
from os import path
import mysql.connector as Mariadb
import logging
from logging.config import fileConfig
import configparser
from Class_Bot import Message_Utilisateur_Private as MUP, Message_Utilisateur_Channel as MUC
from telegram import ParseMode, Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot, PhotoSize, ChatJoinRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler
)
import traceback
import html
import json


""" 

    INITIALISATION VARIABLES

"""
ETAGE, APPT, COURRIEL, NOM, INVITATION, DATA_END, END_CONV = range(7)
DICO_COPRO = {"COPRO_NOM":None, "COPRO_COURRIEL":None, "COPRO_APPT":None, "COPRO_ETAGE":None}

""" 

   INITIALISATION LOGGING

"""
# Enable logging
if  path.exists("Logging.conf"):
    logging.config.fileConfig("Logging.conf",encoding="utf_8")
    botlog = logging.getLogger("BOTLOG")
    dbchecklog = logging.getLogger("DBCHECK")
    dbdatalog = logging.getLogger("DBDATA")
    botlog.info("Lecture du fichier de configuration de la journalisation")
else: 
   exit("Le fichier Logging.conf n'existe pas")

"""

    LECTURE FICHIER DE CONFIGURATION DU BOT

"""
if  path.exists("config.ini"):
    botlog.info("Lecture du fichier de configuration")
    config_bot = configparser.ConfigParser()
    config_bot.read("config.ini")
else: 
   botlog.error("Le fichier config.ini n'existe pas")
   exit("Le fichier config.ini n'existe pas")

"""
    
    CONNEXION A LA BDD

"""
def connexion_to_database() -> Mariadb:
    try:
        MARIADB_CNX = Mariadb.connect(
            user=config_bot["DATABASE"]["USER"],
            password=config_bot["DATABASE"]["PASSWORD"],
            host=config_bot["DATABASE"]["HOST"],
            port=config_bot["DATABASE"]["PORT"],
            database=config_bot["DATABASE"]["DATABASE"],
            autocommit=True
            )
        dbdatalog.info("Connexion à la base de données réussie")
        return MARIADB_CNX
    except:
        dbdatalog.critical("Impossible de se connecter à la base de données")
        return False

def check_database_connnexion (MARIADB_CNX):
    if (MARIADB_CNX.is_connected()) :
        dbchecklog.info("Check database connexion : ONLINE")
        return True
    else:
        dbchecklog.critical("Check database connexion : OFFLINE")
        return False
    

def push_data_stats(MARIADB_CNX,MARIADB_CURSOR, USER_ID,TELEGRAM_USER_NAME, USER_FIRSTNAME, USER_LASTNAME, USER_FULLNAME, TYPE_MESSAGE, USER_LAST_MESSAGE_TIME) :
    if check_database_connnexion(MARIADB_CNX) == False:
       connexion_to_database()
    else:
        DATA_STATS = 'INSERT INTO STATS (USER_ID, TELEGRAM_USER_NAME, USER_FIRSTNAME, USER_LASTNAME, USER_FULLNAME, TYPE_MESSAGE, USER_LAST_MESSAGE_TIME) VALUES (%s,%s,%s,%s,%s,%s,%s)'
        DATA_STATS_DATA = (USER_ID, TELEGRAM_USER_NAME, USER_FIRSTNAME, USER_LASTNAME, USER_FULLNAME,TYPE_MESSAGE, USER_LAST_MESSAGE_TIME )
        MARIADB_CURSOR.execute(DATA_STATS, DATA_STATS_DATA)
    
MARIADB_CNX = connexion_to_database()
MARIADB_CURSOR = MARIADB_CNX.cursor()

"""

    CODE BOT

"""
TOKEN_BOT_TELEGRAM = config_bot["TELEGRAM"]["TOKEN_BOT"]
CHATID_COPRO = config_bot["CHAT_COPRO_INFO"]["CHAT_COPRO_ID"]

botcopro = Bot(TOKEN_BOT_TELEGRAM)
def start(update, context):
    update.message.reply_text("Plop Ici Georges ")

def help(update, context):
    update.message.reply_text("""
    
    /start
    /help
    /contact
    /contenu

    """)

def contact(update, context):
    update.message.reply_text("Contact ")

def contenu(update, context):
    update.message.reply_text("contenu ")

def recup_message_user(update, context):
    print(update.effective_message)
    if update.effective_message.chat.type == "private":
        botlog.info("Creation d'un objet MUP")
        plop = MUP(  
                    message_text = update.effective_message.text , 
                    message_type = update.effective_message.chat.type ,
                    message_id = update.effective_message.message_id,
                    message_telegram_user_name = update.effective_message.chat.username, 
                    message_date = update.effective_message.date, 
                    message_author_id = update.effective_message.chat.id,
                    message_author_first_name = update.effective_message.chat.first_name, 
                    message_author_last_name = update.effective_message.chat.last_name
                )
        push_data_stats(MARIADB_CNX,MARIADB_CURSOR, plop.message_author_id,plop.message_telegram_user_name, plop.message_author_first_name, plop.message_author_last_name,plop.message_full_authorname,update.effective_message.chat.type,plop.message_date)       
    elif update.effective_message.chat.type == "channel":
        botlog.info("Creation d'un objet MUC") 
        plip = MUC(  
                    message_text = update.effective_message.text , 
                    message_type = update.effective_message.chat.type ,
                    message_id = update.effective_message.message_id, 
                    message_date = update.effective_message.date, 
                    message_from_chat = update.effective_message.chat.title,
                    message_from_chat_id = update.effective_message.chat.id,
                    message_full_authorname = update.effective_message.author_signature 
                )
        push_data_stats(MARIADB_CNX,MARIADB_CURSOR, plip.message_full_authorname,"", "" , "" , plip.message_full_authorname,update.effective_message.chat.type,plip.message_date)    
    else:
        botlog.info("Aucune creation d'objet") 

def hello_copro(update,context) -> int :
    botlog.info(f"Initialisation inscription chat copro pour le user : {update.effective_user.id}")
    infobot = botcopro.get_user_profile_photos(config_bot["BOT_INFO"]["BOT_ID"])
    taille= PhotoSize(config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID"], config_bot["BOT_INFO"]["BOT_PHOTO_FILE_ID_UNIQUE"], "50", "50")
    botcopro.send_photo(chat_id=update.effective_message.chat.id, photo=taille, caption="Bonjour, je suis Georges Bot, l'assitant virtuel de la copro.\n\nAfin de mieux répondre à vos demandes, je vais vous demander quelques informations.\n\nVous étes libre de ne pas répondre.\n\n")
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


def get_copro_etage(update, context) -> int :
    # Get CallbackQuery from Update
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    botlog.info(f"le user : {update.effective_user.id} à choisit Etage : {query.data}")
    DICO_COPRO["COPRO_ETAGE"] = query.data
    print(DICO_COPRO["COPRO_ETAGE"])
    query.edit_message_text(text="Quel est le numéro de votre appartement ?\n Pour passer, tapez /suivant")
    
    return APPT

def get_copro_appt(update, context) -> int :
    DICO_COPRO["COPRO_APPT"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} à saisit Appartement : {update.message.text}")
    print(DICO_COPRO["COPRO_APPT"])
    update.message.reply_text("Quel est votre courriel ? :\n Pour passer, tapez /suivant")
    return COURRIEL

def next_get_copro_appt(update, context) -> int :
    DICO_COPRO["COPRO_APPT"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} à saisit Appartement : NSP")
    print(DICO_COPRO["COPRO_APPT"])
    update.message.reply_text("Quel est votre courriel ? :\n Pour passer, tapez /suivant")
    return COURRIEL

def get_copro_courriel(update, context) -> int :
    DICO_COPRO["COPRO_COURRIEL"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} à saisit Courriel : {update.message.text}")
    print(DICO_COPRO["COPRO_COURRIEL"])
    update.message.reply_text("Quel est votre nom ? :\n Pour passer, tapez /suivant")
    return NOM 

def next_get_copro_courriel(update, context) -> int :
    DICO_COPRO["COPRO_COURRIEL"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} à saisit Courriel : NSP")
    print(DICO_COPRO["COPRO_COURRIEL"])
    update.message.reply_text("Quel est votre nom ? :\n Pour passer, tapez /suivant")
    return NOM 

def get_copro_nom(update, context) -> int :
    DICO_COPRO["COPRO_NOM"] = update.message.text
    botlog.info(f"le user : {update.effective_user.id} à saisit Nom : {update.message.text}")
    print(DICO_COPRO["COPRO_NOM"])
    update.message.reply_text("/creer  :)")
    print(DICO_COPRO)
    return INVITATION

def next_get_copro_nom(update, context) -> int :
    DICO_COPRO["COPRO_NOM"] = "NSP"
    botlog.info(f"le user : {update.effective_user.id} à saisit Nom : NSP")
    print(DICO_COPRO["COPRO_NOM"])
    update.message.reply_text("/creer  :)")
    print(DICO_COPRO)
    return INVITATION 

def get_copro_end_conv (update, context):
    update.message.reply_text("Quel est votre courriel :\n Pour passer, tapez /suivant")
    return END_CONV

def invitation_copro_to_chat(update, context):
    print("plop")
    copro_bio = "bla bla bla"
    invit_link = ChatJoinRequest(chat=CHATID_COPRO, from_user=update.effective_message.chat.id, date=datetime.now(), bio=copro_bio, invite_link=config_bot["BOT_INFO"]["BOT_INVITATION_LINK"])
    #invit_link (chat=CHATID_COPRO, from_user=update.effective_message.chat.id, date=datetime, bio=copro_bio, invite_link=config_bot["BOT_INFO"]["BOT_INVITATION_LINK"])
    print(invit_link)
    return invit_link, ConversationHandler.END 


def error_handler(update: Update, context) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    botlog.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id="CHATID_COPRO", text=message, parse_mode=ParseMode.HTML)


updater = Updater(TOKEN_BOT_TELEGRAM)
disp = updater.dispatcher

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
        },
        fallbacks=[CommandHandler('Quitter', get_copro_end_conv)],
    )

    

disp.add_handler(conv_inscription_handler)
disp.add_handler(CommandHandler("start",start))
disp.add_handler(CommandHandler("help",help))
disp.add_handler(CommandHandler("contact",contact))
disp.add_handler(CommandHandler("contenu",contenu))
disp.add_handler(MessageHandler(Filters.text & ~Filters.command,recup_message_user))
disp.add_handler(ChatJoinRequestHandler(invitation_copro_to_chat))
disp.add_error_handler(error_handler)

updater.start_polling()
updater.idle()

