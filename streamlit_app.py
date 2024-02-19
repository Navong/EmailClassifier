import streamlit as st
import pickle
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import os
import time



# Download NLTK resources
nltk.download('stopwords')
nltk.download('punkt')

# Initialize NLTK components
ps = PorterStemmer()

# Load the TF-IDF vectorizer and the classification model
with open('vectorizer.pkl', 'rb') as vectorizer_file:
    tfidf = pickle.load(vectorizer_file)

with open('model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

# Define the OAuth 2.0 scopes required for accessing Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Custom CSS styles for highlighting
GREEN_HIGHLIGHT = '<span style="color: green; font-weight: bold; font-size: larger;">Not Spam</span>'
RED_HIGHLIGHT = '<span style="color: red; font-weight: bold; font-size: larger;">Spam</span>'


def transform_text(text):
    text = text.lower()
    text = nltk.word_tokenize(text)

    y = [i for i in text if i.isalnum()]

    text = [i for i in y if i not in stopwords.words(
        'english') and i not in string.punctuation]

    return " ".join([ps.stem(i) for i in text])


def clear_token_file():
    token_file = 'token.json'
    max_age_seconds = 3600  # 1 hour

    if os.path.exists(token_file):
        # Get the modification time of the token file
        file_modified_time = os.path.getmtime(token_file)

        # Get the current time
        current_time = time.time()

        # Calculate the age of the token file in seconds
        age_seconds = current_time - file_modified_time

        # If the token file is older than the maximum age, delete it
        if age_seconds > max_age_seconds:
            os.remove(token_file)

# Call the function to clear the token file


def get_credentials():
    clear_token_file()
    if not os.path.exists('token.json'):
        st.error("No user credentials found. Please log in.")
        authenticate_user()
        # refresh page
        st.experimental_rerun()
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        st.error("Invalid user credentials. Please log in.")
        authenticate_user()
    return creds


def authenticate_user():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())


def get_email_body(service, message_id):
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full').execute()
        payload = message['payload']
        parts = payload.get('parts', [])

        for part in parts:
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        return "No content available."
    except Exception as e:
        return f"Error fetching email content: {e}"


def classify_email(email_body):
    transformed_text = transform_text(email_body)
    vectorized_text = tfidf.transform([transformed_text])
    result = model.predict(vectorized_text)[0]
    return result


def main():
    st.title("Email Classification")
    creds = get_credentials()

    try:
        service = build('gmail', 'v1', credentials=creds)

        result = service.users().messages().list(userId='me').execute()
        messages = result.get('messages', [])

        if not messages:
            st.sidebar.write('No messages found.')
            return

        st.sidebar.write('\n**Inbox Emails:**')

        email_list = []

        for i, message in enumerate(messages[:20], start=1):
            msg = service.users().messages().get(
                userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']
            subject = ''

            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                    break

            email_list.append(f'{i}. **{subject}** ({message["threadId"]})')

        selected_email = st.sidebar.selectbox("Select Email", email_list)

        for i, message in enumerate(messages[:20], start=1):
            msg = service.users().messages().get(
                userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']
            subject = ''

            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                    break

            if f'{i}. **{subject}** ({message["threadId"]})' == selected_email:
                st.write(f'Selected Email: {selected_email}')

                # Retrieve the email body
                email_body = get_email_body(service, message['id'])

                # Classify the email as spam or not spam
                result = classify_email(email_body)

                # Apply border color based on classification result
                border_color = 'red' if result == 1 else 'green'

                # Write custom HTML to apply the border around the email body
                st.markdown(
                    f'<div style="border: 2px solid {border_color}; padding: 10px;">{email_body}</div>',
                    unsafe_allow_html=True
                )

                # Highlight the classification result
                st.write(
                    f'<p style="padding-top: 20px; font-weight: bold;">Classification:</p>', unsafe_allow_html=True)
                st.write(
                    f'<p>{RED_HIGHLIGHT if result == 1 else GREEN_HIGHLIGHT}</p>', unsafe_allow_html=True)

    except Exception as e:
        st.write(f'An error occurred: {e}')


if __name__ == "__main__":
    main()
