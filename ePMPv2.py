import streamlit as st
import pdfplumber
import json

# -----------------------------
# 🔹 Page Config
# -----------------------------
st.set_page_config(
    page_title="📡 ePMP Configuration Tool",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# 🔹 Channel Bandwidth Mapping (Internal Logic)
# -----------------------------
channel_bandwidth_mapping = {
    "20": "1",
    "40": "2",
    "10": "4",
    "5": "8"
}

# Preview mapping for display only


def preview_bandwidth(value):
    mapping = {
        "1": "20",
        "2": "40",
        "4": "10",
        "8": "5"
    }
    return mapping.get(str(value), value)


# -----------------------------
# 🔹 Target Fields & Mappings
# -----------------------------
targets = [
    "Master", "Slave", "Latitude", "Longitude", "Antenna Height",
    "Channel Bandwidth", "AP SSID", "Transmitter Output Power",
    "System Name", "Frequency"
]

replacements = {
    "Master": "systemConfigDeviceName",
    "Slave": "systemConfigDeviceName",
    "Latitude": "systemDeviceLocLatitude",
    "Longitude": "systemDeviceLocLongitude",
    "Antenna Height": "systemDeviceLocHeight",
    "Channel Bandwidth": "wirelessInterfaceScanFrequencyBandwidth",
    "AP SSID": "wirelessInterfaceSSID",
    "Transmitter Output Power": "wirelessInterfaceTXPower",
    "System Name": "snmpSystemName",
    "Frequency": "centerFrequency"
}

units_to_remove = [" meters AGL", " MHz", " dBm"]

# -----------------------------
# 🔹 Clean Values
# -----------------------------


def clean_value(value, field_name=None):
    if not value:
        return value

    value = value.strip()
    for unit in units_to_remove:
        if value.endswith(unit):
            value = value.replace(unit, "").strip()

    if field_name in ["systemDeviceLocLatitude", "systemDeviceLocLongitude"]:
        if value and value[-1] in ["N", "S", "E", "W"]:
            value = value[:-1].strip()

        try:
            num = float(value)
            value = str(int(num)) if num.is_integer() else str(num)
        except ValueError:
            pass

    if field_name in ["systemDeviceLocHeight", "wirelessInterfaceTXPower", "centerFrequency"]:
        try:
            num = float(value)
            value = str(int(num)) if num.is_integer() else str(num)
        except ValueError:
            pass

    if field_name == "wirelessInterfaceScanFrequencyBandwidth":
        value = channel_bandwidth_mapping.get(value, value)

    return value.strip()

# -----------------------------
# 🔹 Extract Data from PDF
# -----------------------------


def extract_full_system_names(pdf_file):
    all_extracted_items = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    clean_row = [" ".join(str(cell).split())
                                 for cell in row if cell]
                    for i, cell in enumerate(clean_row):
                        for target in targets:
                            if cell.startswith(target):
                                value = clean_row[i + 1] if i + 1 < len(
                                    clean_row) else cell.replace(target, "").strip(": ").strip()
                                if value:
                                    mapped_key = replacements.get(
                                        target, target)
                                    cleaned_value = clean_value(
                                        value, mapped_key)
                                    all_extracted_items.append({
                                        "field": mapped_key,
                                        "value": cleaned_value
                                    })
    return all_extracted_items

# -----------------------------
# 🔹 Apply Scan Frequency Lists for SM
# -----------------------------


def apply_scan_frequency_lists_sm(config):
    bandwidth = config.get("wirelessInterfaceScanFrequencyBandwidth")
    frequency = config.get("centerFrequency")
    config["wirelessInterfaceScanFrequencyListTwenty"] = ""
    config["wirelessInterfaceScanFrequencyListForty"] = ""
    config["wirelessInterfaceScanFrequencyListTen"] = ""
    config["wirelessInterfaceScanFrequencyListFive"] = ""
    if not bandwidth or not frequency:
        return
    bandwidth_to_field = {
        "1": "wirelessInterfaceScanFrequencyListTwenty",
        "2": "wirelessInterfaceScanFrequencyListForty",
        "4": "wirelessInterfaceScanFrequencyListTen",
        "8": "wirelessInterfaceScanFrequencyListFive"
    }
    field = bandwidth_to_field.get(bandwidth)
    if field:
        config[field] = frequency
    config.pop("centerFrequency", None)

# -----------------------------
# 🔹 Add Preferred AP Table for SM
# -----------------------------


def add_preferred_ap_table(sm_dict):
    ssid_from_pdf = sm_dict.get("wirelessInterfaceSSID", "")
    sm_dict["prefferedAPTable"] = [

        {
            "prefferedListTableEntrySSID":	ssid_from_pdf,
            "prefferedListTableEntryKEY":	"dialog_5.2cambium",
            "prefferedListTableSecurityMethod":	"5",
            "prefferedListTableEntryBSSID":	""
        }


    ]

# -----------------------------
# 🔹 Split to JSON Objects
# -----------------------------


def split_to_json_objects(extracted_data):
    ap_lines = [1, 3, 4, 5, 10, 11, 12, 13, 14]
    sm_lines = [2, 6, 7, 8, 10, 16, 17, 18]

    ap_json = {extracted_data[i-1]['field']: extracted_data[i-1]
               ['value'] for i in ap_lines if i-1 < len(extracted_data)}
    sm_json = {extracted_data[i-1]['field']: extracted_data[i-1]
               ['value'] for i in sm_lines if i-1 < len(extracted_data)}

    # Manual entries for AP
    ap_manual_entries = {
        "acsEnable": "0",
        "wirelessDeviceCountryCode": "OT",
        "networkBridgeMTU": "1700",
        "mgmtVLANEnable": "1",
        "mgmtVLANVP": "5",
        "systemConfigTimezone": "SLT-5:30",
        "wirelessInterfaceEncryptionKey": "dialog_5.2cambium",
        "wirelessInterfaceTPCTRL": "-56",
        "wirelessInterfaceMode": "1",
        "wirelessInterfacePTPMode": "1",
        "wirelessMaximumCellSize": "64",
        "wirelessMaximumSTA": "10",
        "systemNtpServerIPMode": "1",
        "systemNtpServerPrimaryIP": "10.58.48.150",
        "systemNtpServerSecondaryIP": "192.168.4.9",
        "cambiumDeviceAgentEnable": "1",
        "cambiumDeviceAgentCNSURL": "https://10.62.231.253/",
        "snmpAgentPort": "161",
        "snmpRemoteAccess": "1",
        "snmpReadOnlyCommunity": "TACpublic",
        "snmpReadWriteCommunity": "TACprivate",
        "snmpTrapCommunity": "cambiumtrap",
        "snmpTrapEnable": "1",
        "snmpTrapTable": [
            {"snmpTrapEntryIP": "10.62.231.252", "snmpTrapEntryPort": "161"},
            {"snmpTrapEntryIP": "10.58.16.160", "snmpTrapEntryPort": "161"},
            {"snmpTrapEntryIP": "10.58.16.168", "snmpTrapEntryPort": "161"}
        ],
        "networkBridgeIPAddr": "",
        "networkBridgeGatewayIP": "",
        "networkBridgeNetmask": "",
        "mgmtVLANVID": "",
    }

    # Manual entries for SM
    sm_manual_entries = {
        "networkBridgeMTU": "1700",
        "mgmtVLANEnable": "1",
        "mgmtVLANVP": "5",
        "systemConfigTimezone": "SLT-5:30",
        "wirelessInterfaceEncryptionKey": "dialog_5.2cambium",
        "wirelessInterfaceMode": "2",
        "systemNtpServerIPMode": "1",
        "systemNtpServerPrimaryIP": "10.58.48.150",
        "systemNtpServerSecondaryIP": "192.168.4.9",
        "cambiumDeviceAgentEnable": "1",
        "cambiumDeviceAgentCNSURL": "https://10.62.231.253/",
        "snmpAgentPort": "161",
        "snmpRemoteAccess": "1",
        "snmpReadOnlyCommunity": "TACpublic",
        "snmpReadWriteCommunity": "TACprivate",
        "snmpTrapCommunity": "cambiumtrap",
        "snmpTrapEnable": "1",
        "snmpTrapTable": [
            {"snmpTrapEntryIP": "10.62.231.252", "snmpTrapEntryPort": "161"},
            {"snmpTrapEntryIP": "10.58.16.160", "snmpTrapEntryPort": "161"},
            {"snmpTrapEntryIP": "10.58.16.168", "snmpTrapEntryPort": "161"}
        ],
        "networkBridgeIPAddr": "",
        "networkBridgeGatewayIP": "",
        "networkBridgeNetmask": "",
        "mgmtVLANVID": "",
        "dataVLANEnable": "1",
        "dataVLANVID": ""
    }

    ap_json.update(ap_manual_entries)
    sm_json.update(sm_manual_entries)

    ap_json["snmpSystemDescription"] = ap_json.get("snmpSystemName", "")
    sm_json["snmpSystemDescription"] = sm_json.get("snmpSystemName", "")

    apply_scan_frequency_lists_sm(sm_json)
    add_preferred_ap_table(sm_json)

    return ap_json, sm_json


# -----------------------------
# 🔹 Streamlit UI
# -----------------------------
st.title("📡 ePMP Configuration Tool")

# Sidebar inputs
st.sidebar.header("⚙️ Device Settings")
ap_ip = st.sidebar.text_input("AP IP", "")
sm_ip = st.sidebar.text_input("SM IP", "")
common_gateway = st.sidebar.text_input("Gateway IP", "")
common_netmask = st.sidebar.text_input("Subnet Mask", "")
common_vlan = st.sidebar.text_input("Management VLAN", "")
sm_data_vlan = st.sidebar.text_input("Data VLAN", "")
sm_data_vlan_enable = st.sidebar.radio(
    "Data VLAN Mode", ["Enable", "Disable"], index=1, horizontal=True)
ap_protocol_mode = st.sidebar.radio(
    "ePMP Mode", ["PtP", "PtMP"], horizontal=True)

uploaded_files = st.file_uploader(
    "📤 Upload Link Budget PDF", type="pdf", accept_multiple_files=True)

preview_fields = [
    "systemConfigDeviceName",
    "systemDeviceLocLatitude",
    "systemDeviceLocLongitude",
    "systemDeviceLocHeight",
    "wirelessInterfaceSSID",
    "wirelessInterfaceScanFrequencyBandwidth",
    "wirelessInterfaceTXPower",
    "centerFrequency",
    "snmpSystemName",
    "snmpSystemDescription"
]

# -----------------------------
# 🔹 Processing Files
# -----------------------------
required_fields = {
    "AP IP": ap_ip,
    "SM IP": sm_ip,
    "Gateway IP": common_gateway,
    "Subnet Mask": common_netmask,
    "Management VLAN": common_vlan
}
all_fields_filled = all(required_fields.values())

if uploaded_files:
    for uploaded_file in uploaded_files:

        extracted_data = extract_full_system_names(uploaded_file)
        ap_json, sm_json = split_to_json_objects(extracted_data)

        if all_fields_filled:
            # Apply IPs and common fields
            ap_json["networkBridgeIPAddr"] = ap_ip
            sm_json["networkBridgeIPAddr"] = sm_ip
            for key, value in {
                "networkBridgeGatewayIP": common_gateway,
                "networkBridgeNetmask": common_netmask,
                "mgmtVLANVID": common_vlan
            }.items():
                ap_json[key] = value
                sm_json[key] = value

            if sm_data_vlan:
                sm_json["dataVLANVID"] = sm_data_vlan
            sm_json["dataVLANEnable"] = "1" if sm_data_vlan_enable == "Enable" else "0"
            ap_json["wirelessInterfaceProtocolMode"] = "4" if ap_protocol_mode == "PtP" else "1"

            st.success("✅ Configuration Success !")

            # Preview function
            def build_preview(json_data):
                return {k: preview_bandwidth(v) if k == "wirelessInterfaceScanFrequencyBandwidth" else v
                        for k, v in json_data.items() if k in preview_fields}

            cols = st.columns(2)
            with cols[0]:
                st.write("### AP Preview")
                st.json(build_preview(ap_json))
            with cols[1]:
                st.write("### SM Preview")
                st.json(build_preview(sm_json))

            # Download buttons (enabled)
            st.download_button(
                "💾 AP Config",
                json.dumps({"device_props": ap_json}, indent=4),
                file_name="ap.json",
                mime="application/json",
                disabled=False
            )
            st.download_button(
                "💾 SM Config",
                json.dumps({"device_props": sm_json}, indent=4),
                file_name="sm.json",
                mime="application/json",
                disabled=False
            )
        else:
            st.warning(
                "⚠️ Please fill all required fields:\n" +
                ", ".join(
                    [name for name, val in required_fields.items() if not val])
            )
            # Show disabled download buttons
            st.download_button(
                "💾 AP Config",
                "{}",
                file_name="ap.json",
                mime="application/json",
                disabled=True
            )
            st.download_button(
                "💾 SM Config",
                "{}",
                file_name="sm.json",
                mime="application/json",
                disabled=True
            )
