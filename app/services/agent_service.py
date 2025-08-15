"""
LangGraph agent service with session-aware conversation management
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Local imports
from app.models.schemas import SessionState
from app.services.session_manager import SessionManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AgentService:
    """
    Service for managing LangGraph agent with session persistence
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.checkpointer = MemorySaver()  # LangGraph's built-in memory saver
        self._compiled_graphs = {}  # Cache compiled graphs per session
        self.llm = self._create_llm_instance()
        logger.info("AgentService initialized successfully")
    
    def _create_llm_instance(self):
        """Create and configure the Gemini LLM instance"""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=gemini_api_key,
            temperature=0.7
        )
        logger.info("Gemini LLM instance created successfully")
        return llm
    
    def _session_start_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize or validate session state"""
        session_id = state.get("session_id", "")
        current_time = time.time()
        
        # Initialize conversation history if this is the first call (not in checkpointer)
        if "conversation_history" not in state:
            state["conversation_history"] = []
            state["created_at"] = current_time
            logger.info(f"Initialized new session state for {session_id}")
        else:
            # Validate conversation_history structure
            conversation_history = state.get("conversation_history", [])
            if not isinstance(conversation_history, list):
                logger.warning(f"Invalid conversation_history type for session {session_id}, resetting")
                state["conversation_history"] = []
            else:
                logger.debug(f"Retrieved existing session state for {session_id} with {len(conversation_history)} messages")
        
        # Ensure created_at exists (fallback for legacy sessions)
        if "created_at" not in state:
            state["created_at"] = current_time
            logger.debug(f"Added missing created_at timestamp for session {session_id}")
        
        # Always update last activity
        state["last_activity"] = current_time
        
        return state
    
    def _conversation_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process query with full conversation context"""
        current_query = state["current_query"]
        conversation_history = state.get("conversation_history", [])
        session_id = state.get("session_id", "unknown")
        
        logger.info(f"Processing query for session {session_id} (history: {len(conversation_history)} messages): {current_query[:50]}...")
        
        # Build context from conversation history
        messages = []
        
        # Add conversation history as context
        for msg in conversation_history:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                logger.warning(f"Skipping invalid message in history for session {session_id}: {msg}")
                continue
                
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            else:
                logger.warning(f"Unknown role '{msg['role']}' in conversation history for session {session_id}")
        
        # Add current query
        messages.append(HumanMessage(content=current_query))
        
        # Get response from LLM with full context
        response = self.llm.invoke(messages)
        
        # Update conversation history
        current_time = time.time()
        conversation_history.append({
            "role": "user",
            "content": current_query,
            "timestamp": current_time
        })
        
        conversation_history.append({
            "role": "assistant", 
            "content": response.content,
            "timestamp": current_time
        })
        
        logger.info(f"Query processed successfully for session {session_id}")
        
        return {
            **state,
            "response": response.content,
            "conversation_history": conversation_history,
            "last_activity": current_time
        }
    
    def _create_session_graph(self):
        """Build and compile the session-aware LangGraph workflow"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("session_start", self._session_start_node)
        workflow.add_node("conversation_agent", self._conversation_agent_node)
        
        # Define edges
        workflow.add_edge(START, "session_start")
        workflow.add_edge("session_start", "conversation_agent")
        workflow.add_edge("conversation_agent", END)
        
        # Compile with checkpointing for session persistence
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _get_compiled_graph(self, session_id: str):
        """Get or create compiled graph for session"""
        if session_id not in self._compiled_graphs:
            self._compiled_graphs[session_id] = self._create_session_graph()
            logger.debug(f"Created compiled graph for session {session_id}")
        return self._compiled_graphs[session_id]
    
    def process_query(self, session_id: str, user_query: str) -> Dict[str, Any]:
        """
        Process a user query within a session context
        
        Args:
            session_id: Session identifier
            user_query: User's query string
            
        Returns:
            Dict containing response and metadata
            
        Raises:
            ValueError: If session not found or expired
        """
        start_time = time.time()
        
        # Validate session exists and is not expired
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or expired")
        
        # Get the compiled graph for this session
        app = self._get_compiled_graph(session_id)
        config = {"configurable": {"thread_id": session_id}}
        
        # Get existing state from checkpointer (if any)
        try:
            current_state = app.get_state(config)
            existing_state = current_state.values if current_state and current_state.values else {}
            logger.info(f"Retrieved existing state for session {session_id}: {list(existing_state.keys())}")
        except Exception as e:
            logger.warning(f"Could not retrieve existing state for session {session_id}: {e}")
            existing_state = {}
        
        # Merge existing state with new request data
        initial_state = {
            **existing_state,  # Start with existing state
            "session_id": session_id,
            "current_query": user_query,
            "response": ""  # Reset response for new query
        }
        
        logger.info(f"Initial state for session {session_id}: conversation_history length = {len(initial_state.get('conversation_history', []))}")
        
        try:
            result = app.invoke(initial_state, config=config)
            
            # Update session activity and message count
            session.update_activity()
            session.message_count += 1
            
            processing_time = time.time() - start_time
            
            # Log successful processing with context info
            conversation_length = len(result.get("conversation_history", []))
            logger.info(f"Query processed in {processing_time:.2f}s for session {session_id}, conversation now has {conversation_length} messages")
            
            return {
                "session_id": session_id,
                "query": user_query,
                "response": result["response"],
                "message_count": session.message_count,
                "conversation_history": result["conversation_history"],
                "processing_time": processing_time
            }
        
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing query for session {session_id} after {processing_time:.2f}s: {str(e)}")
            raise
    
    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """
        Get full conversation history for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session history and metadata
            
        Raises:
            ValueError: If session not found or expired
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or expired")
        
        # Get the current state from checkpointer
        if session_id in self._compiled_graphs:
            app = self._compiled_graphs[session_id]
            config = {"configurable": {"thread_id": session_id}}
            
            try:
                # Get latest state
                current_state = app.get_state(config)
                if current_state and current_state.values:
                    return {
                        "session_id": session_id,
                        "created_at": session.created_at,
                        "last_activity": session.last_activity,
                        "message_count": session.message_count,
                        "conversation_history": current_state.values.get("conversation_history", [])
                    }
            except Exception as e:
                logger.warning(f"Could not retrieve state for session {session_id}: {str(e)}")
        
        # Return basic session info if state retrieval fails
        return {
            "session_id": session_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "message_count": session.message_count,
            "conversation_history": []
        }
    
    def cleanup_session_graph(self, session_id: str):
        """Clean up compiled graph cache for ended session"""
        if session_id in self._compiled_graphs:
            del self._compiled_graphs[session_id]
            logger.debug(f"Cleaned up graph cache for session {session_id}")

# Global agent service instance (will be initialized in main app)
_agent_service = None

def get_agent_service() -> AgentService:
    """
    Dependency injection function for FastAPI
    
    Returns:
        AgentService: The global agent service instance
    """
    global _agent_service
    if _agent_service is None:
        from app.services.session_manager import get_session_manager
        _agent_service = AgentService(get_session_manager())
    return _agent_service