import os
import matplotlib.pyplot as plt
from doccano_client import DoccanoClient
from dotenv import load_dotenv
from util.config_util import ConfigUtil
config = ConfigUtil.get_config()

# 1. Configuration & Setup
load_dotenv()
URL = os.getenv("DOCCANO_URL")
USERNAME = os.getenv("DOCCANO_USERNAME")
PASSWORD = os.getenv("DOCCANO_PASSWORD")
PROJECT_ID = config.main.project_id  # Replace with your actual project ID

# NEW: Define which users to exclude dynamically
# You can add as many names as you want here: ["heidi", "admin", "test_user"]
EXCLUDE_USERS = config.download_expert_report.exclude_members 

client = DoccanoClient(URL)
client.login(username=USERNAME, password=PASSWORD)

# 2. Fetch and Dynamic Filtering
print(f"Fetching progress for project {PROJECT_ID}...")
raw_progress = client.get_members_progress(project_id=PROJECT_ID)

# Filtering logic using 'not in' for multiple users
member_progress = [
    m for m in raw_progress 
    if m.username not in EXCLUDE_USERS
]

# 3. Data Preparation for Plotting
if not member_progress:
    print("No data found after filtering. Skipping graph generation.")
else:
    usernames = [m.username for m in member_progress]
    completed = [m.progress.completed for m in member_progress]
    remaining = [m.progress.remaining for m in member_progress]

    # 4. Create the Visualization
    plt.figure(figsize=(10, 6))
    
    # Create the stacked bars
    plt.bar(usernames, completed, label='Completed', color='#4CAF50')
    plt.bar(usernames, remaining, bottom=completed, label='Remaining', color='#FFC107')

    plt.xlabel('Annotators')
    plt.ylabel('Number of Tasks')
    plt.title(f'Progress Report (Excluding: {", ".join(EXCLUDE_USERS)})')
    plt.legend()

    # 5. Export Logic
    output_dir = "report"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "members_progress.png")

    plt.savefig(output_path)
    plt.close()
    print(f"Success! Report saved to {output_path} for users: {usernames}")