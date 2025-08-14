# Import required libraries and modules
import os  # For accessing environment variables
from typing import TypedDict  # For type hinting with dictionary structure
from dotenv import load_dotenv  # For loading environment variables from .env file
from langchain_google_genai import ChatGoogleGenerativeAI  # Google's Gemini AI model wrapper
from langgraph.graph import StateGraph, START, END  # LangGraph components for building the agent workflow

# Load environment variables from .env file into the system environment
load_dotenv()

# Define the state structure that will be passed between nodes in the graph
# TypedDict provides type hints for dictionary keys and their expected value types
class AgentState(TypedDict):
    user_query: str  # The input question/query from the user
    response: str    # The AI-generated response to the query

# Start node function - handles initial processing and validation
# This is the entry point where we can add preprocessing logic
def start_node(state: AgentState):
    # Validate that we have a user query
    user_query = state.get("user_query", "").strip()
    
    # Basic validation - ensure query is not empty
    if not user_query:
        return {
            "user_query": "No query provided",
            "response": "Please provide a valid query."
        }
    
    # Return the state, potentially with any preprocessing done
    return {
        "user_query": user_query,
        "response": state.get("response", "")  # Preserve any existing response
    }

# Function to create and configure the Gemini LLM (Large Language Model) instance
def create_llm_agent():
    # Retrieve the Gemini API key from environment variables
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    # Check if the API key exists, raise an error if it's missing
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    # Initialize the Gemini AI model with configuration parameters
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",  # Specify the Gemini model version to use
        google_api_key=gemini_api_key,  # Pass the API key for authentication
        temperature=0.7  # Control randomness in responses (0.0 = deterministic, 1.0 = very random)
    )
    return llm

# Main agent processing node - this function handles the core logic
# It receives the current state and returns an updated state with the AI response
def agent_node(state: AgentState):
    # Create an instance of the LLM agent
    llm = create_llm_agent()
    
    # Extract the user's query from the current state
    user_query = state["user_query"]
    
    # Send the query to the Gemini AI model and get a response
    response = llm.invoke(user_query)
    
    # Return the updated state with both the original query and the AI's response
    return {
        "user_query": user_query,        # Preserve the original user query
        "response": response.content     # Extract the text content from the AI response
    }

# Function to build and configure the LangGraph workflow
def create_graph():
    # Initialize a StateGraph with our defined state structure
    workflow = StateGraph(AgentState)
    
    # Add all nodes to the workflow graph
    workflow.add_node("start", start_node)    # Entry node for preprocessing/validation
    workflow.add_node("agent", agent_node)   # Main AI processing node
    
    # Define the workflow edges (path between nodes)
    workflow.add_edge(START, "start")        # START -> start node
    workflow.add_edge("start", "agent")      # start node -> agent node  
    workflow.add_edge("agent", END)          # agent node -> END
    
    # Compile the workflow into an executable graph and return it
    return workflow.compile()

# High-level function to run the agent with a user query
def run_agent(query: str):
    # Create the compiled workflow graph
    app = create_graph()
    
    # Set up the initial state with the user's query
    initial_state = {
        "user_query": query,  # The user's input question
        "response": ""        # Empty response field to be filled by the agent
    }
    
    # Execute the workflow with the initial state
    result = app.invoke(initial_state)
    
    # Return only the response part of the final state
    return result["response"]

# Main execution block - only runs when script is executed directly (not imported)
if __name__ == "__main__":
    # Print a welcome header for the application
    print("LangGraph Gemini Agent")
    print("=" * 50)  # Create a line of 50 equal signs for visual separation
    
    # Start an infinite loop for continuous user interaction
    while True:
        # Get user input from the command line
        user_input = input("\nEnter your query (or 'quit' to exit): ")
        
        # Check if user wants to exit the program
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break  # Exit the while loop and end the program
        
        # Try to process the user's query and handle any potential errors
        try:
            # Call the agent with the user's input and get a response
            response = run_agent(user_input)
            # Display the AI's response to the user
            print(f"\nAgent Response: {response}")
        except Exception as e:
            # Handle any errors that occur during processing
            print(f"Error: {e}")
            print("Make sure you have set the GEMINI_API_KEY environment variable")