# Note: Whatever you block with this script will be added under Content Filtering
# Use the file "urls_to_block.txt" as the input list of URLs to block
import os
import sys
import getpass
from dotenv import load_dotenv
from meraki import DashboardAPI


# Step 1: Load API Key
load_dotenv()
API_KEY = os.getenv("MERAKI_API_KEY")
if not API_KEY:
    API_KEY = getpass.getpass(" Enter your Meraki API Key: ").strip()

ORG_ID = os.getenv("MERAKI_ORG_ID", "XXXX")

if not API_KEY:
    print("❌ API key missing.")
    sys.exit(1)

# Initialize API
dashboard = DashboardAPI(API_KEY, suppress_logging=True)


# Step 2: Load networks from .env
network_mapping = {
    key.upper(): value for key, value in os.environ.items()
    if key.upper() not in ("MERAKI_API_KEY", "MERAKI_ORG_ID") and value.startswith("N_")
}
if not network_mapping:
    print("❌ No networks found in .env file (must start with N_)")
    sys.exit(1)


# Step 3: Choose Global or Specific
global_choice = input("🌍 Block globally (YES/NO)? ").strip().upper()
target_networks = []

if global_choice == "YES":
    target_networks = list(network_mapping.items())
elif global_choice == "NO":
    print("\n Networks:")
    for idx, (name, net_id) in enumerate(network_mapping.items(), start=1):
        print(f"{idx}. {name} ({net_id})")
    try:
        choice = int(input(" Enter number: ").strip())
        selected_name = list(network_mapping.keys())[choice - 1]
        target_networks = [(selected_name, network_mapping[selected_name])]
    except Exception:
        print("❌ Invalid selection")
        sys.exit(1)
else:
    sys.exit(1)


# Step 4: Load URLs
if not os.path.exists("urls_to_block.txt"):
    print("❌ Missing urls_to_block.txt")
    sys.exit(1)

with open("urls_to_block.txt") as f:
    urls = [line.strip() for line in f if line.strip()]

if not urls:
    print("❌ urls_to_block.txt is empty")
    sys.exit(1)


# Step 5: Apply Rules
success, failed = [], []

for name, net_id in target_networks:
    print(f"\n🔧 Updating {name} ({net_id})")

    try:
        current = dashboard.appliance.getNetworkApplianceContentFiltering(net_id)

        # Merge & deduplicate
        combined = list(set(current.get("blockedUrlPatterns", []) + urls))

        # Update filtering
        dashboard.appliance.updateNetworkApplianceContentFiltering(
            net_id,
            blockedUrlPatterns=combined,
            allowedUrlPatterns=current.get("allowedUrlPatterns", []),
            urlCategoryListSize=current.get("urlCategoryListSize", "topSites"),
            urlCategoryList=current.get("urlCategoryList", []),
        )
        print(f"✅ URLs applied to {name}")
        success.append(name)

    except Exception as e:
        print(f"❌ Failed {name}: {e}")
        failed.append(name)

print("\n🎉  URL blocking completed.")
print(f"✅  Success: {success if success else 'None'}")
print(f"❌  Failed ({len(failed)}): {failed if failed else 'None'}")
