import os
import json
import re
import sys
import io
import contextlib
import warnings
from pathlib import Path
from typing import Optional, List, Any, Tuple
from PIL import Image
import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from together import Together
from e2b_code_interpreter import Sandbox

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

pattern = re.compile(r"```python\n(.*?)\n```", re.DOTALL)

def code_interpret(e2b_code_interpreter: Sandbox, code: str) -> Optional[List[Any]]:
    with st.spinner('Executing code in E2B sandbox...'):
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exec = e2b_code_interpreter.run_code(code)

        if stderr_capture.getvalue():
            print("[Code Interpreter Warnings/Errors]", file=sys.stderr)
            print(stderr_capture.getvalue(), file=sys.stderr)

        if stdout_capture.getvalue():
            print("[Code Interpreter Output]", file=sys.stdout)
            print(stdout_capture.getvalue(), file=sys.stdout)

        if exec.error:
            print(f"[Code Interpreter ERROR] {exec.error}", file=sys.stderr)
            return None
        return exec.results

def match_code_blocks(llm_response: str) -> str:
    match = pattern.search(llm_response)
    if match:
        code = match.group(1)
        return code
    return ""

def chat_with_llm(e2b_code_interpreter: Sandbox, user_message: str, dataset_path: str) -> Tuple[Optional[List[Any]], str]:
    # Update system prompt to include dataset path information
    system_prompt = f"""You're a Python data scientist and data visualization expert. You are given a dataset at path '{dataset_path}' and also the user's query.
You need to analyze the dataset and answer the user's query with a response and you run Python code to solve them.
IMPORTANT: Always use the dataset path variable '{dataset_path}' in your code when reading the CSV file."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    with st.spinner('Getting response from Together AI LLM model...'):
        client = Together(api_key=st.session_state.together_api_key)
        response = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=messages,
        )

        response_message = response.choices[0].message
        python_code = match_code_blocks(response_message.content)
        
        if python_code:
            code_interpreter_results = code_interpret(e2b_code_interpreter, python_code)
            return code_interpreter_results, response_message.content
        else:
            st.warning(f"Failed to match any Python code in model's response")
            return None, response_message.content

def upload_dataset(code_interpreter: Sandbox, filename: str, file_data: bytes) -> str:
    dataset_path = f"./{Path(filename).name}"
    
    try:
        code_interpreter.files.write(dataset_path, file_data)
        return dataset_path
    except Exception as error:
        st.error(f"Error during file upload: {error}")
        raise error


def apply_theme() -> None:
    """Apply the visual language for the dashboard."""
    st.set_page_config(
        page_title="Vizly | AI Data Visualization",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --ink: #172033;
            --muted: #63708a;
            --teal: #0c8b83;
            --teal-dark: #08635e;
            --coral: #ed765f;
            --surface: #ffffff;
            --line: #e8eaf2;
        }
        .stApp {
            background: linear-gradient(135deg, #f7f8ff 0%, #f9fbff 48%, #f4f9f8 100%);
            color: var(--ink);
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #11182a;
            border-right: 0;
        }
        [data-testid="stSidebar"] * { color: #e7e9f4; }
        [data-testid="stSidebar"] input {
            background: #202a42;
            border-color: #394562;
        }
        [data-testid="stSidebar"] a { color: #bcb1ff; }
        h1, h2, h3, p, label, .stMarkdown { font-family: 'DM Sans', sans-serif; }
        h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
        h1 { letter-spacing: -0.04em; }
        .hero {
            padding: 2.2rem 2.5rem 2rem;
            border-radius: 28px;
            background: radial-gradient(circle at 90% 10%, #59c9c0 0, transparent 35%),
                        linear-gradient(115deg, #12333d 0%, #126c6a 55%, #0c8b83 100%);
            box-shadow: 0 18px 45px rgba(12, 139, 131, .2);
            color: white;
            margin-bottom: 1.5rem;
        }
        .hero h1 { color: white; font-size: 2.8rem; margin: .35rem 0 .5rem; }
        .hero p { color: #e4e0ff; font-size: 1.08rem; max-width: 680px; margin: 0; }
        .eyebrow {
            color: #c4f2ec; font-size: .76rem; font-weight: 700;
            letter-spacing: .14em; text-transform: uppercase;
        }
        .section-title { margin: 1.3rem 0 .2rem; }
        .section-subtitle { color: var(--muted); margin-bottom: 1rem; }
        .metric-card {
            background: var(--surface); border: 1px solid var(--line);
            border-radius: 16px; padding: 1rem 1.1rem;
            box-shadow: 0 8px 20px rgba(34, 42, 70, .05);
        }
        .metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
        .metric-value { color: var(--ink); font-family: 'Space Grotesk'; font-size: 1.45rem; font-weight: 700; margin-top: .25rem; }
        .tip-card {
            background: #e8f7f4; border: 1px solid #c7eae4; border-radius: 14px;
            padding: .9rem 1rem; color: #155d5a; font-size: .9rem;
        }
        .stButton > button {
            background: linear-gradient(100deg, var(--teal-dark), var(--teal));
            color: white; border: 0; border-radius: 10px; font-weight: 700;
            padding: .65rem 1.2rem; box-shadow: 0 8px 16px rgba(12, 139, 131, .18);
        }
        .stButton > button:hover { color: white; border: 0; filter: brightness(1.06); }
        [data-testid="stFileUploader"] {
            background: rgba(255,255,255,.75); border: 1px dashed #9bc9c5;
            border-radius: 16px; padding: .5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">AI-powered data storytelling</div>
            <h1>Turn raw data into clear decisions.</h1>
            <p>Upload a CSV, ask a question in plain English, and let Vizly find the patterns and visualizations that matter.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def apply_data_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply lightweight filters so users can explore before using AI."""
    filtered_df = df.copy()
    categorical_columns = list(df.select_dtypes(include=["object", "category", "bool"]).columns)
    numeric_columns = list(df.select_dtypes(include="number").columns)

    if not categorical_columns and not numeric_columns:
        return filtered_df

    st.markdown("### 🎛️ Filter this dataset")
    filter_columns = st.columns(2)
    if categorical_columns:
        with filter_columns[0]:
            category = st.selectbox("Category field", ["None"] + categorical_columns)
            if category != "None":
                values = sorted(df[category].dropna().astype(str).unique().tolist())
                selected_values = st.multiselect(
                    f"Values in {category}",
                    values,
                    default=values,
                )
                filtered_df = filtered_df[filtered_df[category].astype(str).isin(selected_values)]

    if numeric_columns:
        with filter_columns[1]:
            numeric_field = st.selectbox("Numeric field", ["None"] + numeric_columns)
            if numeric_field != "None" and not filtered_df.empty:
                numeric_values = pd.to_numeric(filtered_df[numeric_field], errors="coerce").dropna()
                if not numeric_values.empty and numeric_values.min() < numeric_values.max():
                    minimum, maximum = st.slider(
                        f"Range for {numeric_field}",
                        float(numeric_values.min()),
                        float(numeric_values.max()),
                        (float(numeric_values.min()), float(numeric_values.max())),
                    )
                    filtered_df = filtered_df[
                        filtered_df[numeric_field].between(minimum, maximum, inclusive="both")
                    ]

    st.caption(f"Showing {len(filtered_df):,} of {len(df):,} rows.")
    return filtered_df


