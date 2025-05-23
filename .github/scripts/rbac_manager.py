import argparse
import yaml
import json
import sys
import re
from pathlib import Path
from google.auth import default
from google.auth import impersonated_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def fetch_permissions_for_role(service, role_name):
    try:
        # Determine if role is predefined or custom
        if re.match(r'^roles/[^/]+$', role_name):
            request = service.roles().get(name=role_name)
        elif re.match(r'organizations/\d+/roles/[^/]+$', role_name):
            request = service.organizations().roles().get(name=role_name)
        else:
            print(f"❌ Invalid role format: {role_name}")
            sys.exit(1)

        response = request.execute()
        return response.get("includedPermissions", [])
    except HttpError as e:
        print(f"⚠️ Could not fetch base role '{role_name}': {e}")
        return [] 

def create_or_update_custom_role_from_yaml(yaml_path, org_id):
    with open(yaml_path, 'r') as f:
        role_def = yaml.safe_load(f)
        role_props = role_def.get('customRole', {})

    role_type = role_props.get('role_type') # Allowed values: Privileged or Regular
    if role_type not in ["Privileged", "Regular"]:
        print(f"❌ Invalid or missing role_type: {role_type}. Allowed values: Privileged or Regular.")
        sys.exit(1)

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

    role_id = role_props['id']
    permissions = set(role_props.get('includedPermissions', []))
    excluded_permissions = set(role_props.get('excludedPermissions', []))

    if 'baseRoles' in role_props:
        print(f"📎 Expanding permissions from baseRoles: {role_props['baseRoles']}")
        for base_role in role_props['baseRoles']:
            base_permissions = fetch_permissions_for_role(service, base_role)
            permissions.update(base_permissions)

    if excluded_permissions:
        print(f"🚫 Excluded permissions: {sorted(excluded_permissions)}")

    permissions.difference_update(excluded_permissions)

    if not permissions:
        print(f"❌ No permissions defined. Must provide 'includedPermissions' or valid 'baseRole'.")
        sys.exit(1)

    role_payload = {
        "title": role_props['name'],
        "description": f"Access Level: {role_type}. {role_props['description']}",
        "stage": role_props.get('stage', 'GA'),
        "includedPermissions": sorted(permissions)
    }

    # Determine IAM parent path based on --org flag
    parent = f"organizations/{org_id}"
    role_name = f"{parent}/roles/{role_id}"
    org_roles = service.organizations().roles()

    try:
        existing = org_roles.get(name=role_name).execute()
        existing_permissions = set(existing.get("includedPermissions", []))
        existing_title = existing.get("title")
        existing_description = existing.get("description")

        # Determine if update is needed
        if (set(existing_permissions) != set(role_payload["includedPermissions"]) or existing_title != role_payload["title"] or existing_description != role_payload["description"]):
            if existing_permissions != set(role_payload["includedPermissions"]):
                added = set(role_payload["includedPermissions"]) - existing_permissions
                removed = existing_permissions - set(role_payload["includedPermissions"])
                if added:
                    print(f"🔼 Permissions added: {sorted(added)}")
                if removed:
                    print(f"🔽 Permissions removed: {sorted(removed)}")

            print(f"♻️ Updating existing role '{role_id}' in {parent}...")
            response = org_roles.patch(
                name=role_name,
                body=role_payload,
                updateMask="title,description,includedPermissions"
            ).execute()
            print(f"✅ Role updated:")
            print(json.dumps(response, indent=2))
        else:
            print(f"✅ Role '{role_id}' in {parent}' is already up-to-date. No action taken.")
                  
    except HttpError as e:
        if e.resp.status == 404:
            # Role does not exist, create new
            print(f"⏳ Creating role '{role_id}' in {parent}")
            response = org_roles.create(
                parent=parent,
                body={"roleId": role_id, "role": role_payload}
            ).execute()
            print(f"✅ Role created:")
            print(json.dumps(response, indent=2))
        else:
            print(f"❌ Failed to retrieve or create role '{role_id}': {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Create custom IAM roles from YAML definitions.")
    parser.add_argument("org_id", help="GCP Organization ID")
    parser.add_argument("--role_file", required=True, help="YAML file name for specific role (inside infrastructure/definitions)")
    args = parser.parse_args()

    base_dir = Path("infrastructure")
    possible_paths = [
        base_dir / "definitions" / args.role_file,
        base_dir / "assignments" / args.role_file
    ]

    yaml_path = next((p for p in possible_paths if p.exists()), None)

    if not yaml_path.exists():
        print(f"❌ File '{yaml_path}' not found.")
        sys.exit(1)

    if not yaml_path.read_text().strip():
        print(f"❌ YAML file {yaml_path} is empty.")
        sys.exit(1)

    print(f"\n📄 Processing: {yaml_path.name}")
    create_or_update_custom_role_from_yaml(yaml_path, args.org_id)


if __name__ == "__main__":
    main()