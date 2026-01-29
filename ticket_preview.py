from flask import Blueprint, jsonify, request, render_template
from models import db, KanbanTicket
from datetime import datetime
import json
import logging

ticket_preview_blueprint = Blueprint('ticket_preview', __name__)
logger = logging.getLogger(__name__)

@ticket_preview_blueprint.route('/ticket-preview')
def serve_ticket_preview():
    """Serve the ticket preview HTML page"""
    ticket_id = request.args.get('ticket_id')
    return render_template('ticket_preview.html', ticket_id=ticket_id)

@ticket_preview_blueprint.route('/api/ticket/<ticket_identifier>', methods=['GET'])
def get_ticket_details(ticket_identifier):
    """Get ticket details by ID, ticket_number, or ticket_id"""
    try:
        # Try all possible identifiers
        ticket = None
        
        if ticket_identifier.isdigit():
            # Try as primary key ID
            ticket = KanbanTicket.query.get(int(ticket_identifier))
        else:
            # Try as ticket_number
            ticket = KanbanTicket.query.filter_by(ticket_number=ticket_identifier).first()
            if not ticket:
                # Try as ticket_id
                ticket = KanbanTicket.query.filter_by(ticket_id=ticket_identifier).first()
        
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        # Return only the necessary fields
        return jsonify({
            'success': True,
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'ticket_id': ticket.ticket_id,
                'title': ticket.title,
                'description': ticket.description or '',
                'status': ticket.status,
                'priority': ticket.priority,
                'category': ticket.category or 'general',
                'progress_percentage': ticket.progress_percentage or 0,
                'estimated_time': ticket.estimated_time,
                'tags': ticket.tags if ticket.tags else [],
                'access_required': ticket.access_required if ticket.access_required else [],  # ADD THIS LINE
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                'started_at': ticket.started_at.isoformat() if ticket.started_at else None,
                'completed_at': ticket.completed_at.isoformat() if ticket.completed_at else None,
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticket: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500
@ticket_preview_blueprint.route('/api/ticket/<ticket_identifier>', methods=['PATCH'])
def update_ticket(ticket_identifier):
    """Update ONLY status and tags of a ticket"""
    try:
        # Get ticket
        ticket = None
        
        if ticket_identifier.isdigit():
            ticket = KanbanTicket.query.get(int(ticket_identifier))
        else:
            ticket = KanbanTicket.query.filter_by(ticket_number=ticket_identifier).first()
            if not ticket:
                ticket = KanbanTicket.query.filter_by(ticket_id=ticket_identifier).first()
        
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Ticket not found'
            }), 404
        
        data = request.get_json()
        
        # Track if anything changed
        changed = False
        old_status = ticket.status  # Store old status for smooth updates
        
        # Update ONLY status if provided
        if 'status' in data and data['status'] != ticket.status:
            new_status = data['status']
            
            ticket.status = new_status
            changed = True
            
            # Update timestamps based on status change
            if new_status == 'in_progress' and old_status != 'in_progress':
                ticket.started_at = datetime.utcnow()
            elif new_status == 'completed' and old_status != 'completed':
                ticket.completed_at = datetime.utcnow()
                ticket.progress_percentage = 100
            elif new_status == 'new':
                ticket.started_at = None
                ticket.completed_at = None
        
        # Update ONLY tags if provided
        if 'tags' in data and data['tags'] is not None:
            ticket.tags = data['tags']  # Should be a list
            changed = True
        
        # Only update timestamps if something changed
        if changed:
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status,
                'old_status': old_status,  # ADD THIS: for smooth dashboard updates
                'tags': ticket.tags if ticket.tags else [],
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                'started_at': ticket.started_at.isoformat() if ticket.started_at else None,
                'completed_at': ticket.completed_at.isoformat() if ticket.completed_at else None,
            },
            'message': 'Ticket updated successfully' if changed else 'No changes made'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating ticket: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error',
            'details': str(e)
        }), 500
  