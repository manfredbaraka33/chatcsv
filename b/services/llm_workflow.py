# import re
# import io
# import contextlib
# import pandas as pd
# # Add logging import for debugging
# import logging 

# from langgraph.graph import StateGraph, END  # type: ignore
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from config.settings import get_llm, MAX_RETRIES
# from models.agent_state import AgentState

# logger = logging.getLogger(__name__) # Initialize logger

# # ------------------------------------------------
# # 1. RECTIFIED SYSTEM PROMPT (Code Generation Instructions)
# # This includes the persona, delegation, and strict code output rules.
# # ------------------------------------------------

# SYSTEM_PROMPT_TEMPLATE = """
# You are an **Expert Python Data Analyst Agent**. Your professional role in this step is to provide **clean, accurate, and executable Python code** to answer the user's request. **The conversational answer will be generated in a subsequent step.**

# Use the following CSV data context and user query to generate Python code.

# ### 🔑 CRITICAL CODE RULES:
# 1. Your entire response **MUST** consist of nothing but the single Python code block. **Do not include any introductory text, explanation, or conversational filler.**
# 2. The final line of your generated Python code **MUST print the calculated result, summary, or final output** (e.g., print(len(df.columns))) to standard output using the **print()** function.
# 3. **MANDATORY FOR SIZE/COUNT:** If the user asks for the total number of rows or the size of the dataset, you **MUST** use `print(len(df))` to get the current row count. **DO NOT infer the count from the data context preview.**
# 4. For all other counting tasks (e.g., unique values), always use `print(df['column'].nunique())` to ensure a clean numerical output.
# 5. **DATA ACCESS:** The DataFrame is already loaded as the variable `df`. **DO NOT** use `pd.read_csv()`, `open()`, or any other file loading function.

# Data Context:
# {data_context}
# {error_context}

# User Query:
# {user_query}

# The code block MUST start with ```python and end with ```.

# When returning tabular summaries, ALWAYS use Markdown table format like this:

# | Column | Missing Values | Data Type |
# |--------|----------------|------------|
# | age | 0 | int64 |

# Do not use spaces or plain text tables. Always use the Markdown pipe syntax.
# """

# def code_generator_node(state: AgentState) -> dict:
#     llm = get_llm()  # lazy load
#     error_context = ""
#     if state.get('error'):
#         error_context = f"""
#         ### ❌ Previous RUNTIME ERROR:
#         {state['error']}
#         ### 📜 Previous FAILED CODE:
#         {state.get('generated_code', '')}
#         """
#     full_prompt = SYSTEM_PROMPT_TEMPLATE.format(
#         user_query=state['user_query'],
#         data_context=state['dqr_report'],
#         error_context=error_context
#     )

#     response = llm.invoke(full_prompt).content
#     response_content = response.strip()

#     # --- Code Extraction Logic ---
#     match = re.search(r"```python\n(.*?)```", response_content, re.DOTALL)
    
#     if match:
#         # Case 1: Code block found and extracted successfully
#         code = match.group(1).strip()
#     elif response_content:
#         # Case 2: No code block found, but LLM returned non-empty content.
#         # This will be passed as code and likely error out, leading to a retry.
#         code = response_content
#     else:
#         # Case 3: LLM returned empty content.
#         error_message = "LLM failed to return any code or content."
#         logger.warning(f"Agent Warning in code_generator_node: {error_message}")
#         code = f"print('LLM output failure: {error_message}')"

#     # Log the generated code for immediate debugging
#     logger.info(f"Generated Code: {code.strip()[:150]}...")

#     # Ensure we reset the error status for the next execution attempt
#     return {
#         **state, 
#         "generated_code": code, 
#         "error": "", 
#         "retries": state.get("retries", 0) + 1
#     }


# # ------------------------------------------------
# # 2. EXECUTE CODE NODE (Unchanged)
# # ------------------------------------------------

# def execute_code_node(state: AgentState) -> dict:
#     # Use .copy() defensively, but reset_index is fine for state propagation
#     df_clean = state['df'].copy().reset_index(drop=True) 
#     # Use local_env for security and context
#     local_env = {'df': df_clean, 'pd': pd} 
#     output, error = "", ""
#     code = state['generated_code']

#     try:
#         temp_stdout = io.StringIO()
#         with contextlib.redirect_stdout(temp_stdout):
#             # Pass local_env as both global and local scope for simplicity in agent code
#             exec(code, {"__builtins__": __builtins__, "pd": pd}, local_env) 
        
#         # Ensure 'Code executed but produced no explicit output.' is ONLY the fallback.
#         output = temp_stdout.getvalue().strip() 
#         if not output:
#              output = "Code executed but produced no explicit output."
        
#         error = ""
        
#     except Exception as e:
#         error = f"{e.__class__.__name__}: {str(e)}"

#     # Log the result of the code execution 
#     logger.info(f"Execution Output (code_result): {output.strip()[:100]}...")

#     # Return the clean df (in case the code modified it) and the execution result/error
#     return {**state, "df": df_clean, "code_result": output, "error": error}

