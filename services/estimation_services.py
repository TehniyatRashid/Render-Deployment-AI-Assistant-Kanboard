# services/estimation_service.py
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List

class TicketEstimator:
    """Service for creating and managing tickets from estimates"""
    
    def __init__(self):
        self.ticket_counter = 1000
    
    def create_ticket(self, task: str, estimate: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a ticket from an estimate"""
        ticket_id = self._generate_ticket_id(task)
        
        ticket = {
            'id': ticket_id,
            'task': task,
            'status': 'Estimated',
            'created_at': datetime.now().isoformat(),
            'estimated_at': datetime.now().isoformat(),
            'estimate_details': estimate,
            'metadata': metadata or {},
            'history': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'Created',
                    'details': 'Ticket estimated by AI assistant'
                }
            ]
        }
        
        # Add suggested assignee based on required access
        ticket['suggested_assignee'] = self._suggest_assignee(estimate)
        
        return ticket
    
    def _generate_ticket_id(self, task: str) -> str:
        """Generate a unique ticket ID"""
        # Use hash of task for consistency
        task_hash = hashlib.md5(task.encode()).hexdigest()[:6].upper()
        self.ticket_counter += 1
        return f"TKT-{self.ticket_counter}-{task_hash}"
    
    def _suggest_assignee(self, estimate: Dict[str, Any]) -> str:
        """Suggest assignee based on required access"""
        required_access = estimate.get('required_access', [])
        
        if 'Backend' in required_access and 'Frontend' in required_access:
            return 'Full Stack Developer'
        elif 'Backend' in required_access:
            return 'Backend Developer'
        elif 'Frontend' in required_access:
            return 'Frontend Developer'
        elif 'Database' in required_access:
            return 'Database Administrator'
        elif 'DevOps' in required_access:
            return 'DevOps Engineer'
        else:
            return 'General Developer'
    
    def update_ticket_status(self, ticket_id: str, status: str, notes: str = None) -> Dict[str, Any]:
        """Update ticket status"""
        # In production, this would update a database
        return {
            'ticket_id': ticket_id,
            'status': status,
            'updated_at': datetime.now().isoformat(),
            'notes': notes
        }