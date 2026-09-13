# Vizly — AI Data Visualization

Turn a CSV into a clear data story. Vizly is a Streamlit app that interprets
natural-language questions and generates useful analyses and visualizations
with Together AI and E2B.

## How to Run

Follow the steps below to set up and run the application:
- Before anything else, Please get a free Together AI API Key here: https://api.together.ai/signin
- Get a free E2B API Key here: https://e2b.dev/ ; https://e2b.dev/docs/legacy/getting-started/api-key

1. **Clone the repository**
   ```bash
   git clone https://github.com/Charan-Hari/Data-Visualitzation-AI.git 
   cd Data-Visualitzation-AI
   ```
2. **Install the dependencies**
    ```bash
    pip install streamlit pandas pillow together e2b-code-interpreter
    ```
3. **Run the Streamlit app**
    ```bash
    streamlit run agent-data-visual.py
    ```

4. **Add your API keys**

   Enter your Together AI and E2B keys in the app sidebar. Keys are kept in
   Streamlit session state and are not written to the repository.

## What you can ask

- “Show the top five categories by average revenue.”
- “Find trends over time and explain the biggest change.”
- “Compare these groups and recommend the best visualization.”