# # ------------------------------------------------
# # 3. RECTIFIED HUMANIZE NODE (Data Scientist Persona and Concision)
# # ------------------------------------------------

# def humanize_node(state: AgentState) -> dict:
#     llm = get_llm()  # lazy load
    
#     # Prompt is now professional, concise, and references "dataset".
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", 
#          "You are a professional Data Scientist presenting the final result of an analysis to a stakeholder. "
#          "**Be highly concise, direct, and definitive in your answer, providing only the necessary finding.** "
#          "Do not mention the underlying code, execution, or the technical name 'df'. "
#          "Instead, refer to the data or the dataset. "
#          "If the result is numerical (e.g., '45'), frame it in a single, confident sentence (e.g., 'The average revenue for the dataset is $45.00'). "
#          "If the result is a table, present the table clearly with a brief, introductory sentence."),
         
#         ("human", f"Original Query: {state['user_query']}\n\nFinal Code Result:\n{state['code_result']}")
#     ])
    
#     chain = prompt | llm | StrOutputParser()
#     final_answer = chain.invoke(state)
    
#     # Log the final answer content for client-side debugging
#     logger.info(f"Final Humanized Answer: {final_answer.strip()[:100]}...")
    
#     return {**state, "code_result": final_answer}

# # ------------------------------------------------
# # 4. CONDITIONAL & WORKFLOW BUILD (Unchanged, but complete)
# # ------------------------------------------------

# def decide_next_step(state: AgentState):
#     if state.get('error'):
#         if state.get('retries', 0) >= MAX_RETRIES:
#             return END
#         return "generate_code"
#     return "humanize_answer"

# def build_workflow():
#     graph = StateGraph(AgentState)
#     graph.add_node("generate_code", code_generator_node)
#     graph.add_node("execute_code", execute_code_node)
#     graph.add_node("humanize_answer", humanize_node)
#     graph.set_entry_point("generate_code")
#     graph.add_edge("generate_code", "execute_code")
#     graph.add_conditional_edges("execute_code", decide_next_step, {
#         "generate_code": "generate_code",
#         "humanize_answer": "humanize_answer",
#         END: END
#     })
    
#     # Add an edge from the humanize node to the END state
#     graph.add_edge("humanize_answer", END) 
    
#     return graph.compile()



import re
import io
import contextlib
import pandas as pd
# Add logging import for debugging
import logging 

from langgraph.graph import StateGraph, END  # type: ignore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config.settings import get_llm, MAX_RETRIES
from models.agent_state import AgentState

logger = logging.getLogger(__name__) # Initialize logger

# Define a structured error constant for empty data results
EMPTY_DATASET_RESULT = "ERROR: EMPTY_DATASET_RESULT"

# ------------------------------------------------
# 1. RECTIFIED SYSTEM PROMPT (Code Generation Instructions)
# ------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """
You are an **Expert Python Data Analyst Agent**. Your professional role in this step is to provide **clean, accurate, and executable Python code** to answer the user's request. **The conversational answer will be generated in a subsequent step.**

Use the following CSV data context and user query to generate Python code.

### 🔑 CRITICAL CODE RULES:
1. Your entire response **MUST** consist of nothing but the single Python code block. **Do not include any introductory text, explanation, or conversational filler.**
2. The final line of your generated Python code **MUST print the calculated result, summary, or final output** (e.g., print(len(df.columns))) to standard output using the **print()** function.
3. **MANDATORY FOR SIZE/COUNT:** If the user asks for the total number of rows or the size of the dataset, you **MUST** use `print(len(df))` to get the current row count. **DO NOT infer the count from the data context preview.**
4. For all other counting tasks (e.g., unique values), always use `print(df['column'].nunique())` to ensure a clean numerical output.
5. **DATA ACCESS:** The DataFrame is already loaded as the variable `df`. **DO NOT** use `pd.read_csv()`, `open()`, or any other file loading function.

Data Context:
{data_context}
{error_context}

User Query:
{user_query}

The code block MUST start with ```python and end with ```.

When returning tabular summaries, ALWAYS use Markdown table format like this:

| Column | Missing Values | Data Type |
|--------|----------------|------------|
| age | 0 | int64 |

