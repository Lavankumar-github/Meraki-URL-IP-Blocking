# Use this script to create policy objects and add them to policy object groups
# Use the file "ips&urls_to_block.txt" as the input for this script

import os
import getpass
from meraki import DashboardAPI

# -------- Helpers -------- #

def sanitize_name(name: str) -> str:
    """Make sure object names are valid (alphanumeric, dash, underscore, space)."""
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)

# -------- Main Script -------- #

def main():
    # Step 1: API Key
    API_KEY = getpass.getpass(" Enter your Meraki API Key: ").strip()
    dashboard = DashboardAPI(API_KEY, suppress_logging=True)

    # Step 2: Change number
    change_number = input(" Enter Change Number (used in object name): ").strip()

    # Step 3: Load entries from file
    filepath = "ips&urls_to_block.txt"
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        entries = sorted(set(line.strip() for line in f if line.strip()))

    print(f"\n Loaded {len(entries)} unique entries from {filepath}")

    # Step 4: Select Organization
    orgs = dashboard.organizations.getOrganizations()
    if not orgs:
        print("❌ No organizations found for this API key.")
        return

    if len(orgs) == 1:
        ORG_ID = orgs[0]["id"]
        print(f" Using Organization: {orgs[0]['name']} ({ORG_ID})")
    else:
        print("\nAvailable Organizations:")
        for idx, org in enumerate(orgs, 1):
            print(f"{idx}. {org['name']} ({org['id']})")
        choice = int(input("Enter the number of the organization to use: "))
        ORG_ID = orgs[choice - 1]["id"]

    # Step 5: Create policy objects
    created_objects = []
    skipped, failed = [], []

    print("\n Creating policy objects (skips duplicates)...")
    for entry in entries:
        obj_name = sanitize_name(f"{change_number}_{entry}")
        payload = {
            "name": obj_name,
            "category": "network",
            "type": "fqdn" if any(c.isalpha() for c in entry) else "ip",
            "fqdn": entry if any(c.isalpha() for c in entry) else None,
            "cidr": entry if entry.replace(".", "").isdigit() or "/" in entry else None,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            new_obj = dashboard.organizations.createOrganizationPolicyObject(ORG_ID, **payload)
            created_objects.append(new_obj["id"])
            print(f"  ✅ Created: {obj_name}")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                skipped.append(obj_name)
                print(f"   Skipped (already exists): {obj_name}")
            else:
                failed.append((obj_name, error_msg))
                print(f"   Failed to create {obj_name}: {error_msg}")

    # Step 6: Select Policy Object Group
    groups = dashboard.organizations.getOrganizationPolicyObjectsGroups(ORG_ID)
    if not groups:
        print("❌ No policy object groups found.")
        return

    print("\n Available Policy Object Groups:")
    for idx, group in enumerate(groups, 1):
        print(f"{idx}. {group['name']} ({group['id']})")

    choice = int(input("\n Enter the number of the group to add objects to: "))
    selected_group_id = groups[choice - 1]["id"]
    selected_group_name = groups[choice - 1]["name"]

    # Step 7: Update Group with New Objects
    if created_objects:
        try:
            # Get current group details
            group = dashboard.organizations.getOrganizationPolicyObjectsGroup(ORG_ID, selected_group_id)
            current_object_ids = group.get("objectIds", [])

            # Merge and deduplicate
            updated_object_ids = list(set(current_object_ids + created_objects))

            # Update group
            dashboard.organizations.updateOrganizationPolicyObjectsGroup(
                ORG_ID,
                selected_group_id,
                name=selected_group_name,  # Must re-send name
                objectIds=updated_object_ids
            )

            print(f"\n✅ Successfully updated group '{selected_group_name}' with {len(created_objects)} new objects.")
        except Exception as e:
            print(f"❌ Failed to update group: {e}")
    else:
        print(" No objects to add to any group. Exiting.")

    # Step 8: Summary
    print("\n Summary:")
    print(f"  ✅ Created: {len(created_objects)}")
    print(f"   Skipped: {len(skipped)}")
    print(f" ❌  Failed: {len(failed)}")
    if failed:
        for name, msg in failed:
            print(f"    - {name}: {msg}")


if __name__ == "__main__":
    main()

