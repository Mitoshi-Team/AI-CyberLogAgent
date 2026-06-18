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


class ReportIncident(Base):
    __tablename__ = "ReportIncidents"
    incident_id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("Reports.report_id"))
    event_description = Column(Text, nullable=False)
    group_id = Column(String(64))
    mitre_technique_id = Column(String(64), nullable=False)
    mitre_technique_name = Column(String(256), nullable=False)
    mitre_tactic = Column(String(256), nullable=False)
    severity_level_id = Column(Integer, ForeignKey("SeverityLevels.severity_level_id"), nullable=False)
    threat_type_id = Column(Integer, ForeignKey("ThreatTypes.threat_type_id"))
    confirmed = Column("confirmed", Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    report = relationship("Report", back_populates="incidents")
    severity = relationship("SeverityLevel")
    threat = relationship("ThreatType")


class Report(Base):
    __tablename__ = "Reports"
    report_id = Column(Integer, primary_key=True)
    log_id = Column(Integer, ForeignKey("Logs.log_id"))
    severity_level_id = Column(Integer, ForeignKey("SeverityLevels.severity_level_id"))
    threat_type_id = Column(Integer, ForeignKey("ThreatTypes.threat_type_id"), nullable=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    log = relationship("Log")
    severity = relationship("SeverityLevel")
    threat = relationship("ThreatType")
    incidents = relationship("ReportIncident", back_populates="report", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "Messages"
    message_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    role = Column(String(32))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class YaraRule(Base):
    __tablename__ = "YaraRules"
    yara_rule_id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SigmaRule(Base):
    __tablename__ = "SigmaRules"
    sigma_rule_id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PendingYaraRule(Base):
    __tablename__ = "PendingYaraRules"
    pending_rule_id = Column(Integer, primary_key=True)
    rule_name = Column(String(256), nullable=False)
    rule_content = Column(Text, nullable=False)
    technique_id = Column(String(64))
    technique_name = Column(String(256))
    report_id = Column(Integer, ForeignKey("Reports.report_id"))
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    report = relationship("Report")