Do not use spaces or plain text tables. Always use the Markdown pipe syntax.
"""

def code_generator_node(state: AgentState) -> dict:
    llm = get_llm()  # lazy load
    error_context = ""
    if state.get('error'):
        error_context = f"""
        ### ❌ Previous RUNTIME ERROR:
        {state['error']}
        ### 📜 Previous FAILED CODE:
        {state.get('generated_code', '')}
        """
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_query=state['user_query'],
        data_context=state['dqr_report'],
        error_context=error_context
    )

    response = llm.invoke(full_prompt).content
    response_content = response.strip()

    # --- Code Extraction Logic ---
    match = re.search(r"```python\n(.*?)```", response_content, re.DOTALL)
    
    if match:
        # Case 1: Code block found and extracted successfully
        code = match.group(1).strip()
    elif response_content:
        # Case 2: No code block found, but LLM returned non-empty content.
        # This will be passed as code and likely error out, leading to a retry.
        code = response_content
    else:
        # Case 3: LLM returned empty content.
        error_message = "LLM failed to return any code or content."
        logger.warning(f"Agent Warning in code_generator_node: {error_message}")
        code = f"print('LLM output failure: {error_message}')"

    # Log the generated code for immediate debugging
    logger.info(f"Generated Code: {code.strip()[:150]}...")

    # Ensure we reset the error status for the next execution attempt
    return {
        **state, 
        "generated_code": code, 
        "error": "", 
        "retries": state.get("retries", 0) + 1
    }


# ------------------------------------------------
# 2. MODIFIED EXECUTE CODE NODE (Handles EMPTY_DATASET_RESULT)
# ------------------------------------------------

def execute_code_node(state: AgentState) -> dict:
    # Use .copy() defensively, but reset_index is fine for state propagation
    df_clean = state['df'].copy().reset_index(drop=True) 
    # Use local_env for security and context
    local_env = {'df': df_clean, 'pd': pd} 
    output, error = "", ""
    code = state['generated_code']

    try:
        temp_stdout = io.StringIO()
        with contextlib.redirect_stdout(temp_stdout):
            # Pass local_env as both global and local scope for simplicity in agent code
            exec(code, {"__builtins__": __builtins__, "pd": pd}, local_env) 
        
        # Capture the output and check if it's empty
        output = temp_stdout.getvalue().strip() 
        
        # CRITICAL FIX: If output is empty, it means filtering yielded no rows.
        if not output:
            # We don't know *why* it was empty (could be user's fault), 
            # so we set a flag for the humanize_node to explain.
            output = EMPTY_DATASET_RESULT
        
        error = ""
        
    except Exception as e:
        error = f"{e.__class__.__name__}: {str(e)}"

    # Log the result of the code execution 
    logger.info(f"Execution Output (code_result): {output.strip()[:100]}...")

    # Return the clean df (in case the code modified it) and the execution result/error
    return {**state, "df": df_clean, "code_result": output, "error": error}

# ------------------------------------------------
# 3. MODIFIED HUMANIZE NODE (Handles EMPTY_DATASET_RESULT)
# ------------------------------------------------

def humanize_node(state: AgentState) -> dict:
    llm = get_llm()  # lazy load
    code_result = state['code_result']
    original_query = state['user_query']

    if code_result == EMPTY_DATASET_RESULT:
        # Case 1: Filter returned an empty dataset. Generate a targeted error message.
        logger.info("Handling EMPTY_DATASET_RESULT.")
        system_prompt_text = (
            "You are a professional Data Scientist. The previous code successfully executed but "
            "the filtering operation returned an empty dataset (zero rows) for the user's query. "
            "Generate a single, concise, and definitive sentence explaining this to the user. "
            "Example: 'The dataset does not contain any information for [specific filter term], resulting in no data for the analysis.'"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            ("human", f"The query was: {original_query}")
        ])
        
    else:
        # Case 2: Normal execution. Humanize the result using the standard persona.
        logger.info("Handling successful code result.")
        system_prompt_text = (
            "You are a professional Data Scientist presenting the final result of an analysis to a stakeholder. "
            "**Be highly concise, direct, and definitive in your answer, providing only the necessary finding.** "
            "Do not mention the underlying code, execution, or the technical name 'df'. "
            "Instead, refer to the data or the dataset. "
            "If the result is numerical (e.g., '45'), frame it in a single, confident sentence (e.g., 'The average revenue for the dataset is $45.00'). "
            "If the result is a table, present the table clearly with a brief, introductory sentence."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            ("human", f"Original Query: {original_query}\n\nFinal Code Result:\n{code_result}")
        ])
    
    chain = prompt | llm | StrOutputParser()
    final_answer = chain.invoke(state)
    
    # Log the final answer content for client-side debugging
    logger.info(f"Final Humanized Answer: {final_answer.strip()[:100]}...")
    
    return {**state, "code_result": final_answer}

# ------------------------------------------------
# 4. CONDITIONAL & WORKFLOW BUILD (Unchanged)
# ------------------------------------------------

def decide_next_step(state: AgentState):
    if state.get('error'):
        # Check if the error is the empty dataset flag, which should proceed to humanize
        if state['code_result'] == EMPTY_DATASET_RESULT:
             return "humanize_answer"
        
        # Otherwise, if it's a true Python error, retry code generation
        if state.get('retries', 0) >= MAX_RETRIES:
            return END
        return "generate_code"
    
    # Normal path
    return "humanize_answer"

def build_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("generate_code", code_generator_node)
    graph.add_node("execute_code", execute_code_node)
    graph.add_node("humanize_answer", humanize_node)
    graph.set_entry_point("generate_code")
    graph.add_edge("generate_code", "execute_code")
    graph.add_conditional_edges("execute_code", decide_next_step, {
        "generate_code": "generate_code",
        "humanize_answer": "humanize_answer",
        END: END
    })
    
    # Add an edge from the humanize node to the END state
    graph.add_edge("humanize_answer", END) 
    
    return graph.compile()