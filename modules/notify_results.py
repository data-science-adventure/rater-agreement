import requests
from dotenv import load_dotenv
from datetime import datetime
import os
now = datetime.now()
load_dotenv()
text_link = os.getenv("REPORT_FOLDER_LINK")
url = os.getenv("SLACK_UML_ANNOTATOR_URL")
formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
# The data payload
data = {"text": f"Se ha generado un nuevo reporte a las {formatted_date} en el siguiente link: {text_link}"}

try:
    # We use json= instead of data= so requests automatically
    # sets the 'Content-type: application/json' header for us.
    response = requests.post(url, json=data)

    # Check if the request was successful
    if response.status_code == 200:
        print("Successfully sent to Slack!")
    else:
        print(f"Failed to send. Status code: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"An error occurred: {e}")
