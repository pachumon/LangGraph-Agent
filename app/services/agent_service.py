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
        
        # Classification configuration
        self.default_response = "I can only help with country capitals. Please ask about a country's capital city."
        self.geography_keywords = ["capital", "capitals", "city", "country", "countries", "nation", "nations"]
        
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
    
    def _classify_question_rules(self, query: str) -> Optional[str]:
        """Fast rule-based classification for obvious geography questions"""
        query_lower = query.lower()
        
        # Check for geography keywords
        if any(keyword in query_lower for keyword in self.geography_keywords):
            return "geography"
        
        return None  # Unclear, need LLM classification
    
    def _classify_question_llm(self, query: str) -> str:
        """Use LLM for ambiguous classification"""
        classification_prompt = f"""You are a question classifier. Determine if this question is about geography (specifically country capitals, cities, or countries) or something else.

Question: "{query}"

Answer with exactly one word: "geography" or "other"

Examples:
- "What's the capital of France?" → geography
- "Tell me about Paris" → geography  
- "What's 2+2?" → other
- "How are you?" → other
- "What's the main city of Germany?" → geography"""
        
        try:
            response = self.llm.invoke(classification_prompt)
            classification = response.content.strip().lower()
            return "geography" if classification == "geography" else "other"
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, defaulting to 'other'")
            return "other"
    
    def _classify_question(self, query: str) -> str:
        """Hybrid classification: rules first, then LLM for ambiguous cases"""
        # Try rule-based classification first
        rule_result = self._classify_question_rules(query)
        if rule_result:
            logger.info(f"Rule-based classification: '{query[:30]}...' → {rule_result}")
            return rule_result
        
        # Fall back to LLM classification
        llm_result = self._classify_question_llm(query)
        logger.info(f"LLM classification: '{query[:30]}...' → {llm_result}")
        return llm_result
    
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
    
    def _question_classifier_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the question and set routing decision"""
        current_query = state["current_query"]
        session_id = state.get("session_id", "unknown")
        
        # Classify the question
        question_type = self._classify_question(current_query)
        
        # Add classification result to state
        state["question_type"] = question_type
        
        logger.info(f"Question classified as '{question_type}' for session {session_id}")
        return state
    
    def _geography_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process geography questions with specialized system prompt"""
        current_query = state["current_query"]
        conversation_history = state.get("conversation_history", [])
        session_id = state.get("session_id", "unknown")
        
        logger.info(f"Processing geography query for session {session_id}: {current_query[:50]}...")
        
        # Build context with geography-specific system prompt
        messages = []
        
        # Add system message for geography specialization
        system_message = """You are a geography expert focused specifically on country capitals. 
        Provide accurate, concise answers about country capitals, capital cities, and related geographic information.
        If asked about anything not related to country capitals, politely redirect to that topic."""
        
        # Add conversation history as context
        for msg in conversation_history:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                continue
                
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current query with system context
        if not messages:  # First message, add system context
            enhanced_query = f"{system_message}\n\nUser question: {current_query}"
        else:
            enhanced_query = current_query
            
        messages.append(HumanMessage(content=enhanced_query))
        
        # Get response from LLM
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
        
        logger.info(f"Geography query processed successfully for session {session_id}")
        
        return {
            **state,
            "response": response.content,
            "conversation_history": conversation_history,
            "last_activity": current_time
        }
    
    def _default_responder_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Provide default response for non-geography questions"""
        current_query = state["current_query"]
        conversation_history = state.get("conversation_history", [])
        session_id = state.get("session_id", "unknown")
        
        logger.info(f"Providing default response for non-geography query in session {session_id}: {current_query[:50]}...")
        
        # Update conversation history with the default response
        current_time = time.time()
        conversation_history.append({
            "role": "user",
            "content": current_query,
            "timestamp": current_time
        })
        
        conversation_history.append({
            "role": "assistant",
            "content": self.default_response,
            "timestamp": current_time
        })
        
        return {
            **state,
            "response": self.default_response,
            "conversation_history": conversation_history,
            "last_activity": current_time
        }
    
    def _route_question(self, state: Dict[str, Any]) -> str:
        """Route based on question classification"""
        question_type = state.get("question_type", "other")
        if question_type == "geography":
            return "geography_agent"
        else:
            return "default_responder"
    
    def _create_session_graph(self):
        """Build and compile the session-aware LangGraph workflow with classification routing"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("session_start", self._session_start_node)
        workflow.add_node("question_classifier", self._question_classifier_node)
        workflow.add_node("geography_agent", self._geography_agent_node)
        workflow.add_node("default_responder", self._default_responder_node)
        
        # Define edges
        workflow.add_edge(START, "session_start")
        workflow.add_edge("session_start", "question_classifier")
        
        # Conditional routing based on question classification
        workflow.add_conditional_edges(
            "question_classifier",
            self._route_question,
            {
                "geography_agent": "geography_agent",
                "default_responder": "default_responder"
            }
        )
        
        # Both paths end the workflow
        workflow.add_edge("geography_agent", END)
        workflow.add_edge("default_responder", END)
        
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