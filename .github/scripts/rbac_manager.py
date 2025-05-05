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

    role_type = role_props.get('role_type')
    if role_type not in ["Privileged", "Regular"]:
        print(f"❌ Invalid or missing role_type: {role_type}. Allowed values: Privileged or Regular.")
        sys.exit(1)

    source_credentials, _ = default()

    target_service_account = "gcp-gh-sa@hale-entry-456413-g7.iam.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    impersonated_creds = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_service_account,
        target_scopes=scopes,
        lifetime=3600,
    )

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

    parent = f"organizations/{org_id}"
    role_name = f"{parent}/roles/{role_id}"
    org_roles = service.organizations().roles()

    try:
        existing = org_roles.get(name=role_name).execute()
        existing_permissions = set(existing.get("includedPermissions", []))
        existing_title = existing.get("title")
        existing_description = existing.get("description")

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

def assign_role_from_yaml(yaml_path):
    with open(yaml_path, 'r') as f:
        assignment_def = yaml.safe_load(f)

    assignments = assignment_def.get("assignments")
    if not assignments or len(assignments) != 1:
        print("❌ Each YAML file must define exactly one role assignment under 'assignments'.")
        sys.exit(1)

    assignment = assignments[0]
    principal = assignment.get("principal")
    role = assignment.get("role")
    scope = assignment.get("scope", {})
    level = scope.get("level")
    target_id = scope.get("id")

    if not principal or not role or not level or not target_id:
        print("❌ Missing required fields in assignment.")
        sys.exit(1)

    valid_prefixes = ["user:", "group:", "serviceAccount:", "domain:", "allUsers", "allAuthenticatedUsers"]
    if not any(principal.startswith(p) for p in valid_prefixes):
        print(f"❌ Invalid principal format: {principal}")
        sys.exit(1)

    source_credentials, _ = default()
    target_service_account = "gcp-gh-sa@hale-entry-456413-g7.iam.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    impersonated_creds = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_service_account,
        target_scopes=scopes,
        lifetime=3600,
    )

    crm_service = build("cloudresourcemanager", "v1", credentials=impersonated_creds)

    if level == "organization":
        resource = f"organizations/{target_id}"
        get_policy = crm_service.organizations().getIamPolicy
        set_policy = crm_service.organizations().setIamPolicy
    elif level == "folder":
        resource = f"folders/{target_id}"
        get_policy = crm_service.folders().getIamPolicy
        set_policy = crm_service.folders().setIamPolicy
    elif level == "project":
        resource = f"projects/{target_id}"
        get_policy = crm_service.projects().getIamPolicy
        set_policy = crm_service.projects().setIamPolicy
    else:
        print(f"❌ Invalid scope level: {level}. Must be 'organization', 'folder', or 'project'.")
        sys.exit(1)

    policy = get_policy(resource=resource, body={}).execute()
    bindings = policy.get("bindings", [])
    for b in bindings:
        if b["role"] == role:
            if principal in b.get("members", []):
                print(f"✅ Principal already has role '{role}' at {resource}. No changes needed.")
                return
            else:
                b["members"].append(principal)
                break
    else:
        bindings.append({"role": role, "members": [principal]})

    policy["bindings"] = bindings
    updated = set_policy(resource=resource, body={"policy": policy}).execute()
    print(f"✅ Role '{role}' assigned to '{principal}' at {resource}.")

def main():
    parser = argparse.ArgumentParser(description="Manage custom IAM roles or assignments from YAML definitions.")
    parser.add_argument("org_id", help="GCP Organization ID")
    parser.add_argument("--role_file", required=True, help="YAML file for custom role or single role assignment")
    args = parser.parse_args()

    base_dir = Path("infrastructure")
    possible_paths = [
        base_dir / "definitions" / args.role_file,
        base_dir / "assignments" / args.role_file
    ]

    yaml_path = next((p for p in possible_paths if p.exists()), None)

    if not yaml_path or not yaml_path.exists():
        print(f"❌ File '{args.role_file}' not found in definitions or assignments directory.")
        sys.exit(1)

    if not yaml_path.read_text().strip():
        print(f"❌ YAML file {yaml_path} is empty.")
        sys.exit(1)

    print(f"\n📄 Processing: {yaml_path.name}")
    content = yaml.safe_load(yaml_path.read_text())
    if "customRole" in content:
        create_or_update_custom_role_from_yaml(yaml_path, args.org_id)
    elif "assignments" in content:
        assign_role_from_yaml(yaml_path)
    else:
        print("❌ Unrecognized YAML structure. Must contain either 'customRole' or 'assignments'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
