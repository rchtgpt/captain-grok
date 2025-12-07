"""
Command execution routes for Grok-Pilot.
Handles text commands with conversational memory and chat streaming.
Features hybrid agentic loop for intelligent multi-step execution.
"""

import json
import time
from flask import Blueprint, request, jsonify, current_app, Response
from core.logger import get_logger
from core.memory import get_memory
from core.chat_generator import get_chat_generator, MessageType
from utils.helpers import format_tool_results
from utils.image_logger import get_image_logger
from ai.prompts import get_contextual_system_prompt

commands_bp = Blueprint('commands', __name__)
log = get_logger('routes.commands')


def sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def emit_chat(message_type: str, content: str, **extra) -> str:
    """Emit a chat message event."""
    chat = get_chat_generator()
    
    # Map message types to chat generator methods
    if message_type == "thinking":
        msg = chat.thinking(content)
    elif message_type == "action":
        msg = chat.system_message(content)
    elif message_type == "observation":
        msg = chat.scene_observation(content)
    elif message_type == "success":
        msg = chat.success(content)
    elif message_type == "error":
        msg = chat.error(content)
    else:
        msg = chat.system_message(content)
    
    return sse_event('chat', {
        'id': msg.id,
        'content': content,
        'type': message_type,
        'timestamp': msg.timestamp.isoformat(),
        **extra
    })


