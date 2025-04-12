import yaml
import json
import sys
from pathlib import Path
from google.auth import default
from google.auth import impersonated_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def create_custom_role_from_yaml(yaml_path, fallback_project_id, is_org):
    with open(yaml_path, 'r') as f:
        role_def = yaml.safe_load(f)

    # Step 1: Load source creds (ADC points to auth@v2 federated token)
    source_credentials, _ = default()

    # Step 2: Create impersonated credentials for your target SA
    target_service_account = "gcp-gh-sa@hale-entry-456413-g7.iam.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    impersonated_creds = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_service_account,
        target_scopes=scopes,
        lifetime=3600,
    )

    # Step 3: Build the IAM service with impersonated identity
    service = build("iam", "v1", credentials=impersonated_creds)

    role_id = role_def['roleId']
    role = {
        "title": role_def['title'],
        "description": role_def['description'],
        "stage": role_def.get('stage', 'GA'),
        "includedPermissions": role_def['includedPermissions']
    }

    # Determine IAM parent path based on --org flag
    if is_org:
        parent = f"organizations/{fallback_project_id}"
        get_func = service.organizations().roles().get
        create_func = service.organizations().roles().create
    else:
        parent = f"projects/{fallback_project_id}"
        get_func = service.projects().roles().get
        create_func = service.projects().roles().create

    # Check if the role exists
    try:
        get_func(name=f"{parent}/roles/{role_id}").execute()
        print(f"⚠️ Role '{role_id}' already exists in {parent}. Skipping creation.")
        return
    except HttpError as e:
        if e.resp.status != 404:
            raise  # only pass if the role truly doesn't exist

    # Create the role
    try:
        print(f"⏳ Creating role '{role_id}' in {parent}")
        response = create_func(
            parent=parent,
            body={"roleId": role_id, "role": role}
        ).execute()
        print("✅ Role created:")
        print(json.dumps(response, indent=2))
    except HttpError as e:
        print(f"❌ Failed to create role '{role_id}': {e}")

def create_roles_from_directory(directory, fallback_project_id, is_org):
    roles_path = Path(directory)
    if not roles_path.exists():
        print(f"❌ Directory '{directory}' not found.")
        sys.exit(1)

    for yaml_file in roles_path.glob("*.yaml"):
        print(f"\n📄 Processing: {yaml_file.name}")
        create_custom_role_from_yaml(yaml_file, fallback_project_id, is_org)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_custom_role.py <project_id or organization_id> [--org]")
        sys.exit(1)

    scope_id = sys.argv[1]
    is_org = len(sys.argv) == 3 and sys.argv[2] == '--org'

    create_roles_from_directory("infrastructure/definitions", scope_id, is_org)
