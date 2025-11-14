import pandas as pd
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    user_query: str
    df: pd.DataFrame
    dqr_report: str
    code_result: str
    error: str
    generated_code: str
    retries: Annotated[int, add]
