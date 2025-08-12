import streamlit as st
from titanic_assistant import TitanicAssistant
import matplotlib.pyplot as plt
import re
import traceback

# Page config
st.set_page_config(
    page_title="Titanic Dataset Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize assistant with error handling
@st.cache_resource
def get_assistant():
    try:
        return TitanicAssistant()
    except Exception as e:
        st.error(f"Failed to initialize Titanic Assistant: {e}")
        return None

assistant = get_assistant()

# Check if assistant loaded successfully
if assistant is None:
    st.error("❌ Could not load the Titanic dataset. Please check your setup.")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Debug toggle
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

# Sidebar with enhanced dataset info
with st.sidebar:
    st.title("📊 Titanic Dataset Explorer")
    
    # Debug toggle
    st.session_state.show_debug = st.toggle("Show Debug Info", value=st.session_state.show_debug)
    
    # Dataset Schema
    st.markdown("### 📋 Dataset Schema")
    
    # Get real dataset info
    try:
        summary = assistant.get_dataset_summary()
        total = summary['shape'][0]
        survivors = int(total * summary['survival_rate'])
        survival_rate = summary['survival_rate']
        
        st.markdown(f"""
        **Total Passengers:** {total}  
        **Survivors:** {survivors} ({survival_rate:.1%})  
        **Features:** {summary['shape'][1]} columns
        """)
        
        # Column details
        with st.expander("Column Details"):
            st.markdown("""
            | Column | Type | Description |
            |--------|------|-------------|
            | PassengerId | int | Unique passenger identifier |
            | Survived | int | 1=Survived, 0=Did not survive |
            | Pclass | int | Ticket class (1=1st, 2=2nd, 3=3rd) |
            | Name | str | Full passenger name |
            | Sex | str | 'male' or 'female' |
            | Age | float | Age in years (missing filled) |
            | SibSp | int | # siblings/spouses aboard |
            | Parch | int | # parents/children aboard |
            | Ticket | str | Ticket number |
            | Fare | float | Passenger fare (missing filled) |
            | Cabin | str | Cabin number (many missing) |
            | Embarked | str | Port: C/Q/S |
            """)
    except Exception as e:
        st.error(f"Error loading dataset summary: {e}")
        st.stop()
    
    # Quick Statistics
    st.markdown("### 📈 Quick Stats")
    
    try:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Passengers", total)
            st.metric("1st Class", summary['class_distribution'].get(1, 0))
        with col2:
            st.metric("Survival Rate", f"{survival_rate:.1%}")
            st.metric("3rd Class", summary['class_distribution'].get(3, 0))
            
        # Gender distribution
        gender_dist = summary['gender_distribution']
        st.markdown("**Gender Distribution:**")
        for gender, count in gender_dist.items():
            st.markdown(f"- {gender.title()}: {count}")
            
    except Exception as e:
        st.warning(f"Could not load statistics: {e}")
    
    # Example Queries
    st.markdown("### 💡 Example Queries")
    
    example_queries = [
        "What was the survival rate by passenger class?",
        "Show me age distribution by gender",
        "Plot survival rates by class and gender", 
        "Compare average fares between survivors",
        "What's the relationship between age and fare?",
        "Show passenger count by embarkation port"
    ]
    
    for i, example in enumerate(example_queries):
        if st.button(f"Try: {example[:30]}...", key=f"example_{i}", help=example):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()

# Main chat interface
st.title("🛳️ Titanic Dataset Explorer")

# Welcome message
if not st.session_state.messages:
    st.markdown("""
    👋 **Welcome to the Titanic Dataset Explorer!**
    
    I can help you analyze the famous Titanic dataset with:
    - 📊 Statistical analysis and comparisons
    - 📈 Data visualizations and plots  
    - 🔍 Passenger information queries
    - 💡 Insights about survival patterns
    
    Try the example queries in the sidebar or ask your own questions!
    """)

# Chat input
if prompt := st.chat_input("Ask about the Titanic dataset..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display chat messages with improved error handling
for i, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
            
    elif message["role"] == "assistant":
        with st.chat_message("assistant"):
            # Display content
            if message.get("content"):
                st.markdown(message["content"])
            
            # Display output
            if message.get("output"):
                st.code(message["output"], language="text")
            
            # Display figure
            if message.get("figure"):
                st.pyplot(message["figure"])
                plt.close('all')
            
            # Display error if any
            if message.get("error") and st.session_state.show_debug:
                with st.expander("🐛 Debug Information", expanded=False):
                    st.error(f"Error: {message['error']}")
                    if message.get("code"):
                        st.code(message["code"], language="python")

# Process the last user message if it hasn't been processed
if (st.session_state.messages and 
    st.session_state.messages[-1]["role"] == "user" and 
    (len(st.session_state.messages) == 1 or st.session_state.messages[-2]["role"] == "assistant")):
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analyzing your question..."):
            try:
                response = assistant.handle_query(st.session_state.messages[-1]["content"])
                
                # Extract explanation (text after code blocks)
                explanation = response['answer']
                code_blocks = re.findall(r'```python(.*?)```', explanation, flags=re.DOTALL)
                if code_blocks:
                    # Remove code blocks from explanation
                    for block in code_blocks:
                        explanation = explanation.replace(f'```python{block}```', '')
                    explanation = explanation.strip()
                
                # Display explanation
                if explanation:
                    st.markdown(explanation)
                
                # Display code output
                if response['output']:
                    st.code(response['output'], language="text")
                
                # Display plot
                if response['figure']:
                    st.pyplot(response['figure'])
                    plt.close('all')
                
                # Show errors in debug mode
                if response['error']:
                    if st.session_state.show_debug:
                        with st.expander("🐛 Debug Information", expanded=True):
                            st.error(f"Execution Error: {response['error']}")
                            if response['code']:
                                st.code(response['code'], language="python")
                    else:
                        st.warning("⚠️ There was an issue processing your request. Enable debug mode for details.")
                
                # Save assistant response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": explanation,
                    "output": response.get('output'),
                    "figure": response.get('figure'),
                    "error": response.get('error'),
                    "code": response.get('code')
                })
                
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                if st.session_state.show_debug:
                    st.code(traceback.format_exc())
                
                # Save error message
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "I encountered an error processing your request.",
                    "error": str(e)
                })

# Helpful footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
💡 <strong>Tips:</strong> Ask about survival rates, passenger demographics, fare analysis, or request visualizations!<br>
🔧 <strong>Having issues?</strong> Enable debug mode in the sidebar to see detailed error information.
</div>
""", unsafe_allow_html=True)

# Custom CSS for better appearance
st.markdown("""
<style>
/* Improve chat message appearance */
.stChatMessage {
    padding: 1rem !important;
    margin-bottom: 1rem !important;
    border-radius: 0.5rem !important;
    border: 1px solid #e0e0e0 !important;
}

/* Better code blocks */
.stCode > div {
    background-color: #f8f9fa !important;
    border: 1px solid #e9ecef !important;
    border-radius: 0.375rem !important;
}

/* Improve metrics */
[data-testid="metric-container"] {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Button styling */
.stButton > button {
    width: 100%;
    border-radius: 0.375rem;
    border: 1px solid #dee2e6;
    background-color: #f8f9fa;
    color: #495057;
}

.stButton > button:hover {
    background-color: #e9ecef;
    border-color: #adb5bd;
}

/* Expandable sections */
.streamlit-expanderHeader {
    background-color: #f8f9fa !important;
    border-radius: 0.375rem !important;
}
</style>
""", unsafe_allow_html=True)