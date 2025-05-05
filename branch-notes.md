
## Branch: feature/rbac-define-get-access_level
- Purpose: Testing to extract role type from role definition spec file
- Status: in progress
- Created by: Mumtaz
- Created on: 2025-04-16
- Notes: This branch will contain the experiment to extract the role_type from definition specfile and embed it into the description.

## Branch: feature/rbac-access_level-in-specfile
- Purpose: Test to extract access_level property from spec file
- Status: in progress
- Created by: Mumtaz
- Created on: 2025-04-17
- Notes: This branch is to test the feature to extract the access_level from role definition specfile, instead of passing it in the GitHub Workflow

## Branch: feature/rbac-manager_func
- Purpose: Function based rbac_manager
- Status: in progress
- Created by: Mumtaz
- Created on: 2025-05-02
- Notes: Create branch to modify existing code into function based.

## Branch: feature/rbac-manager_search_files_in_infra
- Purpose: Search .yaml files under infrastructure/
- Status: in progress
- Created by: Mumtaz
- Created on: 2025-05-02
- Notes: Modify the logic and search .yaml or .yml files starting from infrastructure folder instead of definition folder. There are two subfolder under infrastructure, one is definitions and other is assignments.

## Branch: feature/rbac-manager_search_files_in_infra
- Purpose: Search .yaml files under infrastructure/
- Status: merged
- Created by: Mumtaz
- Created on: 2025-05-05
- Notes: .ymal/.yml files are now seachable from infrastructure/ folder
