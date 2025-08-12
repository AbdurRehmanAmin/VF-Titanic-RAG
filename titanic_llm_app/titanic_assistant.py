import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
import re
from io import StringIO
import traceback
import warnings
from typing import Dict, Any, Tuple, Optional

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
genai.configure(api_key=api_key)

class TitanicAssistant:
    def __init__(self):
        """Initialize the Titanic dataset assistant with improved error handling."""
        try:
            # Load and prepare the dataset
            self.df = pd.read_csv("titanic.csv")
            self.original_df = self.df.copy()  # Keep original for reference
            
            # Clean and prepare data with better error handling
            self._prepare_data()
            
            # Initialize Gemini model
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Configure plot style
            self._setup_plotting()
            
        except Exception as e:
            print(f"Error initializing TitanicAssistant: {e}")
            raise

    def _prepare_data(self):
        """Prepare and clean the dataset with robust error handling."""
        try:
            # Create a working copy
            self.df = self.original_df.copy()
            
            # Handle missing values
            self.df['Age'].fillna(self.df['Age'].median(), inplace=True)
            self.df['Fare'].fillna(self.df['Fare'].median(), inplace=True)
            self.df['Embarked'].fillna('S', inplace=True)  # Most common port
            
            # Create encoded versions but keep originals
            self.df['Sex_encoded'] = self.df['Sex'].map({'male': 0, 'female': 1})
            self.df['Embarked_encoded'] = self.df['Embarked'].map({'C': 0, 'Q': 1, 'S': 2})
            
            # Store mappings for reference
            self.sex_mapping = {'male': 0, 'female': 1}
            self.embarked_mapping = {'C': 0, 'Q': 1, 'S': 2}
            self.sex_mapping_rev = {0: 'male', 1: 'female'}
            self.embarked_mapping_rev = {0: 'C', 1: 'Q', 2: 'S'}
            
            print(f"Dataset loaded successfully: {len(self.df)} passengers")
            
        except Exception as e:
            print(f"Error preparing data: {e}")
            raise

    def _setup_plotting(self):
        """Configure plotting settings."""
        plt.style.use('default')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10

    def handle_query(self, query: str) -> Dict[str, Any]:
        """Handle a user query with improved error handling and code generation."""
        try:
            # Detect if visualization is needed
            viz_keywords = ["plot", "graph", "chart", "show", "visualize", "distribution", "histogram", "scatter"]
            needs_viz = any(keyword in query.lower() for keyword in viz_keywords)
            
            # Get enhanced dataset information
            dataset_info = self._get_dataset_info()
            
            # Generate improved prompt
            prompt = self._generate_prompt(query, needs_viz, dataset_info)
            
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            answer = response.text
            
            # Extract and execute code with better error handling
            code = self._extract_code(answer)
            output, fig, execution_error = self._safe_execute_code(code)
            
            return {
                'answer': answer,
                'output': output,
                'figure': fig,
                'error': execution_error,
                'code': code
            }
            
        except Exception as e:
            return {
                'answer': f"Error processing query: {str(e)}",
                'output': None,
                'figure': None,
                'error': str(e),
                'code': None
            }

    def _get_dataset_info(self) -> str:
        """Generate comprehensive dataset information."""
        buffer = StringIO()
        self.df.info(buf=buffer)
        df_info = buffer.getvalue()
        
        # Enhanced dataset description
        dataset_info = f"""
TITANIC DATASET INFORMATION:
============================

DataFrame Shape: {self.df.shape}
Total Passengers: {len(self.df)}

COLUMN DETAILS:
- PassengerId: Unique identifier (int)
- Survived: Target variable (0=died, 1=survived)
- Pclass: Passenger class (1=1st class, 2=2nd class, 3=3rd class)
- Name: Full passenger name with title (string)
- FirstName: Extracted first name without title (string)
- Sex: Gender ('male' or 'female' - NOT encoded)
- Sex_encoded: Encoded gender (0=male, 1=female)
- Age: Age in years (float, filled missing values with median)
- SibSp: Number of siblings/spouses aboard
- Parch: Number of parents/children aboard
- Ticket: Ticket number (string)
- Fare: Passenger fare (float, filled missing values with median)
- Cabin: Cabin number (string, many missing values)
- Embarked: Port of embarkation ('C'=Cherbourg, 'Q'=Queenstown, 'S'=Southampton)
- Embarked_encoded: Encoded embarkation port (0=C, 1=Q, 2=S)

SURVIVAL STATISTICS:
- Survivors: {self.df['Survived'].sum()} ({self.df['Survived'].mean():.1%})
- Non-survivors: {len(self.df) - self.df['Survived'].sum()} ({1 - self.df['Survived'].mean():.1%})

SAMPLE DATA (first 3 rows):
{self.df.head(3).to_string()}

STATISTICAL SUMMARY:
{self.df.describe()}
"""
        return dataset_info

    def _generate_prompt(self, query: str, needs_viz: bool, dataset_info: str) -> str:
        """Generate an improved prompt for the LLM."""
        
        common_rules = """
CRITICAL RULES:
1. The DataFrame 'df' contains {len(self.df)} real Titanic passengers - DO NOT create sample data
2. Use ORIGINAL column names: 'Sex' (not encoded), 'Embarked' (not encoded) for readability
3. For filtering: df[df['Sex'] == 'male'] or df[df['Embarked'] == 'S']
4. NEVER use df.columns[n] or row[n] - always use column names like df['Age']
5. Handle missing values appropriately (Age and Fare are already filled)
6. Always add proper titles, labels, and legends to plots
7. Use clear variable names and add comments to your code

AVAILABLE LIBRARIES (already imported):
- pandas as pd
- matplotlib.pyplot as plt  
- seaborn as sns
"""

        if needs_viz:
            return f"""{dataset_info}

{common_rules}

VISUALIZATION REQUEST: "{query}"

Create a compelling visualization that answers this question. Your code should:
1. Use the existing 'df' DataFrame directly
2. Create an appropriate plot type (bar, histogram, scatter, box, etc.)
3. Add meaningful titles, axis labels, and legends
4. Use colors effectively to highlight insights
5. Include a brief 2-3 sentence explanation of key findings

Format: Write Python code in ```python``` blocks, followed by your analysis.
"""
        else:
            return f"""{dataset_info}

{common_rules}

ANALYSIS REQUEST: "{query}"

Perform statistical analysis to answer this question. Your code should:
1. Use the existing 'df' DataFrame directly  
2. Calculate relevant statistics, percentages, or comparisons
3. Print results clearly with context
4. Show actual numbers and percentages where relevant
5. Provide insights about what the data reveals

Format: Write Python code in ```python``` blocks, followed by your analysis.
"""

    def _extract_code(self, text: str) -> str:
        """Extract Python code from LLM response."""
        code_blocks = re.findall(r'```python(.*?)```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        return ""

    def _safe_execute_code(self, code: str) -> Tuple[Optional[str], Optional[plt.Figure], Optional[str]]:
        """Execute code with comprehensive error handling."""
        if not code:
            return None, None, "No code to execute"
        
        # Clear any existing plots
        plt.close('all')
        
        # Capture output
        output_lines = []
        execution_error = None
        
        try:
            # Create safe execution environment
            exec_globals = {
                'df': self.df.copy(),  # Work with a copy for safety
                'pd': pd,
                'plt': plt,
                'sns': sns,
                'print': lambda *args, **kwargs: output_lines.append(' '.join(map(str, args)))
            }
            
            # Execute the code
            exec(code, exec_globals)
            
            # Get figure if created
            fig = None
            if plt.get_fignums():
                fig = plt.gcf()
                # Ensure tight layout
                fig.tight_layout()
            
            # Join output
            output = '\n'.join(output_lines) if output_lines else None
            
            return output, fig, None
            
        except Exception as e:
            execution_error = f"Execution Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"Code execution failed: {execution_error}")
            return None, None, execution_error

    def get_dataset_summary(self) -> Dict[str, Any]:
        """Get comprehensive dataset summary for debugging."""
        return {
            'shape': self.df.shape,
            'columns': list(self.df.columns),
            'dtypes': self.df.dtypes.to_dict(),
            'missing_values': self.df.isnull().sum().to_dict(),
            'sample_data': self.df.head().to_dict(),
            'survival_rate': self.df['Survived'].mean(),
            'class_distribution': self.df['Pclass'].value_counts().to_dict(),
            'gender_distribution': self.df['Sex'].value_counts().to_dict()
        }