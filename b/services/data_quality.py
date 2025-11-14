import pandas as pd
import io

def generate_dqr_and_context(df: pd.DataFrame) -> tuple[str, str]:
    buffer = io.StringIO()
    df.info(verbose=True, buf=buffer, memory_usage=False)
    info_str = buffer.getvalue()
    
    # We are explicitly REMOVING the df.head(10) markdown table from the context 
    # to eliminate the visual cue that was confusing the LLM into thinking the dataset 
    # only contained 10 rows, despite the correct count being in the summary.

    dqr_list = []
    df_len = len(df) # <-- The correct total row count
    numeric_threshold = 0.5

    # DQR Logic 
    for col in df.columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            # Report nulls with respect to the total length (df_len)
            dqr_list.append(f"Column '{col}' has {null_count} null/NaN values (out of {df_len} rows).")

        if df[col].dtype == "object":
            numeric_convertible_count = pd.to_numeric(df[col], errors="coerce").notna().sum()
            numeric_ratio = numeric_convertible_count / df_len
            if numeric_ratio > numeric_threshold and col not in ["Name", "Region"]:
                dqr_list.append(
                    f"Column '{col}' is object but looks numeric; consider conversion."
                )

            datetime_convertible_count = pd.to_datetime(df[col], errors="coerce").notna().sum()
            if datetime_convertible_count == df_len and col not in ["Name", "Region"]:
                dqr_list.append(f"Column '{col}' seems to be a datetime column.")

    DQR = "\n".join(sorted(set(dqr_list))) or "Data appears clean."

    # FIX: The DATA_CONTEXT now only includes the mandatory, accurate information.
    DATA_CONTEXT = f"""
### 📊 Dataset Summary
The entire DataFrame 'df' contains **{df_len} rows** and **{len(df.columns)} columns**.

### 🚩 Data Info (Column Types and Non-Null Counts)
{info_str}

### 📈 Data Quality Report (DQR)
{DQR}
"""
    return DQR, DATA_CONTEXT