def render_dataset_explorer(df: pd.DataFrame) -> None:
    """Show useful local insights before the user spends an AI request."""
    numeric_columns = list(df.select_dtypes(include="number").columns)
    categorical_columns = list(df.select_dtypes(include=["object", "category", "bool"]).columns)

    st.markdown('<h2 class="section-title">Explore your data</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">A quick visual health check, available instantly and without an API call.</div>',
        unsafe_allow_html=True,
    )
    overview_tab, columns_tab, chart_tab = st.tabs(["✨ Overview", "🔎 Column profile", "📊 Quick chart"])

    with overview_tab:
        overview_columns = st.columns(3)
        with overview_columns[0]:
            render_metric("Complete cells", f"{int(df.notna().sum().sum()):,}")
        with overview_columns[1]:
            render_metric("Unique values", f"{int(df.nunique().sum()):,}")
        with overview_columns[2]:
            render_metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
        if numeric_columns:
            selected_numeric = st.selectbox("Numeric field", numeric_columns, key="overview_numeric")
            st.line_chart(df[selected_numeric].reset_index(drop=True), color="#0c8b83")
        else:
            st.info("Upload a dataset with numeric fields to see a trend preview.")

    with columns_tab:
        profile = pd.DataFrame({
            "Field": df.columns,
            "Type": [str(df[column].dtype) for column in df.columns],
            "Filled": [f"{int(df[column].notna().sum() / len(df) * 100)}%" for column in df.columns],
            "Unique": [int(df[column].nunique()) for column in df.columns],
        })
        st.dataframe(profile, use_container_width=True, hide_index=True)

    with chart_tab:
        if categorical_columns and numeric_columns:
            category = st.selectbox("Group by", categorical_columns, key="chart_category")
            measure = st.selectbox("Measure", numeric_columns, key="chart_measure")
            grouped = (
                df.groupby(category, dropna=False)[measure]
                .mean()
                .sort_values(ascending=False)
                .head(10)
            )
            st.bar_chart(grouped, color="#ed765f")
            st.caption(f"Showing the top 10 {category} groups by average {measure}.")
        elif numeric_columns:
            st.area_chart(df[numeric_columns].head(100), color="#0c8b83")
        else:
            st.info("Add at least one numeric field to create a quick chart.")


