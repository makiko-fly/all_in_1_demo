from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# class InvestmentStyle(Base):
#     __tablename__ = 'investment_styles'
#
#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     style = Column(String(100), nullable=False)
#     user = relationship("User", back_populates="investment_styles")
#
#     def __repr__(self):
#         return f'<InvestmentStyle {self.style} for User {self.user_id}>'