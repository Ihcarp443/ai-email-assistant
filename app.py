import streamlit as st
import requests
import json

st.set_page_config(
    page_title="AI Email Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

FASTAPI_URL = "http://127.0.0.1:8000"

if "email_data" not in st.session_state:
    st.session_state.email_data = None
if "meet_link" not in st.session_state:
    st.session_state.meet_link = None
if "reply_status" not in st.session_state:
    st.session_state.reply_status = None
if "email_history" not in st.session_state:
    st.session_state.email_history = []

st.title("AI Email Assistant")
st.caption("Automated ingestion, parsing, scheduling, and drafting pipeline.")

hist_res = requests.get(
    f"{FASTAPI_URL}/emails"
)

if hist_res.status_code == 200:
    st.session_state.email_history = (
        hist_res.json()["emails"]
    )


with st.sidebar:
    st.header("Processed Emails")

    for mail in st.session_state.email_history:

        if st.button(
            mail["subject"][:30]+"...",
            key=mail["thread_id"]
        ):

            detail_res = requests.get(
                f"{FASTAPI_URL}/emails/{mail['thread_id']}"
            )

            if detail_res.status_code == 200:

                st.session_state.email_data = (
                    detail_res.json()["email"]
                )

            actions_res = requests.get(
                f"{FASTAPI_URL}/emails/{mail['thread_id']}/actions"
            )

            if actions_res.status_code == 200:

                st.write(
                    actions_res.json()["actions"]
                )
                actions = actions_res.json()["actions"]

                st.session_state.meet_link = None
                st.session_state.reply_status = "Not Sent"

                for action in actions:

                    if action["action_type"] == "meeting_scheduled":
                        st.session_state.meet_link = action["action_value"]

                    elif action["action_type"] == "reply_sent":
                        st.session_state.reply_status = "Sent"

                # st.write(st.session_state.email_data)
st.markdown("---")
if st.button("Process Latest Email", type="primary", use_container_width=True):
    with st.spinner("Invoking LangGraph AI pipeline..."):
        try:
            res = requests.get(f"{FASTAPI_URL}/api/process-email")
            if res.status_code == 200:
                st.session_state.email_data = res.json().get("email")
                st.session_state.meet_link = None
                st.session_state.reply_status = None
            else:
                st.error(f"Error fetching email data: {res.text}")
        except Exception as e:
            st.error(f"Could not connect to backend service: {e}")
st.markdown("---")

if st.session_state.email_data:
    email = st.session_state.email_data

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Email Metadata")
        st.text_input("Subject", value=email.get("subject", "N/A"), disabled=True)
        st.text_input("Sender", value=email.get("sender", "N/A"), disabled=True)
        
    with col2:
        st.markdown("##### Classification")

        st.metric(
            label="Category",
            value=email.get("category", "N/A")
        )

        priority = email.get("priority", "Low")

        if priority.lower() == "critical":
            st.error(f"Priority: {priority}")
        elif priority.lower() == "high":
            st.warning(f"Priority: {priority}")
        elif priority.lower() == "medium":
            st.info(f"Priority: {priority}")
        else:
            st.success(f"Priority: {priority}")

        st.caption(f"Status: {email.get('status', 'Pending Action')}")

    st.markdown("---")

    col3, col4 = st.columns([1,  1], gap="large")

    with col3:
        st.subheader("Extracted Action Items")
        action_items = email.get("parsed_action_items", [])
        if action_items:
            for item in action_items:
                task_str = item.get("task", "")
                deadline_str = item.get("deadline", "")
                
                # Dynamic text construction matching layout specifications
                display_text = f"**{task_str}**"
                if deadline_str:
                    display_text += f" (Deadline: *{deadline_str}*)"
                st.markdown(f"- {display_text}")
        else:
            st.text("No immediate items parsed.")

    with col4:
        st.subheader("Meeting Detection & Scheduling")

        meeting = email.get("parsed_meeting", {})

        meeting_related = meeting.get("meeting_related", False)
        meeting_intent = meeting.get("meeting_intent", "none")

        st.checkbox(
            "Meeting Detected by AI",
            value=meeting_related,
            disabled=True
        )

        st.text_input(
            "Meeting Intent",
            value=meeting_intent,
            disabled=True
        )

        m_date = st.text_input(
            "Proposed Date",
            value=meeting.get("meeting_date", "")
        )

        m_time = st.text_input(
            "Proposed Time",
            value=meeting.get("meeting_time", "")
        )

        attendees = meeting.get("attendees", [])

        attendee_text = "\n".join(
            [
                f"{attendee.get('name', '')} ({attendee.get('email', '')})"
                if attendee.get("email")
                else attendee.get("name", "")
                for attendee in attendees
            ]
        )

        st.text_area(
            "Parsed Attendees",
            value=attendee_text,
            disabled=True,
            height=120
        )

        attendee_emails = [
            attendee["email"]
            for attendee in attendees
            if attendee.get("email")
        ]

        st.text_area(
            "Attendee Emails",
            value=", ".join(attendee_emails),
            disabled=True,
            height=80
        )

        if meeting_intent == "schedule":

            if st.button("Schedule Google Meet", use_container_width=True):
                with st.spinner("Connecting to Google Calendar Service..."):

                    try:
                        sched_res = requests.post(
                            f"{FASTAPI_URL}/schedule-meeting",
                            json={
                                "thread_id": email.get("thread_id"),
                                "subject": email.get("subject", "Meeting"),
                                "meeting_date": m_date,
                                "meeting_time": m_time,
                                "attendees": attendee_emails
                            }
                        )

                        if sched_res.status_code == 200:
                            st.session_state.meet_link = (
                                sched_res.json().get("meet_link", "#")
                            )
                        else:
                            st.error(sched_res.text)

                    except Exception as e:
                        st.error(f"Network processing exception: {e}")

        if st.session_state.meet_link:
            st.success("Meeting Scheduled Successfully")

            st.link_button(
                "Join Calendar Event / Meet",
                st.session_state.meet_link,
                type="secondary",
                use_container_width=True
            )

    st.markdown("---")

    # Layout Row 3: Action Draft Framework Response Block
#     st.subheader("Draft Composition Engine")
#     draft_body = st.text_area(
#         "Review and modify draft reply:", 
#         value=email.get("parsed_draft", ""), 
#         height=250
#     )

#     if st.button("Send Email Response", type="primary"):
#         with st.spinner("Sending message over Gmail OAuth Relay..."):
#             reply_payload = {
#                 "thread_id": email.get("thread_id"),
#                 "to_email": email.get("sender"),
#                 "subject": email.get("subject"),
#                 "thread_id": email.get("thread_id"),
#                 "body_text": draft_body
#             }
#             try:
#                 reply_res = requests.post(f"{FASTAPI_URL}/send-reply", json=reply_payload)
#                 if reply_res.status_code == 200:
#                     st.toast("Email dispatched successfully!")
#                     st.session_state.reply_status = "Dispatched"
#                 else:
#                     st.error("Could not forward text to destination mailbox.")
#             except Exception as e:
#                 st.error(f"Transmission connection failed: {e}")
                
#     if st.session_state.reply_status == "Dispatched":
#         st.success("Draft synchronization successfully committed to target exchange thread.")

# else:
#     st.info("Awaiting interaction. Click 'Process Latest Email' to read messages.")

st.subheader("Draft Composition Engine")

draft_body = st.text_area(
    "Review and modify draft reply:",
    value=email.get("parsed_draft", ""),
    height=250
)

already_sent = (
    st.session_state.reply_status == "Sent"
)

if already_sent:
    st.success("Reply Already Sent")

    send_label = "Resend Reply"
else:
    send_label = "Send Email Response"

if st.button(send_label, type="primary"):
    with st.spinner("Sending message over Gmail OAuth Relay..."):

        reply_payload = {
            "thread_id": email.get("thread_id"),
            "to_email": email.get("sender"),
            "subject": email.get("subject"),
            "body_text": draft_body
        }

        try:
            reply_res = requests.post(
                f"{FASTAPI_URL}/send-reply",
                json=reply_payload
            )

            if reply_res.status_code == 200:

                st.session_state.reply_status = "Sent"

                if already_sent:
                    st.toast("Reply resent successfully!")
                else:
                    st.toast("Email dispatched successfully!")

                st.rerun()

            else:
                st.error(reply_res.text)

        except Exception as e:
            st.error(f"Transmission connection failed: {e}")