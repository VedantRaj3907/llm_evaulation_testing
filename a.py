import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
from langchain_core.prompts import MessagesPlaceholder
import threading
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
from collections import deque
from db import append_message, get_history
import concurrent.futures

load_dotenv()

MAX_HISTORY_LENGTH = 5

# def set_column_style():
#     column_height = 400  # Set the height of the columns in pixels

#     # Correct implementation of an f-string for CSS
#     column_style = f"""
#     <style>
#     /* This targets the outer block container for columns in Streamlit */
#     .block-container>div {{
#         height: {column_height}px;
#         overflow-y: auto;
#     }}

#     /* Adding this to ensure that the entire block is scrollable if needed */
#     .stBlock {{
#         height: 100%;
#         overflow-y: auto;
#     }}
#     </style>
#     """
#     st.markdown(column_style, unsafe_allow_html=True)

st.set_page_config("LLM TEST")
# set_column_style() 
MODEL_CHOICES = ['gpt-3.5-turbo', 'gpt-4-turbo']

selected_models = st.multiselect("Select models:", MODEL_CHOICES, default=MODEL_CHOICES)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = {model: deque(maxlen=MAX_HISTORY_LENGTH) for model in MODEL_CHOICES}


def call_chain(ctx, model_name, prompt):
    add_script_run_ctx(threading.current_thread(), ctx)
    try:
        if 'opus' in model_name:  # This distinguishes Claude models
            llm = ChatAnthropic(temperature=0, model_name=model_name)
        else:
            llm = ChatOpenAI(model=model_name, temperature=0, streaming=True, max_tokens=150)

        # Use model specific history
        input = ChatPromptTemplate.from_messages(
            [
                ("system", "helpful assistant"),
                MessagesPlaceholder(variable_name='chat_history'),
                ("human", "{input}")
            ]
        )
        chat_history_for_model = get_history(model_name)

        chain = input | llm
        response_content = ""  # Initialize to accumulate streamed response
        for i in chain.stream({'input': prompt, 'chat_history': chat_history_for_model}):
            response_content += i.content  # Accumulate response
            yield i.content
        # Append the complete response to the model's chat history only after streaming ends
        # st.session_state.chat_history[model_name].append(f"AI ({model_name}): {response_content}")
        append_message(model_name, f"AI ({model_name}): {response_content}", 'AI')
    except Exception as e:
        yield f"Error: {str(e)}"


def threading_output(prompt):
    ctx = get_script_run_ctx()
    cols = st.columns(len(selected_models)) if len(selected_models) > 1 else [st.container()]  # Using container if only one model is selected

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_models)) as executor:
        future_to_col = {}  # Map futures to columns for result handling

        for i, model in enumerate(selected_models):
            generator = call_chain(ctx, model, prompt)
            # Submit task to executor
            future = executor.submit(give_output, ctx, generator, cols[i], model)
            future_to_col[future] = cols[i]
        
        # Handle completed futures
        for future in concurrent.futures.as_completed(future_to_col):
            col = future_to_col[future]
            try:
                future.result()  # We are just calling result to trigger exception handling if any
            except Exception as exc:
                col.error(f'Generator raised an exception: {exc}')
            except BaseException as exc:  # BaseException to capture other potential system-level exceptions
                col.error(f'Unhandled exception in the generator: {exc}')

def give_output(ctx, generator, col, model_name):
    add_script_run_ctx(threading.current_thread(), ctx)

    chat_history_for_model = get_history(model_name)
    for message in chat_history_for_model:
        if "USER" in message:
            with col.chat_message("Human"):
                col.markdown(f"<div style='text-align: left; border: 1px solid gray; padding: 10px; border-radius: 5px; color:red'>{message}</div>", unsafe_allow_html=True)
        else:
            with col.chat_message("AI"):

                col.markdown(f"<div style='text-align: left; border: 1px solid gray; padding: 10px; border-radius: 5px;color:yellow'>{message}</div>", unsafe_allow_html=True)
    
    with col.chat_message("AI"):
        col.write(generator)

user_prompt = st.chat_input("Write a question")

if user_prompt:
    # Store user input into each model's history
    for model in selected_models:
        # st.session_state.chat_history[model].append(f"USER: - {user_prompt}")
        append_message(model, f"USER: - {user_prompt}", 'USER')
    threading_output(user_prompt)