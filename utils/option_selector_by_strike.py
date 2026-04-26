import os
from get_keys import load_valid_dhan_credentials
from dhanhq import dhanhq

# reuse same env style
BASIC_LOGS = os.getenv("BASIC_LOGS", "false").lower() == "true"


def log(msg):
    if BASIC_LOGS:
        print(msg)


def log_line():
    if BASIC_LOGS:
        print("-" * 40)

def adjust_strike(base_strike, option_type, shift_enabled, shift_points=1000):
    if not shift_enabled:
        return base_strike

    if option_type == "buyCE":
        return base_strike + shift_points
    elif option_type == "buyPE":
        return base_strike - shift_points
    return base_strike


def get_option_contract_by_strike(security_id, option_type, target_strike):
    """
    NEW FUNCTION (DOES NOT TOUCH EXISTING CODE)

    security_id → index (13 / 51)
    option_type → buyCE / buyPE
    target_strike → from TradingView message
    """

    try:
        log_line()
        log(f"🔍 Strike-Based Contract | SecID={security_id} | Type={option_type} | Strike={target_strike}")

        # -----------------------------
        # 🔐 STEP 0: Credentials
        # -----------------------------
        log_line()

        creds = load_valid_dhan_credentials()

        if not creds:
            return {"error": "No valid credentials"}

        dhan_instance = dhanhq(creds['client_id'], creds['access_token'])

        # -----------------------------
        # 📅 STEP 1: Expiry
        # -----------------------------
        log_line()

        expiry_data = dhan_instance.expiry_list(
            under_security_id=int(security_id),
            under_exchange_segment="IDX_I"
        )

        expiry_list = expiry_data.get("data", {}).get("data", [])

        if not expiry_list:
            return {"error": "No expiry data"}

        expiry = expiry_list[0]
        log(f"✅ Selected Expiry: {expiry}")

        # -----------------------------
        # 📊 STEP 2: Option Chain
        # -----------------------------
        log_line()

        oc = dhan_instance.option_chain(
            under_security_id=int(security_id),
            under_exchange_segment="IDX_I",
            expiry=expiry
        )

        oc_map = oc.get("data", {}).get("data", {}).get("oc", {})

        if not oc_map:
            return {"error": "Invalid option chain"}

        # -----------------------------
        # 🎯 STEP 3: USE MESSAGE STRIKE
        # -----------------------------
        log_line()

        strike_key = f"{float(target_strike):.6f}"

        if strike_key not in oc_map:
            return {"error": f"Strike {target_strike} not found"}

        strike_data = oc_map[strike_key]

        ce = strike_data.get("ce", {})
        pe = strike_data.get("pe", {})

        # -----------------------------
        # 🧾 STEP 4: Select Contract
        # -----------------------------
        log_line()

        if option_type == "buyCE":
            sec_id = ce.get("security_id")
            price = ce.get("last_price")

        elif option_type == "buyPE":
            sec_id = pe.get("security_id")
            price = pe.get("last_price")

        else:
            return {"error": "Invalid option type"}

        # -----------------------------
        # ❌ VALIDATION
        # -----------------------------
        log_line()

        if not sec_id or price is None:
            return {"error": "Invalid contract data"}

        log(f"✅ FINAL CONTRACT → SecID: {sec_id}, Price: {price}")

        # -----------------------------
        # ✅ FINAL RESPONSE (PRINT PURPOSE)
        # -----------------------------
        log_line()

        return {
            "security_id": sec_id,
            "price": price,
            "strike": target_strike,
            "option_type": option_type,
            "expiry": expiry
        }

    except Exception as e:
        print(f"❌ Exception in get_option_contract_by_strike: {str(e)}")
        return {"error": str(e)}