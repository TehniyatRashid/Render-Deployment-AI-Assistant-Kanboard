# ai_task_creator.py
from flask import Blueprint, request, jsonify, current_app # Add current_app here
import logging
import hashlib
import uuid
from datetime import datetime

# Import db from models - will be initialized by app.py
from models import db, KanbanTicket

# Import services
try:
    from services.estimation_services import TicketEstimator
    ticket_service = TicketEstimator()
except ImportError:
    ticket_service = None

# Create blueprint
ai_task_blueprint = Blueprint('ai_task', __name__)
logger = logging.getLogger(__name__)

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)

# Logic for AI Estimator
try:
    from services.ai_services import AIEstimator
    logger.info("✅ AIEstimator imported successfully")
    ai_estimator = AIEstimator()
except ImportError as e:
    logger.error(f"❌ Failed to import AIEstimator: {e}")
    class AIEstimator:
        def estimate_task(self, task, options=None):
            return {
                "success": True,
                "estimated_time": "2 days", 
                "priority": "Medium",
                "complexity_level": "Medium",
                "dependencies": ["Initial setup"],
                "required_access": ["Backend"],
                "suggested_labels": ["feature"],
                "reasoning": "Basic implementation (FALLBACK RESPONSE)"
            }
    ai_estimator = AIEstimator()

def generate_ticket_number():
    """Generate a unique ticket number"""
    return f"TKT-{str(uuid.uuid4())[:8].upper()}"

@ai_task_blueprint.route('/api/estimate', methods=['POST'])
def get_ai_estimate():
    print("\n" + "🚀"*30)
    print("🚀 /api/estimate ENDPOINT HIT!")
    print("🚀"*30 + "\n")
    
    try:
        data = request.get_json()
        task_description = data.get('task', '').strip()
        
        print("\n" + "="*60)
        print("🔍 NEW ESTIMATE REQUEST")
        print("="*60)
        print(f"📝 Task: {task_description}")
        print(f"📦 Full request data: {data}")
        print("="*60 + "\n")
        
        if not task_description:
            return jsonify({
                'success': False, 
                'error': 'Task description is required'
            }), 400
        
        # Call AI service
        logger.info(f"🤖 Calling AI estimator for: {task_description[:50]}...")
        ai_response = ai_estimator.estimate_task(task_description)
        
        print("\n" + "="*60)
        print("🤖 AI RESPONSE RECEIVED")
        print("="*60)
        print(f"✅ Success: {ai_response.get('success')}")
        print(f"⏱️  Estimated Time: {ai_response.get('estimated_time')}")
        print(f"🎯 Priority: {ai_response.get('priority')}")
        print(f"💭 Reasoning: {ai_response.get('reasoning', '')[:100]}...")
        print(f"📋 Full Response: {ai_response}")
        print("="*60 + "\n")
        
        if ai_response.get('success'):
            # Generate ticket ID
            ticket_id = hashlib.md5(task_description.encode()).hexdigest()[:16]
            ticket_number = generate_ticket_number()
            
            # Prepare data
            tags = ai_response.get('suggested_labels', [])
            if isinstance(tags, str):
                tags = [tags]
            
            access_required = ai_response.get('required_access', [])
            if isinstance(access_required, str):
                access_required = [access_required]
            
            dependencies = ai_response.get('dependencies', [])
            if isinstance(dependencies, str):
                dependencies = [dependencies]

            # Use AI title or generate from description
            raw_title = ai_response.get('title')
            title = (
                raw_title.strip()
                if isinstance(raw_title, str) and 3 <= len(raw_title.split()) <= 6
                else generate_short_title(task_description)
            )

            # Return the AI estimate WITHOUT creating the ticket yet
            response_data = {
                'success': True,
                'ticket_id': ticket_id,
                'ticket_number': ticket_number,
                'task': task_description,
                'title': title,
                'estimate': {
                    'estimated_time': ai_response.get('estimated_time', 'Unknown'),
                    'priority': ai_response.get('priority', 'Medium'),
                    'complexity_level': ai_response.get('complexity_level', 'Medium'),
                    'dependencies': dependencies,
                    'required_access': access_required,
                    'suggested_labels': tags,
                    'reasoning': ai_response.get('reasoning', '')
                }
            }
            
            print("\n" + "="*60)
            print("📤 SENDING RESPONSE TO FRONTEND")
            print("="*60)
            print(f"Response: {response_data}")
            print("="*60 + "\n")
            
            return jsonify(response_data)
        else:
            logger.error(f"❌ AI generation failed: {ai_response.get('error')}")
            return jsonify({
                'success': False, 
                'error': ai_response.get('error', 'AI generation failed')
            }), 500

    except Exception as e:
        logger.error(f"💥 EXCEPTION in get_ai_estimate: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@ai_task_blueprint.route('/api/create-ticket', methods=['POST'])
def create_final_ticket():
    try:
        data = request.get_json()
        
        print("\n" + "="*60)
        print("🎫 CREATING TICKET")
        print("="*60)
        print(f"Data received: {data}")
        print("="*60 + "\n")
        
        logger.info(f"Received ticket data: {data}")
        # Use the application context to perform DB operations
        with current_app.app_context():

        # Create new ticket object
            new_ticket = KanbanTicket(
                ticket_id=data.get('ticket_id'),
                ticket_number=data.get('ticket_number') or generate_ticket_number(),
                title=data.get('title', generate_short_title(data.get('task', 'New Ticket'))),
                description=data.get('edited_description', ''),
                status='new',
                priority=data.get('edited_priority', 'medium').lower(),
                estimated_time=data.get('estimate', {}).get('estimated_time', 'TBD'),
                tags=data.get('estimate', {}).get('suggested_labels', []),
                access_required=data.get('estimate', {}).get('required_access', []),
                dependencies=data.get('estimate', {}).get('dependencies', [])
            )
            
            # Add to database
            db.session.add(new_ticket)
            db.session.commit()
            # Convert to dict while still inside the context
            ticket_data = new_ticket.to_dict()
            logger.info(f"✅ Ticket created successfully: {new_ticket.ticket_number}")
            
        return jsonify({
            'success': True, 
            'ticket': ticket_data,
            'message': f"Ticket {ticket_data['ticket_number']} created successfully!"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"💥 DB Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

def generate_short_title(task: str, max_words: int = 6) -> str:
    """
    Generate a short, Kanban-style title from a task description.
    """
    if not task:
        return "New Ticket"

    task = task.replace("\n", " ").strip()
    words = task.split()

    short_title = " ".join(words[:max_words])
    return short_title.capitalize()