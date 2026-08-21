import streamlit as st

from services.auth.security import (
    hash_password,
    verify_password,
    is_valid_email,
)
from services.persistence.exercise_repository import (
    get_user_by_username_or_email,
    get_user,
    get_user_by_email,
    create_user_with_credentials,
)


def _switch_to(mode: str) -> None:
    st.session_state["auth_mode"] = mode
    st.rerun()


def _render_sign_in() -> None:
    st.markdown("### Welcome back! Please sign in to continue.")

    with st.form("sign_in_form", clear_on_submit=False):
        identifier = st.text_input(
            "Username or Email",
            placeholder="e.g. mahammadafridh or you@example.com",
        )
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button("Sign In", width="stretch")

    if submitted:
        if not identifier or not password:
            st.error("Please enter your username/email and password.")
            return

        user = get_user_by_username_or_email(identifier.strip())

        if user is None or not user["password_hash"]:
            st.error("Invalid username/email or password.")
            return

        if not verify_password(password, user["password_hash"]):
            st.error("Invalid username/email or password.")
            return

        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]
        st.rerun()

    st.markdown("")
    st.caption("Don't have an account yet?")

    if st.button("Create an account", key="go_to_sign_up", width="stretch"):
        _switch_to("sign_up")


def _render_sign_up() -> None:
    st.markdown("### Create your account to get started.")

    with st.form("sign_up_form", clear_on_submit=False):
        username = st.text_input("Username (unique)", placeholder="e.g. mahammadafridh")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        submitted = st.form_submit_button("Create Account", width="stretch")

    if submitted:
        username = (username or "").strip()
        email = (email or "").strip().lower()

        if not username or not email or not password or not confirm_password:
            st.error("Please fill in all fields.")
            return

        if len(username) < 3:
            st.error("Username must be at least 3 characters long.")
            return

        if not is_valid_email(email):
            st.error("Please enter a valid email address.")
            return

        if len(password) < 6:
            st.error("Password must be at least 6 characters long.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        if get_user(username) is not None:
            st.error("That username is already taken.")
            return

        if get_user_by_email(email) is not None:
            st.error("An account with that email already exists.")
            return

        create_user_with_credentials(username, email, hash_password(password))

        st.success("Account created successfully! Please sign in.")
        st.session_state["auth_mode"] = "sign_in"

    st.markdown("")
    st.caption("Already have an account?")

    if st.button("Sign in instead", key="go_to_sign_in", width="stretch"):
        _switch_to("sign_in")


def render_login_wall() -> bool:
    """
    Renders the Sign In / Sign Up screens.
    Returns True once the user is authenticated, False otherwise.
    """
    if st.session_state.get("user_id") is not None:
        return True

    st.title("🏋️‍♂️ AI Real-time GYM Trainer")

    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "sign_in"

    if st.session_state["auth_mode"] == "sign_up":
        _render_sign_up()
    else:
        _render_sign_in()

    return False


def render_logout_button() -> None:
    """Renders a Logout button in the sidebar for the authenticated user."""
    if st.session_state.get("user_id") is None:
        return

    if st.button("Logout", key="logout_button", width="stretch"):
        for key in ("user_id", "username", "auth_mode"):
            st.session_state.pop(key, None)

        st.rerun()
