import streamlit as st
import os
import time
import pandas as pd
from pathlib import Path

from services.auth.login_wall import render_login_wall, render_logout_button
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import (
    load_css,
    inject_local_font,
    inject_webrtc_styles
)
from services.persistence.exercise_repository import (
    init_db,
    get_users_exercises
)
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import (
    VoicePipeline,
    autoplay_audio
)


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    if not api_key:
        try:
            if "GROQ_API_KEY" in st.secrets:
                api_key = str(st.secrets["GROQ_API_KEY"]).strip()
        except Exception:
            pass

    if not api_key:
        return None

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        print("Groq client initialization error:", e)
        return None


def initialize_voice_pipeline():
    try:
        groq_client = get_groq_client()

        if groq_client is None:
            return None, "GROQ_API_KEY is missing."

        llm_coach = LLMCoach(groq_client)
        tts = TextToSpeech(groq_client)
        pipeline = VoicePipeline(llm_coach, tts)

        return pipeline, None

    except Exception as e:
        print("Voice pipeline initialization error:", e)
        return None, str(e)


def main():

    base_dir = Path(__file__).resolve().parent

    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )

    load_css(
        str(base_dir / "static" / "style.css")
    )

    inject_local_font(
        str(base_dir / "static" / "AdobeClean.otf"),
        "AdobeClean"
    )

    init_db()

    if not render_login_wall():
        return

    initial_session_defaults()

    # ---------------------------------------------------------
    # INITIALIZE VOICE PIPELINE
    # ---------------------------------------------------------

    if "voice_pipeline" not in st.session_state:

        pipeline, pipeline_error = initialize_voice_pipeline()

        st.session_state.voice_pipeline = pipeline
        st.session_state.voice_pipeline_error = pipeline_error

    if st.session_state.get("voice_pipeline") is None:

        with st.sidebar:

            st.warning(
                "🤖 AI Coach is currently unavailable."
            )

            st.caption(
                "Check your GROQ_API_KEY in Streamlit Secrets."
            )

    workout_started = st.session_state.get(
        "workout_started",
        False
    )

    # =========================================================
    # SIDEBAR
    # =========================================================

    with st.sidebar:

        st.title("🏋️‍♂️ AI Coach")

        if st.session_state.get("username"):

            st.caption(
                f"👤 Login as {st.session_state.username}"
            )

            render_logout_button()

        st.divider()

        st.subheader("Workout Plan")

        # -----------------------------------------------------
        # BEFORE WORKOUT
        # -----------------------------------------------------

        if not workout_started:

            plan_exercise = st.selectbox(
                "Exercise",
                options=EXERCISE_OPTIONS,
                key="plan_exercise"
            )

            plan_sets = st.number_input(
                "Sets",
                min_value=0,
                max_value=50,
                key="plan_sets",
                step=1
            )

            plan_reps = st.number_input(
                "Reps per Set",
                min_value=0,
                max_value=50,
                key="plan_reps",
                step=1
            )

            st.markdown("")

            start_session_button = st.button(
                "Start Workout",
                width="stretch",
                key="start_session_button"
            )

            if start_session_button:

                st.session_state.exercise_type = plan_exercise

                st.session_state.target_sets = int(
                    plan_sets
                )

                st.session_state.reps_per_set = int(
                    plan_reps
                )

                st.session_state.reps = 0

                st.session_state.workout_started = True

                st.session_state.set_cycle_started_at = (
                    time.time()
                )

                st.session_state.last_saved_sets_completed = 0

                # ---------------------------------------------
                # AI WORKOUT START MESSAGE
                # ---------------------------------------------

                if st.session_state.get("voice_pipeline"):

                    try:

                        result = (
                            st.session_state.voice_pipeline
                            .process_event(
                                event="workout_started",
                                exercise=plan_exercise,
                                metrics={}
                            )
                        )

                        if result:

                            st.session_state.audio_to_play = (
                                result[0]
                            )

                            st.session_state.coach_feedback = (
                                result[1]
                            )

                    except Exception as e:

                        print(
                            "Groq workout_started error:",
                            e
                        )

                        st.session_state.coach_feedback = (
                            "Workout started! "
                            "AI coaching is temporarily unavailable."
                        )

                else:

                    st.session_state.coach_feedback = (
                        "Workout started! "
                        "AI coaching is currently unavailable."
                    )

                st.session_state.last_notified_sets_completed = 0

                st.session_state.last_notified_workout_complete = False

                st.rerun()

        # -----------------------------------------------------
        # DURING WORKOUT
        # -----------------------------------------------------

        else:

            exercise = st.session_state.get(
                "exercise_type"
            )

            sets = st.session_state.get(
                "target_sets"
            )

            reps = st.session_state.get(
                "reps_per_set"
            )

            st.info(
                f"**{exercise}** -- {sets} Sets / {reps} Reps"
            )

            end_session_button = st.button(
                "End Workout",
                key="end_session_button",
                width="stretch"
            )

            if end_session_button:

                st.session_state.workout_started = False

                # ---------------------------------------------
                # AI WORKOUT COMPLETED MESSAGE
                # ---------------------------------------------

                if st.session_state.get("voice_pipeline"):

                    try:

                        result = (
                            st.session_state.voice_pipeline
                            .process_event(
                                event="workout_completed",
                                exercise=exercise,
                                metrics={}
                            )
                        )

                        if result:

                            st.session_state.audio_to_play = (
                                result[0]
                            )

                            st.session_state.coach_feedback = (
                                result[1]
                            )

                    except Exception as e:

                        print(
                            "Groq workout_completed error:",
                            e
                        )

                        st.session_state.coach_feedback = (
                            "Workout completed! "
                            "AI coaching is temporarily unavailable."
                        )

                st.rerun()

        # =====================================================
        # PROGRESS
        # =====================================================

        if workout_started:

            st.divider()

            exercise = st.session_state.get(
                "exercise_type"
            )

            total_reps = st.session_state.get(
                "reps",
                0
            )

            current_set_reps = st.session_state.get(
                "current_set_reps",
                0
            )

            reps_per_set = st.session_state.get(
                "reps_per_set",
                0
            )

            sets_completed = st.session_state.get(
                "sets_completed",
                0
            )

            target_sets = st.session_state.get(
                "target_sets",
                0
            )

            st.subheader("Progress")

            st.metric(
                "Total Reps",
                f"{total_reps}"
            )

            st.metric(
                "Current Set Reps",
                f"{current_set_reps} / {reps_per_set}"
            )

            st.metric(
                "Sets Completed",
                f"{sets_completed} / {target_sets}"
            )

            st.divider()

            # =================================================
            # SQUATS
            # =================================================

            if exercise == "Squats":

                st.subheader("Squat Metrics")

                st.metric(
                    "Knee Angle",
                    f"{st.session_state.get('knee_angle', 0)}°"
                )

                st.metric(
                    "Back Angle",
                    f"{st.session_state.get('back_angle', 0)}°"
                )

                st.metric(
                    "Depth Status",
                    st.session_state.get(
                        "depth_status",
                        "N/A"
                    )
                )

            # =================================================
            # PUSH-UPS
            # =================================================

            elif exercise == "Push-ups":

                st.subheader("Push-up Metrics")

                st.metric(
                    "Elbow Angle",
                    f"{st.session_state.get('elbow_angle', 0)}°"
                )

                st.metric(
                    "Body Alignment",
                    st.session_state.get(
                        "body_alignment",
                        "N/A"
                    )
                )

                st.metric(
                    "Hip Position",
                    st.session_state.get(
                        "hip_status",
                        "N/A"
                    )
                )

            # =================================================
            # BICEPS CURLS
            # =================================================

            elif exercise == "Biceps Curls (Dumbbell)":

                st.subheader("Curl Metrics")

                st.metric(
                    "Elbow Angle",
                    f"{st.session_state.get('elbow_angle', 0)}°"
                )

                st.metric(
                    "Shoulder Stability",
                    st.session_state.get(
                        "shoulder_status",
                        "N/A"
                    )
                )

                st.metric(
                    "Swing Detection",
                    st.session_state.get(
                        "swing_status",
                        "N/A"
                    )
                )

            # =================================================
            # SHOULDER PRESS
            # =================================================

            elif exercise == "Shoulder Press":

                st.subheader("Shoulder Press Metrics")

                st.metric(
                    "Elbow Angle",
                    f"{st.session_state.get('elbow_angle', 0)}°"
                )

                st.metric(
                    "Arm Extension",
                    st.session_state.get(
                        "extension_status",
                        "N/A"
                    )
                )

                st.metric(
                    "Back Arch",
                    st.session_state.get(
                        "back_arch_status",
                        "N/A"
                    )
                )

            # =================================================
            # LUNGES
            # =================================================

            elif exercise == "Lunges":

                st.subheader("Lunge Metrics")

                st.metric(
                    "Front Knee Angle",
                    f"{st.session_state.get('front_knee_angle', 0)}°"
                )

                st.metric(
                    "Torso Angle",
                    f"{st.session_state.get('torso_angle', 0)}°"
                )

                st.metric(
                    "Balance Status",
                    st.session_state.get(
                        "balance_status",
                        "N/A"
                    )
                )

    # =========================================================
    # MAIN PAGE
    # =========================================================

    st.title("AI Real-time GYM Coach")

    st.markdown(
        "#### Real-time pose detection with proactive AI voice coaching"
    )

    # =========================================================
    # AUDIO
    # =========================================================

    if st.session_state.get("audio_to_play"):

        try:

            autoplay_audio(
                st.session_state.audio_to_play
            )

        except Exception as e:

            print(
                "Audio playback error:",
                e
            )

    # =========================================================
    # COACH FEEDBACK
    # =========================================================

    if st.session_state.get("coach_feedback"):

        st.markdown("")

        st.success(
            f"🤖 **Coach:** "
            f"{st.session_state.coach_feedback}"
        )

    # =========================================================
    # CAMERA / WEBRTC
    # =========================================================

    if not workout_started:

        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
                margin-bottom: 32px;
            ">

                <h2 style="color:#ccc; margin-bottom:8px;">
                    👈 Set your workout plan
                </h2>

                <p style="font-size:1.05rem;">

                    Choose your exercise, sets and reps in the sidebar,

                    <br>

                    then click <strong>Start Workout</strong>
                    to activate the camera and AI coach.

                </p>

            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        # -----------------------------------------------------
        # WEBRTC CONFIGURATION
        # -----------------------------------------------------
        #
        # STUN helps establish the public network address.
        #
        # TURN is optional. If you add TURN credentials to
        # Streamlit Secrets, they will automatically be used.
        #
        # IMPORTANT:
        # We do NOT continuously call st.rerun() while WebRTC
        # is playing. Continuous reruns can destroy and recreate
        # the WebRTC transport and cause aioice/STUN errors.
        # -----------------------------------------------------

        rtc_configuration = {

            "iceServers": [

                {
                    "urls": [
                        "stun:stun.l.google.com:19302"
                    ]
                }

            ]

        }

        # -----------------------------------------------------
        # OPTIONAL TURN SERVER
        # -----------------------------------------------------

        try:

            turn_url = str(
                st.secrets.get(
                    "TURN_URL",
                    ""
                )
            ).strip()

            turn_username = str(
                st.secrets.get(
                    "TURN_USERNAME",
                    ""
                )
            ).strip()

            turn_credential = str(
                st.secrets.get(
                    "TURN_CREDENTIAL",
                    ""
                )
            ).strip()

            if (
                turn_url
                and turn_username
                and turn_credential
            ):

                rtc_configuration["iceServers"].append(
                    {
                        "urls": [turn_url],
                        "username": turn_username,
                        "credential": turn_credential
                    }
                )

        except Exception:

            pass

        # -----------------------------------------------------
        # START WEBRTC
        # -----------------------------------------------------

        context = webrtc_streamer(

            key="exercise-analysis",

            mode=WebRtcMode.SENDRECV,

            video_processor_factory=VideoProcessorClass,

            rtc_configuration=rtc_configuration,

            media_stream_constraints={
                "video": True,
                "audio": False
            },

            async_processing=True
        )

        # -----------------------------------------------------
        # SYNC METRICS
        # -----------------------------------------------------

        sync_metrics_update(context)

        # IMPORTANT:
        # DO NOT DO THIS:
        #
        # if context.state.playing:
        #     time.sleep(0.25)
        #     st.rerun()
        #
        # It can repeatedly destroy/recreate WebRTC and cause
        # connection timeout / aioice transport errors.

        inject_webrtc_styles()

    # =========================================================
    # WORKOUT HISTORY
    # =========================================================

    st.divider()

    st.markdown(
        "#### Workout History"
    )

    user_id = st.session_state.get(
        "user_id",
        0
    )

    if isinstance(user_id, int):

        try:

            history_rows = get_users_exercises(
                user_id
            )

            arr = [

                {
                    "Exercise": row["exercise_name"],
                    "Reps": row["reps"],
                    "Sets": row["sets"],
                    "Time (sec)": row["time"],
                    "Date": row["created_at"]
                }

                for row in history_rows

            ]

            df = pd.DataFrame(arr)

            if not df.empty:

                df["Date"] = pd.to_datetime(
                    df["Date"]
                ).dt.date

                agg_df = (

                    df

                    .groupby(
                        [
                            "Exercise",
                            "Date"
                        ]
                    )

                    .agg(
                        {
                            "Reps": "sum",
                            "Sets": "sum",
                            "Time (sec)": "sum"
                        }
                    )

                    .reset_index()

                )

                agg_df.index += 1

                st.table(
                    agg_df,
                    border="horizontal"
                )

            else:

                st.info(
                    "No workout history found."
                )

        except Exception as e:

            print(
                "Workout history error:",
                e
            )

            st.info(
                "Unable to load workout history."
            )


if __name__ == "__main__":
    main()