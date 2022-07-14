from dataclasses import dataclass

@dataclass
class MessageUtilisateurPrivate:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_author_id: int
    message_telegram_user_name: str = "None"
    message_author_first_name: str = "None"
    message_author_last_name: str = "None"
    message_full_authorname: str = "None"
 
    def __post_init__(self):
        self.message_full_authorname = f"{self.message_author_first_name} {self.message_author_last_name}"
        """
            print("MessageUtilisateurPrivate message_text : ", self.message_text)
            print("MessageUtilisateurPrivate message_type : ", self.message_type)
            print("MessageUtilisateurPrivate message_id : ", self.message_id)
            print("MessageUtilisateurPrivate message_date : ", self.message_date)
            print("MessageUtilisateurPrivate message_author_id : ", self.message_author_id)
            print("MessageUtilisateurPrivate message_author_signature : ", self.message_author_first_name)
            print("MessageUtilisateurPrivate message_author_last_name : ", self.message_author_last_name)
            print("MessageUtilisateurPrivate message_full_authorname : ", self.message_full_authorname)
        """
        

@dataclass
class MessageUtilisateurChannel:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_from_chat: str
    message_from_chat_id: int
    message_full_authorname: str = "None"

    def __post_init__(self):    
        print("MessageUtilisateurChannel message_id : ", self.message_id)

    """
        print("MessageUtilisateurChannel message_text :", self.message_text)
        print("MessageUtilisateurChannel message_type : ", self.message_type)
        print("MessageUtilisateurChannel message_id : ", self.message_id)
        print("MessageUtilisateurChannel message_date : ", self.message_date)
        print("MessageUtilisateurChannel message_from_chat : ", self.message_from_chat)
        print("MessageUtilisateurChannel message_from_chat_id : ", self.message_from_chat_id)
        print("MessageUtilisateurChannel message_full_authorname : ", self.message_full_authorname)
    """
    