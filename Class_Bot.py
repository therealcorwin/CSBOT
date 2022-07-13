from dataclasses import dataclass

@dataclass
class message_utilisateur_private:
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
            print("message_utilisateur_private message_text : ", self.message_text)
            print("message_utilisateur_private message_type : ", self.message_type)
            print("message_utilisateur_private message_id : ", self.message_id)
            print("message_utilisateur_private message_date : ", self.message_date)
            print("message_utilisateur_private message_author_id : ", self.message_author_id)
            print("message_utilisateur_private message_author_signature : ", self.message_author_first_name)
            print("message_utilisateur_private message_author_last_name : ", self.message_author_last_name)
            print("message_utilisateur_private message_full_authorname : ", self.message_full_authorname)
        """
        

@dataclass
class message_utilisateur_channel:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_from_chat: str
    message_from_chat_id: int
    message_full_authorname: str = "None"
    
    """
    def __post_init__(self):
        print("message_utilisateur_channel message_text :", self.message_text)
        print("message_utilisateur_channel message_type : ", self.message_type)
        print("message_utilisateur_channel message_id : ", self.message_id)
        print("message_utilisateur_channel message_date : ", self.message_date)
        print("message_utilisateur_channel message_from_chat : ", self.message_from_chat)
        print("message_utilisateur_channel message_from_chat_id : ", self.message_from_chat_id)
        print("message_utilisateur_channel message_full_authorname : ", self.message_full_authorname)
    """
    