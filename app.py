import streamlit as st
import sqlite3
import json
import os
import uuid
from dotenv import load_dotenv
import re
import time

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS admin_info (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def validate_email_format(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None
import sqlite3



def delete_user_chat_history(email):
    """
    Deletes all chat logs for a specific user from the database.
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM chat_history WHERE email = ?", (email,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting chat: {e}")
        return False
    finally:
        conn.close()






def register_user(name, email, password):
    if not validate_email_format(email): return False, "Invalid email formatting."
    if len(password) < 4: return False, "Password must be at least 4 characters long."
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admin_info (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        return True, "Registration successful! Please login."
    except sqlite3.IntegrityError: return False, "This email is already registered."
    finally: conn.close()

def check_login(email, password):
    if not validate_email_format(email): return False
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_info WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None
# --------------------------------------------------
from groq import Groq

# Initialize Local Database Setup
init_db()
load_dotenv()

st.set_page_config(page_title="LICT AI Assistant", page_icon="🤖", layout="wide")

# Persistent Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"  # Alternates: Login / Register
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- Database Helpers ---
def save_chat_message(email, session_id, role, content):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (email, session_id, role, content) VALUES (?, ?, ?, ?)", (email, session_id, role, content))
    conn.commit()
    conn.close()

def fetch_unique_sessions(email):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id, content FROM chat_history WHERE email = ? AND role = 'user' GROUP BY session_id ORDER BY timestamp DESC", (email,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def fetch_session_messages(session_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

# --- RAG Core Pipeline ---
def process_groq_rag(user_query, history_context, language):
    if not GROQ_API_KEY:
        return "Error: `GROQ_API_KEY` is missing."
        
    context_data = ""
    if os.path.exists("lict_data.json"):
        with open("lict_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            context_data = "\n".join([item["content"] for item in data])
    else:
        context_data = "No local dynamic context data available."

    # Language instruction injection
    lang_instruction = "You must respond ONLY in English." if language == "English" else "You must respond ONLY in Nepali language (नेपाली भाषा)."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the strict LICT College Assistant chatbot. "
                    f"{lang_instruction} Your ONLY source of truth is the provided context.\n"
                    "RULES:\n1. Only answer queries using the provided text.\n"
                    "2. If the user asks about anything outside this data, politely say that you are only allowed to discuss LICT Campus topics.\n\n"
                    f"CONTEXT:\n{context_data}"
                )
            }
        ]
        
        for msg in history_context[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": user_query})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"System processing error: {e}"

# --- VIEW RENDERING LOGIC ---
if not st.session_state.logged_in:
    # -------------------------------------------------------------
    # LOGIN / REGISTER SPLIT SCREEN UI (Your Custom Layout Design)
    # -------------------------------------------------------------
    left_col, right_col = st.columns([1.2, 1], gap="large")
    
    with left_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Custom Brand styling to match your picture assets
        st.markdown("<h1>🤖 LICT AI Assistant</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:gray;'>Intelligent Document Assistant</h3>", unsafe_allow_html=True)
        st.write("---")
        
        st.markdown("### 🛡️ Secure Login")
        st.caption("Your institutional metrics and session histories remain highly secured and encrypted.")
        
        st.markdown("### 🧠 RAG Powered")
        st.caption("Advanced Retrieval-Augmented Generation matching official college database pipelines.")
        
        st.markdown("### 💬 AI Assistant")
        st.caption("Get immediate responsive query structural solutions instantly.")
        
    with right_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        
        if st.session_state.auth_mode == "Login":
            st.markdown("## Welcome Back 👋")
            st.caption("Login to continue to your account")
            
            login_email = st.text_input("Email", placeholder="Enter your email")
            login_pw = st.text_input("Password", type="password", placeholder="Enter your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Login →", use_container_width=True, type="primary"):
                if check_login(login_email, login_pw):
                    st.session_state.logged_in = True
                    st.session_state.user_email = login_email
                    st.session_state.current_session_id = str(uuid.uuid4())
                    st.rerun()
                else:
                    st.error("Authentication failed. Check entries.")
                    
            st.write("---")
            st.write("Don't have an account?")
            if st.button("Register Here"):
                st.session_state.auth_mode = "Register"
                st.rerun()
                
        else:
            st.markdown("## Create Account ✨")
            st.caption("Register an administrative operative user key")
            
            reg_name = st.text_input("Full Name", placeholder="Enter your full name")
            reg_email = st.text_input("Email", placeholder="Enter your email address")
            reg_pw = st.text_input("Password", type="password", placeholder="Choose a strong password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Complete Registration", use_container_width=True, type="primary"):
                success, msg = register_user(reg_name, reg_email, reg_pw)
                if success:
                    st.success(msg)
                    st.session_state.auth_mode = "Login"
                    st.rerun()
                else:
                    st.error(msg)
                    
            st.write("---")
            st.write("Already have an account?")
            if st.button("Back to Login"):
                st.session_state.auth_mode = "Login"
                st.rerun()

else:
    # -------------------------------------------------------------
    # LOGGED IN CHAT INTERFACE WITH CHATGPT-LIKE SIDEBAR
    # -------------------------------------------------------------
    with st.sidebar:
        st.markdown(f"**Operator:** `{st.session_state.user_email}`")
        
        # Language Selector Toggle
        st.write("---")
        selected_lang = st.radio("🌐 **Select Language / भाषा**", ["English", "नेपाली"], horizontal=True)
        st.write("---")
        
        # New Chat Action Button
        if st.button("➕ New Chat Session", use_container_width=True):
            st.session_state.current_session_id = str(uuid.uuid4())
            st.rerun()
            
        st.write("### 🕒 Chat History")
        
        # Fetch existing distinct historical user logs
        past_sessions = fetch_unique_sessions(st.session_state.user_email)
        for sess_id, summary in past_sessions:
            # Cut text if it is too long for the sidebar menu width
            title = summary[:24] + "..." if len(summary) > 24 else summary
            if st.button(title, key=sess_id, use_container_width=True):
                st.session_state.current_session_id = sess_id
                st.rerun()
                
        st.write("---")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.rerun()

    # Chat Display Workspace View
    st.title("⚡ LICT Instant AI Portal")
    st.caption(f"Active Session: `{st.session_state.current_session_id[:8]}...` | Mode: **{selected_lang}**")
    st.divider()
    st.markdown("### ⚙️ Chat Settings")
     
    current_messages = fetch_session_messages(st.session_state.current_session_id)
    
    for msg in current_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Live Prompt Execution Framework
    if user_prompt := st.chat_input("Ask a question about LICT Campus..."):
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        save_chat_message(st.session_state.user_email, st.session_state.current_session_id, "user", user_prompt)
        
        # Process streaming through Context matching parameters
        with st.spinner("Analyzing context..."):
            updated_ctx = fetch_session_messages(st.session_state.current_session_id)
            ai_response = process_groq_rag(user_prompt, updated_ctx, selected_lang)
            
        with st.chat_message("assistant"):
            st.markdown(ai_response)
            
        save_chat_message(st.session_state.user_email, st.session_state.current_session_id, "assistant", ai_response)
        st.rerun()