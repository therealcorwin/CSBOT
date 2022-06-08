from dataclasses import dataclass

@dataclass
class Message_Utilisateur_Private:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_author_id: int
    message_author_first_name: str = None
    message_author_last_name: str = None
    message_full_authorname: str = None
 
    def __post_init__(self):
        self.message_full_authorname = f"{self.message_author_first_name} {self.message_author_last_name}"
        #print("Message_Utilisateur_Private message_text : ", self.message_text)
        #print("Message_Utilisateur_Private message_type : ", self.message_type)
        #print("Message_Utilisateur_Private message_id : ", self.message_id)
        #print("Message_Utilisateur_Private message_date : ", self.message_date)
        #print("Message_Utilisateur_Private message_author_id : ", self.message_author_id)
        #print("Message_Utilisateur_Private message_author_signature : ", self.message_author_first_name)
        #print("Message_Utilisateur_Private message_author_last_name : ", self.message_author_last_name)
        #print("Message_Utilisateur_Private message_full_authorname : ", self.message_full_authorname)

@dataclass
class Message_Utilisateur_Channel:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_from_chat: str
    message_from_chat_id: int
    message_full_authorname: str = None
 
    #def __post_init__(self):
        #print("Message_Utilisateur_Channel message_text :", self.message_text)
        #print("Message_Utilisateur_Channel message_type : ", self.message_type)
        #print("Message_Utilisateur_Channel message_id : ", self.message_id)
        #print("Message_Utilisateur_Channel message_date : ", self.message_date)
        #print("Message_Utilisateur_Channel message_from_chat : ", self.message_from_chat)
        #print("Message_Utilisateur_Channel message_from_chat_id : ", self.message_from_chat_id)
        #print("Message_Utilisateur_Channel message_full_authorname : ", self.message_full_authorname)