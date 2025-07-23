import streamlit as st
import streamlit_authenticator as stauth
import bcrypt

def load_authenticator():
    # ✅ Nested access (compatible with Streamlit Secrets)
    usernames = st.secrets["credentials"]["usernames"]
    cookie = st.secrets["cookie"]

    # 🔐 Authenticator instance
    authenticator = stauth.Authenticate(
        {"usernames": dict(usernames)},
        cookie["name"],
        cookie["key"],
        cookie["expiry_days"]
    )

    return authenticator


    # # 🧪 Optional Auth Debug Mode (for dev/testing only)
    # if st.sidebar.checkbox("Enable Auth Debug Mode"):
    #     st.write("Available usernames:", list(usernames.keys()))

    #     selected_user = st.selectbox("Select user to test", usernames.keys())
    #     test_password = st.text_input("Enter raw password to verify", type="password")

    #     if test_password:
    #         hashed_pw = usernames[selected_user]["password"]
    #         match = bcrypt.checkpw(test_password.encode(), hashed_pw.encode())

    #         st.success("✅ Password matches!" if match else "❌ Incorrect password for selected user")

    # return authenticator
