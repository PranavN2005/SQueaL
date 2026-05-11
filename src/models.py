from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    tables = relationship("Table", back_populates="assigned_waiter")


class Table(Base):
    __tablename__ = "tables"

    table_id = Column(Integer, primary_key=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="open")
    assigned_waiter_id = Column(
        Integer, ForeignKey("employees.employee_id"), nullable=True
    )
    current_party_size = Column(Integer, nullable=True)
    reserved_for = Column(String, nullable=True)

    assigned_waiter = relationship("Employee", back_populates="tables")
    parties = relationship("Party", back_populates="table")
    reservations = relationship("Reservation", back_populates="table")
    tabs = relationship("Tab", back_populates="table")


class Party(Base):
    __tablename__ = "parties"

    party_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    party_size = Column(Integer, nullable=False)
    table_id = Column(Integer, ForeignKey("tables.table_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    table = relationship("Table", back_populates="parties")
    tabs = relationship("Tab", back_populates="party")


class FoodItem(Base):
    __tablename__ = "food_items"

    food_item_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)


class Tab(Base):
    __tablename__ = "tabs"

    tab_id = Column(Integer, primary_key=True)
    party_id = Column(Integer, ForeignKey("parties.party_id"), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.table_id"), nullable=True)
    total_price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    party = relationship("Party", back_populates="tabs")
    table = relationship("Table", back_populates="tabs")
    items = relationship("TabItem", back_populates="tab")


class TabItem(Base):
    __tablename__ = "tab_items"

    tab_item_id = Column(Integer, primary_key=True)
    tab_id = Column(Integer, ForeignKey("tabs.tab_id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    tab = relationship("Tab", back_populates="items")


class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id = Column(Integer, primary_key=True)
    customer_name = Column(String, nullable=False)
    party_size = Column(Integer, nullable=False)
    table_id = Column(Integer, ForeignKey("tables.table_id"), nullable=False)
    reservation_time = Column(String, nullable=False)
    status = Column(String, nullable=False, default="reserved")
    created_at = Column(DateTime, default=datetime.utcnow)

    table = relationship("Table", back_populates="reservations")
