from dataclasses import dataclass

@dataclass
class MessageUtilisateurPrivate:
    message_text: str
    message_type: str
    message_id: int
    message_date: int
    message_author_id: int

    def __post_init__(self):
        self.message_full_authorname = f"{self.message_author_first_name} {self.message_author_last_name}"

    @property
    def message_author_first_name(self) -> str:
        return "None"

    @property
    def message_author_last_name(self) -> str:
        return "None"

    @property
    def message_telegram_user_name(self) -> str:
        return "None"

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

    def _from_private_(self, private: MessageUtilisateurPrivate) -> None:
        self.message_text = private.message_text
        self.message_type = private.message_type
        self.message_id = private.message_id
        self.message_date = private.message_date
        self.message_full_authorname = private.message_full_authorname
        self.message_from_chat = private.message_author_first_name
        self.message_from_chat_id = private.message_author_id


private = MessageUtilisateurPrivate(message_text="Hello, world!", message_type="text", message_id=1234, message_date=1643218832, message_author_id=5678)
channel = MessageUtilisateurChannel(message_text="", message_type="", message_id=0, message_date=0, message_from_chat="", message_from_chat_id=0)
channel._from_private_(private)
