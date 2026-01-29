from flask import Blueprint, jsonify, request, render_template
from models import db, KanbanTicket
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import logging
import calendar

kanban_blueprint = Blueprint('kanban', __name__)
logger = logging.getLogger(__name__)

@kanban_blueprint.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get real-time dashboard statistics for tiles"""
    try:
        total = KanbanTicket.query.count() or 0
        # Stages counts
        new_count = KanbanTicket.query.filter_by(status='new').count()
        in_progress = KanbanTicket.query.filter_by(status='in_progress').count()
        completed = KanbanTicket.query.filter_by(status='completed').count()
        review = KanbanTicket.query.filter_by(status='review').count()
        blocked = KanbanTicket.query.filter_by(status='blocked').count()

        # Calculate average progress ONLY for tickets that are "in_progress"
        in_progress_tickets = KanbanTicket.query.filter_by(status='in_progress').all()
        if in_progress_tickets:
            # Get all non-null progress values, default to 0 if null
            progress_values = [t.progress_percentage if t.progress_percentage is not None else 0 for t in in_progress_tickets]
            avg_progress = sum(progress_values) / len(progress_values) if progress_values else 0
            logger.info(f"In Progress tickets: {len(in_progress_tickets)}, Progress values: {progress_values}, Average: {avg_progress}")
        else:
            avg_progress = 0
            logger.info("No tickets in progress")
        
        # Calculate average progress across ALL ACTIVE projects (excluding completed)
        active_tickets = KanbanTicket.query.filter(
            KanbanTicket.status.in_(['new', 'in_progress', 'review', 'blocked'])
        ).all()
        
        if active_tickets:
            # Calculate weighted progress based on status
            total_progress = 0
            for ticket in active_tickets:
                if ticket.status == 'new':
                    # New tickets are 0% complete
                    total_progress += 0
                elif ticket.status == 'review':
                    # Review tickets are considered 90% complete
                    total_progress += 90
                elif ticket.status == 'blocked':
                    # Blocked tickets use their current progress or default to 30%
                    total_progress += (ticket.progress_percentage if ticket.progress_percentage is not None else 30)
                else:  # in_progress
                    # In progress tickets use their actual progress or default to 50%
                    total_progress += (ticket.progress_percentage if ticket.progress_percentage is not None else 50)
            
            avg_active_progress = total_progress / len(active_tickets)
            logger.info(f"Active tickets: {len(active_tickets)}, Average active progress: {avg_active_progress}")
        else:
            avg_active_progress = 0
            logger.info("No active tickets")
        
        # Calculate ON HOLD category breakdown
        blocked_tickets = KanbanTicket.query.filter_by(status='blocked').all()
        on_hold_categories = {
            'Pending Reviews': 0,
            'Access Issue': 0,
            'Code Quality': 0,
            'Other': 0
        }
        
        if blocked_tickets:
            for ticket in blocked_tickets:
                category = ticket.category or 'Other'
                # Map database categories to display categories
                if 'review' in category.lower():
                    on_hold_categories['Pending Reviews'] += 1
                elif 'access' in category.lower():
                    on_hold_categories['Access Issue'] += 1
                elif 'quality' in category.lower() or 'code' in category.lower():
                    on_hold_categories['Code Quality'] += 1
                else:
                    on_hold_categories['Other'] += 1
            
            # Convert to percentages
            total_blocked = len(blocked_tickets)
            on_hold_percentages = {
                key: round((value / total_blocked) * 100) if total_blocked > 0 else 0
                for key, value in on_hold_categories.items()
            }
        else:
            on_hold_percentages = {
                'Pending Reviews': 0,
                'Access Issue': 0,
                'Code Quality': 0,
                'Other': 0
            }

        return jsonify({
            'success': True,
            'stats': {
                'total_tickets': total,
                'completion_status': round(avg_active_progress),
                'tiles': {
                    'NEW': {'count': new_count},
                    'IN_PROGRESS': {'count': in_progress},
                    'REVIEW': {'count': review},
                    'COMPLETED': {'count': completed},
                    'ON_HOLD': {
                        'count': blocked,
                        'categories': on_hold_percentages
                    }
                }
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kanban_blueprint.route('/api/kanban-tickets', methods=['GET'])
def get_kanban_tickets():
    """Group tickets by stages for the Kanban view"""
    try:
        tickets = KanbanTicket.query.all()
        grouped = {
            'new': [t.to_dict() for t in tickets if t.status == 'new'],
            'in_progress': [t.to_dict() for t in tickets if t.status == 'in_progress'],
            'review': [t.to_dict() for t in tickets if t.status == 'review'],
            'completed': [t.to_dict() for t in tickets if t.status == 'completed'],
            'blocked': [t.to_dict() for t in tickets if t.status == 'blocked']
        }
        return jsonify({'success': True, 'tickets': grouped})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@kanban_blueprint.route('/api/kanban-tickets/<int:ticket_id>', methods=['PATCH'])
def update_ticket_status(ticket_id):
    """Update a ticket's status when dragged to a new column"""
    try:
        ticket = KanbanTicket.query.get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        data = request.get_json()
        new_status = data.get('status')
        new_progress = data.get('progress_percentage')
        
        if new_status and new_status not in ['new', 'in_progress', 'review', 'completed', 'blocked']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Update status if provided
        if new_status:
            ticket.status = new_status
            ticket.updated_at = datetime.utcnow()
            
            # Update timestamps based on status
            if new_status == 'in_progress' and not ticket.started_at:
                ticket.started_at = datetime.utcnow()
                # Set initial progress to 10% when moved to in_progress if not already set
                if ticket.progress_percentage is None or ticket.progress_percentage == 0:
                    ticket.progress_percentage = 10
            elif new_status == 'completed' and not ticket.completed_at:
                ticket.completed_at = datetime.utcnow()
                ticket.progress_percentage = 100
            elif new_status == 'new':
                ticket.progress_percentage = 0
                ticket.started_at = None
                ticket.completed_at = None
        
        # Update progress if provided
        if new_progress is not None:
            ticket.progress_percentage = max(0, min(100, int(new_progress)))  # Ensure 0-100
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating ticket: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kanban_blueprint.route('/api/kanban-tickets/reset', methods=['POST'])
def reset_all_tickets():
    """Reset all tickets to 'new' status"""
    try:
        tickets = KanbanTicket.query.all()
        for ticket in tickets:
            ticket.status = 'new'
            ticket.progress_percentage = 0
            ticket.started_at = None
            ticket.completed_at = None
            ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Reset {len(tickets)} tickets to new status'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kanban_blueprint.route('/api/historical-stats', methods=['GET'])
