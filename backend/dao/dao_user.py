from sqlalchemy.orm import Session
from dao.models import User

class UserDAO:
    def __init__(self, Session):
        self.Session = Session

    def create_user(self, username, hashed_password):
        with self.Session() as session:
            new_user = User(username=username, password=hashed_password)
            session.add(new_user)
            session.commit()
            return new_user

    def get_user_by_username(self, username):
        with self.Session() as session:
            return session.query(User).filter(User.username == username).first()

    def get_all_users(self):
        with self.Session() as session:
            return session.query(User).all()

    # def add_investment_style(self, user_id, style):
    #     with self.Session() as session:
    #         new_style = InvestmentStyle(user_id=user_id, style=style)
    #         session.add(new_style)
    #         session.commit()
    #         return new_style
    #
    # def get_investment_styles(self, user_id):
    #     with self.Session() as session:
    #         return session.query(InvestmentStyle).filter(InvestmentStyle.user_id == user_id).all()