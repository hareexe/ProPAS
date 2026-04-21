from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict

db = SQLAlchemy()

# ---------------- ACCOUNTS (Org + Office + Admin) ----------------
class User(UserMixin, db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    account_type = db.Column(db.String(20))  # 'Org', 'Office', or 'Admin'
    
    # JSON for flexible profile info (contact, department, etc.)
    profile_data = db.Column(MutableDict.as_mutable(db.JSON), default=dict) 

    # Relationship to proposals they created
    proposals = db.relationship('Proposal', backref='creator', lazy=True)


# ---------------- PROPOSAL ----------------
class Proposal(db.Model):
    __tablename__ = 'proposals'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    version_number = db.Column(db.Integer, default=1)
    
    # file_path stores the local filename (e.g., "20260402_123.pdf")
    file_path = db.Column(db.String(300))
    
    # THE FIX: Added JSON column for all form-specific metadata
    proposal_data = db.Column(db.JSON) 
    
    current_step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    current_step = db.relationship('ApprovalStep', foreign_keys=[current_step_id])


# ---------------- APPROVAL STEPS ----------------
class ApprovalStep(db.Model):
    __tablename__ = 'approval_steps'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)  # CAS, OSA, FINANCE, etc.
    step_order = db.Column(db.Integer, unique=True)


# ---------------- DOCUMENT APPROVALS ----------------
class DocumentApproval(db.Model):
    __tablename__ = 'document_approvals'
    id = db.Column(db.Integer, primary_key=True)
    
    document_id = db.Column(db.Integer, db.ForeignKey('proposals.id'))
    step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    signed_name = db.Column(db.String(150))
    remarks = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('document_id', 'step_id'),
    )

    # Relationships
    step = db.relationship('ApprovalStep')
    document = db.relationship('Proposal', backref=db.backref('approvals', lazy=True))
    approver = db.relationship('User')


# ---------------- DOCUMENT VERSION ----------------
class DocumentVersion(db.Model):
    __tablename__ = 'document_versions'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('proposals.id'))
    file_path = db.Column(db.String(300))
    version_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Proposal', backref=db.backref('versions', lazy=True))


# ---------------- DOCUMENT LOGS ----------------
class DocumentLog(db.Model):
    __tablename__ = 'document_logs'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('proposals.id'))
    action = db.Column(db.String(100))  # created, submitted, approved, rejected
    performed_by = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    document = db.relationship('Proposal', backref=db.backref('logs', lazy=True))
    performer = db.relationship('User')

class ProposalMessage(db.Model):
    __tablename__ = 'proposal_messages'
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    office_step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    sender_role = db.Column(db.String(20), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    proposal = db.relationship('Proposal', backref=db.backref('messages', lazy=True))
    office_step = db.relationship('ApprovalStep')
    sender = db.relationship('User')