@commands_bp.route('/', methods=['POST'])
def execute_command():
    """Execute a text command (non-streaming, for testing)."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json', 'status': 'error'}), 400
        
        data = request.get_json(force=True)
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field', 'status': 'error'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': 'Empty command', 'status': 'error'}), 400
        
        log.info(f"Command received: {text}")
        
        # Get memory context
        memory = get_memory()
        
        # Get drone flying state
        is_flying = False
        try:
            is_flying = current_app.drone.state_machine.is_flying()
        except:
            pass
        
        system_prompt = get_contextual_system_prompt(memory, drone_flying=is_flying)
        
        # Add user message to conversation
        memory.add_conversation_turn("user", text)
        
        # Build messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(memory.get_conversation_for_ai(last_n=5))
        messages.append({"role": "user", "content": text})
        
        # Call Grok
        grok = current_app.grok
        tools = current_app.tools
        
        result = grok.chat_with_tools(messages=messages, tools=tools.get_schemas())
        
        ai_response = result.get('response', '')
        tool_calls = result.get('tool_calls', [])
        
        # Execute tools
        tool_results = []
        for call in tool_calls:
            try:
                tool_result = tools.execute(call['name'], **call['arguments'])
                tool_results.append({
                    'tool': call['name'],
                    'success': tool_result.success,
                    'message': tool_result.message,
                    'data': tool_result.data
                })
            except Exception as e:
                tool_results.append({
                    'tool': call['name'],
                    'success': False,
                    'message': str(e)
                })
        
        # Add AI response to conversation
        memory.add_conversation_turn("assistant", ai_response)
        
        return jsonify({
            'status': 'success',
            'response': ai_response,
            'tool_results': tool_results,
            'memory_stats': {
                'heading': memory.heading
            }
        })
    
    except Exception as e:
        log.error(f"Command failed: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@commands_bp.route('/stream', methods=['POST'])
def execute_command_stream():
    """
    Execute command with SSE streaming and conversational chat.
    
    Features:
    - Real-time chat messages as drone operates
    - Memory-aware context
    - Hybrid agentic loop (batch related tools, iterate for complex tasks)
    
    SSE Events:
    - chat: Chat message with type (thinking, action, observation, success, error)
    - tool_start: Tool execution starting
    - tool_complete: Tool execution finished
    - memory_update: Entity added/updated in memory
    - found: Target found during search
    - done: Execution complete
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing "text" field'}), 400
    
    text = data['text'].strip()
    if not text:
        return jsonify({'error': 'Empty command'}), 400
    
    # Get app components
    grok = current_app.grok
    tools = current_app.tools
    
    def generate():
        """Generate SSE events with conversational chat."""
        try:
            memory = get_memory()
            chat_gen = get_chat_generator()
            
            log.info(f"Command received: {text}")
            
            # Emit user message
            user_msg = chat_gen.user_message(text)
            yield sse_event('chat', user_msg.to_dict())
            
            # Add to memory
            memory.add_conversation_turn("user", text)
            
            # Get contextual prompt with drone state
            is_flying = False
            try:
                is_flying = current_app.drone.state_machine.is_flying()
            except:
                pass
            
            system_prompt = get_contextual_system_prompt(memory, drone_flying=is_flying)
            
            # Build messages with history
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(memory.get_conversation_for_ai(last_n=5))
            messages.append({"role": "user", "content": text})
            
            # Emit thinking
            thinking_msg = chat_gen.thinking()
            yield sse_event('chat', thinking_msg.to_dict())
            
            # Call Grok
            result = grok.chat_with_tools(messages=messages, tools=tools.get_schemas())
            
            ai_response = result.get('response', '')
            tool_calls = result.get('tool_calls', [])
            
            if ai_response:
                log.info(f"AI: {ai_response}")
            
            # Log tool calls
            if tool_calls:
                log.info(f"Planned {len(tool_calls)} tool(s): {[tc['name'] for tc in tool_calls]}")
            
            # If AI responded with text (no tools), emit it as a chat message
            if ai_response and not tool_calls:
                response_msg = chat_gen.system_message(ai_response)
                yield sse_event('chat', response_msg.to_dict())
            
            # Execute tools with chat updates
            tool_results = []
            successful = 0
            
            for i, call in enumerate(tool_calls):
                tool_name = call['name']
                tool_args = call['arguments']
                
                # Generate appropriate chat message based on tool
                if tool_name == "takeoff":
                    msg = chat_gen.takeoff()
                elif tool_name == "land":
                    msg = chat_gen.landing()
                elif tool_name == "move":
                    msg = chat_gen.moving(tool_args.get('direction', ''), tool_args.get('distance', 0))
                elif tool_name == "rotate":
                    msg = chat_gen.rotating(tool_args.get('degrees', 0))
                elif tool_name == "look" or tool_name == "look_around":
                    msg = chat_gen.scanning()
                elif tool_name == "search":
                    msg = chat_gen.scanning(f"searching for {tool_args.get('target', 'target')}")
                elif tool_name == "recall":
                    msg = chat_gen.memory_recall(f"Checking memory for: {tool_args.get('query', '')}")
                elif tool_name == "navigate_to":
                    msg = chat_gen.navigation_start(tool_args.get('target', 'target'), "remembered location")
                else:
                    msg = chat_gen.system_message(f"Executing: {tool_name}")
                
                yield sse_event('chat', msg.to_dict())
                
                # Emit tool_start
                yield sse_event('tool_start', {
                    'index': i + 1,
                    'total': len(tool_calls),
                    'tool': tool_name,
                    'arguments': tool_args
                })
                
                try:
                    tool_result = tools.execute(tool_name, **tool_args)
                    
                    if tool_result.success:
                        successful += 1
                        
                        # Generate success chat based on tool type
                        if tool_name == "search" and tool_result.data and tool_result.data.get('found'):
                            target_data = tool_result.data.get('target_data', {})
                            desc = target_data.get('description', tool_result.data.get('target', 'target'))
                            
                            # Get entity for direction
                            entity_id = target_data.get('entity_id')
                            entity = memory.get_entity(entity_id) if entity_id else None
                            direction = entity.direction if entity else 'found'
                            distance = entity.estimated_distance_cm if entity else 'unknown'
                            
                            # Get image URL
                            image_url = None
                            try:
                                image_logger = get_image_logger()
                                run_dir = image_logger.run_dir.name
                                image_url = f"/images/vision/{run_dir}/frame_{image_logger.image_counter:04d}.jpg"
                            except:
                                pass
                            
                            found_msg = chat_gen.survivor_found(
                                desc, direction, 
                                distance if isinstance(distance, int) else 150,
                                image_url, entity_id
                            )
                            yield sse_event('chat', found_msg.to_dict())
                            
                            # Emit found event
                            yield sse_event('found', {
                                'target': tool_result.data.get('target', ''),
                                'description': desc,
                                'entity_id': entity_id,
                                'image_url': image_url,
                                'confidence': target_data.get('confidence', 'medium')
                            })
                        
                        elif tool_name == "look" or tool_name == "look_around":
                            # Emit observation - safely access data
                            data = tool_result.data or {}
                            
                            # Handle different field names from look vs look_around
                            summary = data.get('summary', '') or (tool_result.message[:100] if tool_result.message else 'Scan complete')
                            people_count = data.get('people_count', 0) or data.get('total_people', 0) or data.get('memory_people_count', 0) or 0
                            
                            obs_msg = chat_gen.scene_observation(summary, people_count)
                            yield sse_event('chat', obs_msg.to_dict())
                            
                            # Emit memory updates
                            people_added = data.get('people_added', 0) or data.get('total_people', 0) or 0
                            objects_added = data.get('objects_added', 0) or data.get('total_objects', 0) or 0
                            
                            yield sse_event('memory_update', {
                                'people_added': people_added,
                                'objects_added': objects_added
                            })
                            
                            # CRITICAL: Emit facial recognition matches from look/look_around
                            face_matches = data.get('face_matches', [])
                            for match in face_matches:
                                yield sse_event('target_found', match)
                        
                        elif tool_name == "navigate_to":
                            target = tool_args.get('target', 'target')
                            complete_msg = chat_gen.navigation_complete(target)
                            yield sse_event('chat', complete_msg.to_dict())
                        
                        elif tool_name == "recall":
                            recall_msg = chat_gen.memory_recall(tool_result.message)
                            yield sse_event('chat', recall_msg.to_dict())
                        
                        elif tool_name == "name_entity":
                            name = tool_args.get('name', 'entity')
                            named_msg = chat_gen.named_entity(name, '')
                            yield sse_event('chat', named_msg.to_dict())
                        
                        elif tool_name == "find_target":
                            # Target found via facial recognition
                            data = tool_result.data or {}
                            if data.get('found'):
                                from core.targets import get_target_manager
                                target_manager = get_target_manager()
                                target = target_manager.get_target(data.get('target_id', ''))
                                
                                if target:
                                    entity = memory.get_entity(data.get('entity_id', ''))
                                    
                                    yield sse_event('target_found', {
                                        'target': target.to_dict(),
                                        'entity': entity.to_dict() if entity else None,
                                        'confidence': data.get('confidence', 0),
                                        'matched_photo_url': target.matched_photos[-1] if target.matched_photos else None
                                    })
                        
                        elif tool_name == "room_search" or tool_name == "search":
                            # Check for face matches in result
                            data = tool_result.data or {}
                            face_matches = data.get('face_matches', [])
                            
                            for match in face_matches:
                                yield sse_event('target_found', match)
                        
                        elif tool_name == "takeoff":
                            success_msg = chat_gen.success("Airborne and ready!")
                            yield sse_event('chat', success_msg.to_dict())
                        
                        elif tool_name == "summarize_memory":
                            # Memory summary - the message contains the summary
                            summary_msg = chat_gen.memory_recall(tool_result.message[:200] if tool_result.message else "Memory summary complete")
                            yield sse_event('chat', summary_msg.to_dict())
                        
                        elif tool_name == "land":
                            success_msg = chat_gen.success("Landed safely!")
                            yield sse_event('chat', success_msg.to_dict())
                        
                        else:
                            # Generic success
                            msg_text = tool_result.message[:100] if tool_result.message else f"{tool_name} complete"
                            success_msg = chat_gen.success(msg_text)
                            yield sse_event('chat', success_msg.to_dict())
                    
                    else:
                        # Tool failed
                        error_msg = chat_gen.error(tool_result.message[:100])
                        yield sse_event('chat', error_msg.to_dict())
                    
                    # Emit tool_complete - ensure data is serializable
                    result_data = tool_result.data if tool_result.data else {}
                    result_message = tool_result.message if tool_result.message else ''
                    
                    yield sse_event('tool_complete', {
                        'index': i + 1,
                        'tool': tool_name,
                        'success': tool_result.success,
                        'message': result_message,
                        'data': result_data
                    })
                    
                    tool_results.append({
                        'tool': tool_name,
                        'success': tool_result.success,
                        'message': result_message,
                        'data': result_data
                    })
                    
                except Exception as e:
                    log.error(f"Tool {tool_name} failed: {e}")
                    
                    error_msg = chat_gen.error(f"Error: {str(e)[:50]}")
                    yield sse_event('chat', error_msg.to_dict())
                    
                    yield sse_event('tool_complete', {
                        'index': i + 1,
                        'tool': tool_name,
                        'success': False,
                        'message': str(e)
                    })
                    
                    tool_results.append({
                        'tool': tool_name,
                        'success': False,
                        'message': str(e)
                    })
            
            # Add AI response to memory
            if ai_response:
                memory.add_conversation_turn("assistant", ai_response)
            
            # Emit final summary if multiple tools
            if len(tool_calls) > 1:
                people_found = sum(1 for r in tool_results 
                                  if (r.get('data') or {}).get('people_added', 0) > 0 or 
                                  ((r.get('data') or {}).get('found') and 'person' in str(r.get('data') or {}).lower()))
                objects_found = sum((r.get('data') or {}).get('objects_added', 0) for r in tool_results)
                
                if people_found > 0 or objects_found > 0:
                    summary_msg = chat_gen.search_complete(people_found, objects_found)
                    yield sse_event('chat', summary_msg.to_dict())
            
            # Emit done
            yield sse_event('done', {
                'status': 'success',
                'tools_executed': len(tool_calls),
                'successful': successful,
                'memory': {
                    'heading': memory.heading
                }
            })
            
        except Exception as e:
            log.error(f"Stream failed: {e}")
            
            chat_gen = get_chat_generator()
            error_msg = chat_gen.error(f"Error: {str(e)}")
            yield sse_event('chat', error_msg.to_dict())
            
            yield sse_event('done', {
                'status': 'error',
                'error': str(e)
            })
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@commands_bp.route('/raw', methods=['POST'])
def execute_raw_code():
    """Execute raw Python code (for debugging)."""
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'Missing "code" field'}), 400
        
        code = data['code']
        log.warning(f"Executing raw code: {code[:100]}...")
        
        from drone.safety import SafetyExecutor
        executor = SafetyExecutor(current_app.drone, current_app.tools)
        result = executor.execute(code)
        
        return jsonify({
            'status': 'success' if result.success else 'error',
            'message': result.message,
            'output': result.output
        })
    
    except Exception as e:
        log.error(f"Raw code execution failed: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500
