from ..models.user.register_user import RegisterUser
from ..models.user.user import User
from ..utils.db import DB
from pymongo.database import Database
class UserRepository:

    def __init__(self):
        self.db_user: Database = DB().database()
        self.collection = self.db_user.users

    def get_user_by_id(self, id: str):
        return "user"
    
    def get_user_by_email(self, email: str):
        try:
            return self.collection.find_one({"email":email})
        except Exception as e:
            raise Exception("The following error occurred: ", e)
        finally:
            DB().get_client().close()
    
    def get_user_by_username(self, username: str):
        try:
            return self.collection.find_one({"username":username})
        except Exception as e:
            raise Exception("The following error occurred: ", e)
        finally:
            DB().get_client().close()

    def create_user(self, user_register: RegisterUser):
        try:
            return self.collection.insert_one(user_register.to_dict())
        except Exception as e:
            raise Exception("The following error occurred: ", e)
        finally:
            DB().get_client().close()
    