def get_historical_stats():
    """Get historical statistics for charts (last 6 months)"""
    try:
        # Get last 6 months
        today = datetime.utcnow()
        months_data = []
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for i in range(5, -1, -1):
            month_date = today - timedelta(days=30 * i)
            month_num = month_date.month
            year = month_date.year
            months_data.append({
                'month': month_num,
                'year': year,
                'label': month_names[month_num - 1]
            })
        
        # Calculate new tickets per month
        new_tickets_data = []
        for month_info in months_data:
            count = KanbanTicket.query.filter(
                extract('month', KanbanTicket.created_at) == month_info['month'],
                extract('year', KanbanTicket.created_at) == month_info['year']
            ).count()
            new_tickets_data.append(count)
        
        # Calculate completed tickets per month
        completed_tickets_data = []
        for month_info in months_data:
            count = KanbanTicket.query.filter(
                KanbanTicket.status == 'completed',
                extract('month', KanbanTicket.completed_at) == month_info['month'],
                extract('year', KanbanTicket.completed_at) == month_info['year']
            ).count()
            completed_tickets_data.append(count)
        
        return jsonify({
            'success': True,
            'new_tickets': {
                'labels': [m['label'] for m in months_data],
                'values': new_tickets_data
            },
            'completed_tickets': {
                'labels': [m['label'] for m in months_data],
                'values': completed_tickets_data
            }
        })
    except Exception as e:
        logger.error(f"Error fetching historical stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@kanban_blueprint.route('/api/kanban-tickets/<int:ticket_id>/detail', methods=['GET'])
def get_ticket_detail(ticket_id):
    """Get detailed information for a single ticket"""
    try:
        ticket = KanbanTicket.query.get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        })
    except Exception as e:
        logger.error(f"Error fetching ticket detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@kanban_blueprint.route('/ticket-preview')
def ticket_preview():
    """Render the ticket preview page"""
    ticket_id = request.args.get('ticket_id')
    return render_template('ticket_preview.html', ticket_id=ticket_id)    
