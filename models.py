# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import uuid

db = SQLAlchemy()

class KanbanTicket(db.Model):
    __tablename__ = 'kanban_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(100), unique=True, nullable=False)
    ticket_number = db.Column(db.String(50), nullable=False, default="")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='new')
    category = db.Column(db.String(50), default='IN PROGRESS')
    priority = db.Column(db.String(50), default='medium')
    estimated_time = db.Column(db.String(100))
    progress_percentage = db.Column(db.Integer, default=0)
    tags = db.Column(db.JSON, default=list)
    access_required = db.Column(db.JSON, default=list)
    dependencies = db.Column(db.JSON, default=list)
    
    # ✅ FIXED: Using timezone-aware datetime
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, 
                          default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    completed_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    supabase_id = db.Column(db.String(100))
    supabase_uuid = db.Column(db.String(100))
    ai_generated = db.Column(db.Boolean, default=False)
    progress_history = db.Column(db.JSON, default=list)
    
    def __init__(self, **kwargs):
        # Generate ticket_number if not provided
        if 'ticket_number' not in kwargs or not kwargs['ticket_number']:
            kwargs['ticket_number'] = self._generate_ticket_number()
        super().__init__(**kwargs)
    
    def _generate_ticket_number(self):
        """Generate a unique ticket number"""
        return f"TKT-{str(uuid.uuid4())[:8].upper()}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'ticket_number': self.ticket_number,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'category': self.category,
            'priority': self.priority,
            'estimated_time': self.estimated_time,
            'progress_percentage': self.progress_percentage,
            'tags': self.tags,
            'access_required': self.access_required,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ai_generated': self.ai_generated,
            'progress_history': self.progress_history
        }