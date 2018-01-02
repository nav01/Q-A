from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import sessionmaker
import enum


engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()

class Employee(Base):
    _Q = enum.Enum('Q', 'engineer manager')
    __tablename__ = 'employee'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    type = Column(Enum(_Q))

    __mapper_args__ = {
        'polymorphic_identity':'employee',
        'polymorphic_on':type,
    }

class Engineer(Employee):
    __tablename__ = 'engineer'
    id = Column(Integer, ForeignKey('employee.id'), primary_key=True)
    engineer_name = Column(String(30))

    __mapper_args__ = {
        'polymorphic_identity':Employee._Q.engineer,
    }

class Manager(Employee):
    __tablename__ = 'manager'
    id = Column(Integer, ForeignKey('employee.id'), primary_key=True)
    manager_name = Column(String(30))

    __mapper_args__ = {
        'polymorphic_identity':Employee._Q.manager,
    }

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

d = {
    'name':'bob',
    'type':getattr(Employee._Q,'engineer'),
    'engineer_name':'bob the builder',
}

e = Engineer(**d)
session.add(e)
session.commit()
e_employee = session.query(Employee).one()
print(e_employee.__class__)
print(e.id)
print(Engineer.type.name)