def main():
    """Main Streamlit application."""
    apply_theme()
    render_hero()

    # Initialize session state variables
    if 'together_api_key' not in st.session_state:
        st.session_state.together_api_key = ''
    if 'e2b_api_key' not in st.session_state:
        st.session_state.e2b_api_key = ''
    if 'model_name' not in st.session_state:
        st.session_state.model_name = ''

    with st.sidebar:
        st.markdown("## ⚙️ Workspace")
        st.caption("Connect your AI tools to start exploring.")
        st.session_state.together_api_key = st.text_input("Together AI API Key", type="password")
        st.info("Together AI includes free starter credit.")
        st.markdown("[Get a Together AI key ↗](https://api.together.ai/signin)")
        
        st.session_state.e2b_api_key = st.text_input("E2B API Key", type="password")
        st.markdown("[Get an E2B key ↗](https://e2b.dev/docs/legacy/getting-started/api-key)")
        
        model_options = {
            "Meta-Llama 3.1 405B": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "DeepSeek V3": "deepseek-ai/DeepSeek-V3",
            "Qwen 2.5 7B": "Qwen/Qwen2.5-7B-Instruct-Turbo",
            "Meta-Llama 3.3 70B": "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        }
        st.session_state.model_name = st.selectbox(
            "Select Model",
            options=list(model_options.keys()),
            index=0  # Default to first option
        )
        st.session_state.model_name = model_options[st.session_state.model_name]
        st.markdown("---")
        st.caption("Your keys are used only for this session.")

    st.markdown('<h2 class="section-title">1. Start exploring</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Try the included sample dataset instantly, or bring your own CSV.</div>',
        unsafe_allow_html=True,
    )
    data_source = st.radio("Data source", ["✨ Sample dataset", "📁 Upload a CSV"], horizontal=True)
    sample_path = Path(__file__).parent / "input" / "sample_sales.csv"
    uploaded_file = None
    source_filename = sample_path.name

    if data_source == "📁 Upload a CSV":
        uploaded_file = st.file_uploader(
            "Drop a CSV here or browse your files",
            type="csv",
            label_visibility="collapsed",
        )
        if uploaded_file is None:
            st.info("Choose a CSV to continue, or switch back to the sample dataset.")
            return
        source_filename = uploaded_file.name
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv(sample_path)
        st.success("Sample dataset loaded. Use the filters below to explore it.")

    if not df.empty:
        df = apply_data_filters(df)
        if df.empty:
            st.warning("No rows match the selected filters. Adjust the filters to continue.")
            return
        st.markdown(f"### 📄 {source_filename}")
        metric_columns = st.columns(4)
        with metric_columns[0]:
            render_metric("Rows", f"{len(df):,}")
        with metric_columns[1]:
            render_metric("Columns", f"{len(df.columns):,}")
        with metric_columns[2]:
            render_metric("Numeric fields", f"{len(df.select_dtypes(include='number').columns):,}")
        with metric_columns[3]:
            render_metric("Missing values", f"{int(df.isna().sum().sum()):,}")

        with st.expander("Preview your dataset", expanded=True):
            st.dataframe(df.head(8), use_container_width=True, hide_index=True)
            st.caption(f"Showing the first 8 rows of {len(df):,}.")

        render_dataset_explorer(df)
        st.markdown('<h2 class="section-title">2. Ask your question</h2>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Describe the comparison, trend, or outlier you want to understand.</div>', unsafe_allow_html=True)
        st.markdown('<div class="tip-card">✨ Try: “Show the top 5 categories by average cost” or “What trend do you see over time?”</div>', unsafe_allow_html=True)
        query = st.text_area(
            "Question",
            "Can you compare the average cost for two people between different categories?",
            label_visibility="collapsed",
        )
        
        if st.button("✨ Generate insight", use_container_width=True):
            if not st.session_state.together_api_key or not st.session_state.e2b_api_key:
                st.error("Please enter both API keys in the sidebar.")
            else:
                with Sandbox(api_key=st.session_state.e2b_api_key) as code_interpreter:
                    dataset_bytes = df.to_csv(index=False).encode("utf-8")
                    dataset_path = upload_dataset(code_interpreter, source_filename, dataset_bytes)
                    
                    # Pass dataset_path to chat_with_llm
                    code_results, llm_response = chat_with_llm(code_interpreter, query, dataset_path)
                    
                    st.markdown('<h2 class="section-title">Your data story</h2>', unsafe_allow_html=True)
                    st.markdown("### 💡 AI interpretation")
                    st.info(llm_response)
                    
                    if code_results:
                        st.markdown("### 📈 Generated visuals")
                        for result in code_results:
                            if hasattr(result, 'png') and result.png:  # Check if PNG data is available
                                # Decode the base64-encoded PNG data
                                png_data = base64.b64decode(result.png)
                                
                                # Convert PNG data to an image and display it
                                image = Image.open(BytesIO(png_data))
                                st.image(image, caption="Generated visualization", use_container_width=True)
                            elif hasattr(result, 'figure'):  # For matplotlib figures
                                fig = result.figure  # Extract the matplotlib figure
                                st.pyplot(fig)  # Display using st.pyplot
                            elif hasattr(result, 'show'):  # For plotly figures
                                st.plotly_chart(result)
                            elif isinstance(result, (pd.DataFrame, pd.Series)):
                                st.dataframe(result)
                            else:
                                st.write(result)  

if __name__ == "__main__":
    main()
