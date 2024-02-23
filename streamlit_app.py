import google_auth_oauthlib
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
import google.auth.transport.requests



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


# def get_credentials():
#     clear_token_file()
#     if not os.path.exists('token.json'):
#         st.error("No user credentials found. Please log in.")
#         authenticate_user()
#         # refresh page
#         st.experimental_rerun()
#     creds = Credentials.from_authorized_user_file('token.json', SCOPES)
#     if not creds or not creds.valid:
#         st.error("Invalid user credentials. Please log in.")
#         authenticate_user()
#     return creds


# def authenticate_user():
#     flow = InstalledAppFlow.from_client_secrets_file(
#         'credentials.json', SCOPES)
#     creds = flow.run_local_server(port=0)
#     with open('token.json', 'w') as token:
#         token.write(creds.to_json())
            
def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


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
    st.title("Email Classification using AI")

    # Add tabs for the guideline, classify emails, and about me
    guideline_tab, classify_tab, about_me_tab = st.tabs(["Guideline", "Classify Emails", "About me"])


    # Guideline Tab
    with guideline_tab:
        st.markdown("""
        #### 📣 Guideline for Testing the Spam Classification Web App 📣

        Hey there! I'm excited to share with you how to test my spam classification web app. Just follow these simple steps:

        1. 📧 Use your Gmail account to send an email to [creativeartist9922@gmail.com](mailto:creativeartist9922@gmail.com) and add this word "**ForTestingWebApp**" in your email body to bypass spam filter in gmail.
        2. 📝 Add a subject of your choice and write some text in the email that you want to analyze. This could be a regular (ham) email or a spam email.
        3. 🧪 Once you've sent the email, the web app will automatically analyze the email and classify it as either spam or ham.
        4. 👀 You can view the analysis results by checking your email inbox for a response from the web app.
        5. 🔄 If you don't see the analysis results right away, don't worry! Sometimes it takes a few minutes for the web app to process the email. Simply refresh the page to see the updated results.
        6. 🔄 Additionally, you can check the color of the line around the email in your inbox to get an idea of whether it's spam or ham. If the line is green it's likely a regular (ham) email. If the line is red, it's likely a spam email.
        
        #### A few things to keep in mind:

        * This web app is for educational purposes only and is not intended for marketing or any other commercial use.
        * The web app uses machine learning algorithms to classify emails as spam or ham, but it may not be 100% accurate.
        * Feel free to test the web app and check out the GitHub repo. If you find it useful, please give it a star!

        That's it! I hope you find this web app helpful and enjoy testing it out. If you have any questions or feedback, please don't hesitate to reach out.

        Thanks for checking it out! 😊
                    
        Get Idea from [GitHub Repo][1].
        Checkout Kaggle for more information [Phishing Detection with Machine Learning](https://www.kaggle.com/code/akritiupadhyayks/phishing-detection-with-machine-learning?scriptVersionId=147660313)

        [1]: https://github.com/campusx-official/sms-spam-classifier "GitHub Repository"

        """)

    # Classify Emails Tab
    with classify_tab:
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

    with about_me_tab:
        st.markdown("""
        I'm Navong (짠나봉), a Computer Science student at Inha University. I'm passionate about AI, Blockchain, NLP, Security, and Cloud. These domains are all interconnected in fascinating ways:

        :brain: AI and NLP: I'm interested in Natural Language Processing (NLP), a subfield of AI that focuses on how computers can understand and generate human language. NLP techniques are essential for developing AI systems that can interact with humans in a natural way.

        :lock: AI and Security: I'm also interested in how AI technologies like machine learning and deep learning can be used to enhance cybersecurity. AI can help with threat detection, anomaly detection, and improving overall security infrastructure.

        :ledger: AI and Blockchain: I think there's a lot of potential for combining AI and blockchain technologies. By using decentralized networks, we can create secure and transparent AI applications.

        :cloud: AI and Cloud: Cloud computing provides the perfect infrastructure for AI applications. Many AI services, like machine learning platforms and NLP APIs, are offered through cloud providers.

        :bulb: AI and Innovation: I love exploring new technologies and domains like AI, Blockchain, NLP, Security, and Cloud. Continuous learning and innovation are key to personal and professional growth!

        🤔 I like to try new things and discover something new every single day. :sparkles:
        """)


if __name__ == "__main__":
    main()
