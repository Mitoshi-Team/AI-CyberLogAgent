from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "Users"
    user_id = Column(Integer, primary_key=True)
    login = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)


class ActionType(Base):
    __tablename__ = "ActionTypes"
    action_type_id = Column(Integer, primary_key=True)
    name = Column(String(128))


class AgentLog(Base):
    __tablename__ = "AgentLogs"
    agent_log_id = Column(Integer, primary_key=True)
    action_type_id = Column(Integer, ForeignKey("ActionTypes.action_type_id"))
    description = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    action_type = relationship("ActionType")


class UserLog(Base):
    __tablename__ = "UserLogs"
    user_log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    action_type_id = Column(Integer, ForeignKey("ActionTypes.action_type_id"))
    description = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    action_type = relationship("ActionType")


class SeverityLevel(Base):
    __tablename__ = "SeverityLevels"
    severity_level_id = Column(Integer, primary_key=True)
    name = Column(String(128))


class ThreatType(Base):
    __tablename__ = "ThreatTypes"
    threat_type_id = Column(Integer, primary_key=True)
    name = Column(String(128))


class Log(Base):
    __tablename__ = "Logs"
    log_id = Column(Integer, primary_key=True)
    file_content = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "Reports"
    report_id = Column(Integer, primary_key=True)
    log_id = Column(Integer, ForeignKey("Logs.log_id"))
    severity_level_id = Column(Integer, ForeignKey("SeverityLevels.severity_level_id"))
    threat_type_id = Column(Integer, ForeignKey("ThreatTypes.threat_type_id"))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    log = relationship("Log")
    severity = relationship("SeverityLevel")
    threat = relationship("ThreatType")


class Message(Base):
    __tablename__ = "Messages"
    message_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    role = Column(String(32))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
