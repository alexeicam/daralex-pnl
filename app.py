import streamlit as st
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Optional import for Refinitiv
try:
    import refinitiv.data as rd
    REFINITIV_AVAILABLE = True
except ImportError:
    REFINITIV_AVAILABLE = False

# Import our enhanced calculator
try:
    from pnl_calculator import EnhancedVegetableOilCalculator, EnhancedPnLResult
    from hubspot_integration import (
        display_hubspot_status,
        render_deal_tracking_section,
        render_deals_log,
        StreamlitHubSpotIntegration
    )
    ENHANCED_MODE = True
except ImportError:
    ENHANCED_MODE = False
    st.warning("⚠️ Enhanced features not available. Using basic mode.")

# Page config
st.set_page_config(
    page_title="DARALEX P&L Calculator",
    page_icon="🌻",
    layout="wide",  # Changed to wide for better layout
    initial_sidebar_state="expanded"  # Show sidebar for enhanced features
)

# Initialize enhanced calculator if available
if ENHANCED_MODE:
    enhanced_calculator = EnhancedVegetableOilCalculator()

# Translations (keeping your existing translations)
TRANSLATIONS = {
    "en": {
        "title": "🌻 DARALEX P&L Calculator",
        "mode": "Calculation Mode",
        "buying": "BUYING (Backwardation)",
        "selling": "SELLING (Forwardation)",
        "market_price": "Market Price (EUR/t)",
        "supplier_price": "Supplier Price",
        "supplier_currency": "Supplier Currency",
        "target_profit": "Target Profit (EUR/t)",
        "quantity": "Quantity (tons)",
        "transport": "Transport (USD/t)",
        "loss": "Loss (kg/truck)",
        "broker": "Broker Commission (EUR/t)",
        "customs": "Customs Cost (EUR/t)",
        "vat": "VAT %",
        "eur_usd": "EUR/USD Rate",
        "eur_mdl": "EUR/MDL Rate",
        "calculate": "🧮 CALCULATE",
        "results": "✅ RESULTS",
        "max_buy": "Max Buy Price",
        "min_sell": "Min Sell Price",
        "profit_truck": "Profit per Truck (24t)",
        "total_profit": "Total Contract Profit",
        "margin": "Margin",
        "copy": "📋 Copy Results",
        "auto_rates": "↻ Auto Rates",
        "rates": "Exchange Rates",
        "inputs": "Deal Parameters",
        "costs": "Costs",
        "your_offer": "Your Actual Offer",
        "your_price": "Your Price (EUR/t)",
        "your_profit": "Your Profit/t",
        "price_truck": "Price per Truck (24t)",
        "deal_tracking": "Deal Tracking",
        "recent_deals": "Recent Deals",
        "product_type": "Product Type",
        "select_buyer": "Select Buyer",
        "select_seller": "Select Seller",
        "deal_name": "Deal Name",
        "save_deal": "💾 Save Deal to HubSpot",
        "refresh_companies": "🔄 Refresh Companies",
        "add_new_company": "➕ Add New Company",
        "new_buyer_name": "New Buyer Name",
        "new_seller_name": "New Seller Name",
        "country": "Country",
        "create_buyer": "Create Buyer",
        "create_seller": "Create Seller",
        "refresh_deals": "🔄 Refresh Deals",
        "no_deals": "No recent deals found.",
        "date": "Date",
        "product": "Product",
        "deal": "Deal",
        "quantity": "Quantity",
        "profit": "Profit",
        "margin": "Margin",
        "stage": "Stage",
        "save_changes": "💾 Save Changes",
        "sync_hubspot": "🔄 Sync to HubSpot",
        "edit_deals": "**Edit deals by clicking on cells:**",
        "stage_appointment": "Appointment Scheduled",
        "stage_qualified": "Qualified To Buy",
        "stage_presentation": "Presentation Scheduled",
        "stage_decision": "Decision Maker Bought-In",
        "stage_contract": "Contract Sent",
        "stage_won": "Closed Won",
        "stage_lost": "Closed Lost",
        "refresh_deals": "🔄 Manual Refresh",
        "auto_refresh_in": "🔄 Auto-refresh in",
        "auto_refreshing": "🔄 Auto-refreshing...",
        "auto_refresh_paused": "⏸️ Auto-refresh paused",
        "pause_auto": "⏸️ Pause Auto",
        "enable_auto": "▶️ Enable Auto",
    },
    "ro": {
        "title": "🌻 DARALEX Calculator P&L",
        "mode": "Modul de Calcul",
        "buying": "CUMPĂRARE (Backwardation)",
        "selling": "VÂNZARE (Forwardation)",
        "market_price": "Preț Piață (EUR/t)",
        "supplier_price": "Preț Furnizor",
        "supplier_currency": "Moneda Furnizor",
        "target_profit": "Profit Țintă (EUR/t)",
        "quantity": "Cantitate (tone)",
        "transport": "Transport (USD/t)",
        "loss": "Pierderi (kg/camion)",
        "broker": "Comision Broker (EUR/t)",
        "customs": "Cost Vamal (EUR/t)",
        "vat": "TVA %",
        "eur_usd": "Curs EUR/USD",
        "eur_mdl": "Curs EUR/MDL",
        "calculate": "🧮 CALCULEAZĂ",
        "results": "REZULTATE",
        "max_buy": "Preț Max Cumpărare",
        "min_sell": "Preț Min Vânzare",
        "profit_truck": "Profit per Camion (24t)",
        "total_profit": "Profit Total Contract",
        "margin": "Marjă",
        "copy": "📋 Copiază Rezultate",
        "auto_rates": "↻ Cursuri Auto",
        "rates": "Cursuri Valutare",
        "inputs": "Parametri Tranzacție",
        "costs": "Costuri",
        "your_offer": "Oferta Ta Reală",
        "your_price": "Prețul Tău (EUR/t)",
        "your_profit": "Profitul Tău/t",
        "price_truck": "Preț per Camion (24t)",
        "deal_tracking": "Urmărire Tranzacții",
        "recent_deals": "Tranzacții Recente",
        "product_type": "Tip Produs",
        "select_buyer": "Selectează Cumpărător",
        "select_seller": "Selectează Vânzător",
        "deal_name": "Nume Tranzacție",
        "save_deal": "💾 Salvează în HubSpot",
        "refresh_companies": "🔄 Reîmprospătează Companii",
        "add_new_company": "➕ Adaugă Companie Nouă",
        "new_buyer_name": "Nume Cumpărător Nou",
        "new_seller_name": "Nume Vânzător Nou",
        "country": "Țară",
        "create_buyer": "Creează Cumpărător",
        "create_seller": "Creează Vânzător",
        "refresh_deals": "🔄 Reîmprospătează Tranzacții",
        "no_deals": "Nu s-au găsit tranzacții recente.",
        "date": "Data",
        "product": "Produs",
        "deal": "Tranzacție",
        "quantity": "Cantitate",
        "profit": "Profit",
        "margin": "Marjă",
        "stage": "Stadiu",
        "save_changes": "💾 Salvează Modificări",
        "sync_hubspot": "🔄 Sincronizează cu HubSpot",
        "edit_deals": "**Editează tranzacțiile făcând clic pe celule:**",
        "stage_appointment": "Întâlnire Programată",
        "stage_qualified": "Calificat Pentru Cumpărare",
        "stage_presentation": "Prezentare Programată",
        "stage_decision": "Factorul Decizional Convins",
        "stage_contract": "Contract Trimis",
        "stage_won": "Câștigat",
        "stage_lost": "Pierdut",
        "refresh_deals": "🔄 Reîmprospătare Manuală",
        "auto_refresh_in": "🔄 Auto-reîmprospătare în",
        "auto_refreshing": "🔄 Se auto-reîmprospătează...",
        "auto_refresh_paused": "⏸️ Auto-reîmprospătare întreruptă",
        "pause_auto": "⏸️ Pauză Auto",
        "enable_auto": "▶️ Activează Auto",
    }
}

# Your existing calculation classes (keeping for compatibility)
@dataclass
class PnLResult:
    price_usd: float
    price_eur: float
    price_mdl: float
    price_mdl_vat: float
    profit_per_ton: float
    profit_per_truck: float
    total_profit: float
    margin_pct: float

# Enhanced sidebar with new features
def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎯 Enhanced Features")

        # Language selector (keeping your existing feature)
        lang = st.selectbox("🌐 Language / Limba", ["en", "ro"], index=1, key="lang")

        # HubSpot integration status
        if ENHANCED_MODE:
            hubspot_connected = display_hubspot_status()
        else:
            st.info("💡 Install enhanced mode for HubSpot integration")

        # Calculation mode toggle
        st.markdown("---")
        enhanced_mode = st.checkbox("🚀 Enhanced Mode", value=ENHANCED_MODE, disabled=not ENHANCED_MODE)

        if enhanced_mode and ENHANCED_MODE:
            st.success("✅ Enhanced calculations active")
            show_sensitivity = st.checkbox("📊 Sensitivity Analysis")
            show_breakdown = st.checkbox("📋 Cost Breakdown")
        else:
            st.info("ℹ️ Basic calculation mode")
            show_sensitivity = False
            show_breakdown = False

        return lang, enhanced_mode if ENHANCED_MODE else False, show_sensitivity, show_breakdown

# Your existing functions (keeping them for compatibility)
def calculate_backwardation(market_price_eur, target_profit_eur, eur_usd, eur_mdl,
                          transport_usd, loss_kg, broker_eur, customs_eur, quantity_t, vat_rate):
    """Your existing backwardation calculation"""
    # [Your existing calculation logic - keeping it exactly as is]
    total_costs_eur = target_profit_eur + broker_eur + customs_eur
    total_costs_usd = market_price_eur * eur_usd
    after_transport = total_costs_usd - transport_usd
    loss_factor = 1 - (loss_kg / 24000)
    max_buy_usd = after_transport * loss_factor
    max_buy_usd = max_buy_usd - (total_costs_eur * eur_usd) + (target_profit_eur * eur_usd)

    cost_total_eur = market_price_eur - target_profit_eur
    cost_usd = cost_total_eur * eur_usd
    minus_transport = cost_usd - transport_usd
    adjusted_for_loss = minus_transport * loss_factor
    max_buy_usd = adjusted_for_loss - (broker_eur * eur_usd) - (customs_eur * eur_usd)

    max_buy_eur = max_buy_usd / eur_usd
    max_buy_mdl = max_buy_eur * eur_mdl
    max_buy_mdl_vat = max_buy_mdl * (1 + vat_rate)

    profit_per_truck = target_profit_eur * 24
    total_profit = target_profit_eur * quantity_t
    margin_pct = target_profit_eur / cost_total_eur if cost_total_eur > 0 else 0

    return PnLResult(
        price_usd=max_buy_usd, price_eur=max_buy_eur, price_mdl=max_buy_mdl,
        price_mdl_vat=max_buy_mdl_vat, profit_per_ton=target_profit_eur,
        profit_per_truck=profit_per_truck, total_profit=total_profit, margin_pct=margin_pct
    )

def calculate_forwardation(supplier_price, supplier_currency, target_profit_eur, eur_usd, eur_mdl,
                         transport_usd, loss_kg, broker_eur, customs_eur, quantity_t, vat_rate):
    """Enhanced forwardation calculation supporting USD and EUR supplier prices"""

    # Convert supplier price to EUR if needed
    if supplier_currency == "USD":
        supplier_price_eur = supplier_price / eur_usd
    else:  # EUR
        supplier_price_eur = supplier_price

    transport_eur = transport_usd / eur_usd

    total_cost_eur = supplier_price_eur + transport_eur + broker_eur + customs_eur
    loss_factor = 1 + (loss_kg / 24000)
    adjusted_cost_eur = total_cost_eur * loss_factor
    min_sell_eur = adjusted_cost_eur + target_profit_eur

    min_sell_usd = min_sell_eur * eur_usd
    min_sell_mdl = min_sell_eur * eur_mdl
    min_sell_mdl_vat = min_sell_mdl * (1 + vat_rate)

    profit_per_truck = target_profit_eur * 24
    total_profit = target_profit_eur * quantity_t
    margin_pct = target_profit_eur / adjusted_cost_eur if adjusted_cost_eur > 0 else 0

    return PnLResult(
        price_usd=min_sell_usd, price_eur=min_sell_eur, price_mdl=min_sell_mdl,
        price_mdl_vat=min_sell_mdl_vat, profit_per_ton=target_profit_eur,
        profit_per_truck=profit_per_truck, total_profit=total_profit, margin_pct=margin_pct
    )

def get_fallback_rates():
    """Your existing exchange rate fetching"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data["rates"].get("USD", 1.164), data["rates"].get("MDL", 19.5), "fallback"
        return 1.164, 19.5, "fallback"
    except:
        return 1.164, 19.5, "fallback"

def get_refinitiv_rates():
    if not REFINITIV_AVAILABLE:
        return get_fallback_rates()

    try:
        rd.open_session()  # Auto-reads config file
        df = rd.get_data(["EUR=", "EURMDL=R"], fields=["BID", "ASK"])
        rd.close_session()
        eur_usd = df.loc["EUR=", "BID"]
        eur_mdl = df.loc["EURMDL=R", "BID"]
        return float(eur_usd), float(eur_mdl), "refinitiv"
    except Exception as e:
        return get_fallback_rates()

def format_number(num: float, decimals: int = 2) -> str:
    """Your existing number formatting"""
    return f"{num:,.{decimals}f}"

def main():
    # Render sidebar and get settings
    lang, enhanced_mode, show_sensitivity, show_breakdown = render_sidebar()
    t = TRANSLATIONS[lang]

    # Main title
    st.title(t["title"])

    if enhanced_mode:
        st.info("🚀 **Enhanced Mode Active** - Advanced calculations with detailed breakdowns")

    # Mode selection
    mode = st.radio(t["mode"], [t["buying"], t["selling"]], horizontal=True)
    is_buying = mode == t["buying"]

    # Create main layout
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📊 " + t["inputs"])

        # Price input (different for buying vs selling)
        if is_buying:
            price = st.number_input(t["market_price"], min_value=0.0, value=1310.0, step=10.0)
            supplier_currency = "EUR"  # Not used for buying
        else:
            col_price, col_currency = st.columns([3, 1])
            with col_currency:
                supplier_currency = st.selectbox(
                    t["supplier_currency"],
                    ["USD", "EUR"],
                    key="supplier_currency_selector"
                )
            with col_price:
                currency_symbol = "$" if supplier_currency == "USD" else "€"
                default_price = 1225.0 if supplier_currency == "USD" else 1052.0
                price = st.number_input(
                    f"{t['supplier_price']} ({currency_symbol}/t)",
                    min_value=0.0,
                    value=default_price,
                    step=10.0
                )

        # Common inputs
        target_profit = st.number_input(t["target_profit"], min_value=0.0, value=85.0, step=5.0)
        quantity = st.number_input(t["quantity"], min_value=1.0, value=250.0, step=10.0)

        st.subheader("💰 " + t["costs"])

        col_cost1, col_cost2 = st.columns(2)
        with col_cost1:
            transport = st.number_input(t["transport"], min_value=0.0, value=125.0, step=5.0)
            broker = st.number_input(t["broker"], min_value=0.0, value=15.0, step=1.0)

        with col_cost2:
            customs = st.number_input(t["customs"], min_value=0.0, value=10.0, step=1.0)
            loss = st.number_input(t["loss"], min_value=0.0, value=200.0, step=10.0)

        st.subheader("💱 " + t["rates"])

        col_rate1, col_rate2, col_rate3 = st.columns(3)
        with col_rate1:
            if st.button(t["auto_rates"]):
                eur_usd_auto, eur_mdl_auto, source = get_refinitiv_rates()
                st.session_state.eur_usd = eur_usd_auto
                st.session_state.eur_mdl = eur_mdl_auto
                if source == "refinitiv":
                    st.success(f"📡 Refinitiv Live @ {datetime.now().strftime('%H:%M:%S')}")
                else:
                    st.warning("🌐 Market Rate")


        with col_rate2:
            eur_usd = st.number_input(t["eur_usd"], min_value=0.1, value=st.session_state.get("eur_usd", 1.164), step=0.001, format="%.3f")

        with col_rate3:
            eur_mdl = st.number_input(t["eur_mdl"], min_value=0.1, value=st.session_state.get("eur_mdl", 19.5), step=0.1)

        vat = st.slider(t["vat"], min_value=0.0, max_value=30.0, value=20.0, step=0.5) / 100

    with col2:
        # Calculate button
        if st.button(t["calculate"], type="primary", use_container_width=True):

            # Prepare calculation parameters
            calc_params = {
                "target_profit_eur": target_profit,
                "eur_usd": eur_usd,
                "eur_mdl": eur_mdl,
                "transport_usd": transport,
                "loss_kg": loss,
                "broker_eur": broker,
                "customs_eur": customs,
                "quantity_t": quantity,
                "vat_rate": vat
            }

            if is_buying:
                calc_params["market_price_eur"] = price
                calc_params["calculation_type"] = "backwardation"

                # Use enhanced calculator if available
                if enhanced_mode:
                    # Filter parameters for enhanced calculator
                    enhanced_params = {k: v for k, v in calc_params.items() if k != "calculation_type"}
                    result = enhanced_calculator.calculate_enhanced_backwardation(**enhanced_params)
                else:
                    # Use your existing calculation
                    result = calculate_backwardation(price, **{k: v for k, v in calc_params.items() if k not in ["market_price_eur", "calculation_type"]})
            else:
                calc_params["supplier_price"] = price
                calc_params["supplier_currency"] = supplier_currency
                calc_params["calculation_type"] = "forwardation"

                if enhanced_mode:
                    # Filter parameters for enhanced calculator
                    enhanced_params = {k: v for k, v in calc_params.items() if k != "calculation_type"}
                    # Convert for enhanced calculator (still expects USD)
                    if supplier_currency == "EUR":
                        enhanced_params["supplier_price_usd"] = price * eur_usd
                    else:
                        enhanced_params["supplier_price_usd"] = price
                    result = enhanced_calculator.calculate_enhanced_forwardation(**{k: v for k, v in enhanced_params.items() if k not in ["supplier_price", "supplier_currency"]})
                else:
                    result = calculate_forwardation(**{k: v for k, v in calc_params.items() if k != "calculation_type"})

            # Store results in session state
            st.session_state.last_result = result
            st.session_state.last_params = calc_params
            st.session_state.last_enhanced = enhanced_mode

    # Display results if available
    if hasattr(st.session_state, 'last_result'):
        result = st.session_state.last_result
        enhanced = st.session_state.get('last_enhanced', False)

        st.markdown("---")
        st.subheader("✅ " + t["results"])

        # Main results display
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)

        if is_buying:
            if enhanced:
                # Enhanced results
                with col_res1:
                    st.metric("💵 USD/t", f"${result.max_buy_usd:,.2f}")
                with col_res2:
                    st.metric("💶 EUR/t", f"€{result.max_buy_eur:,.2f}")
                with col_res3:
                    st.metric("🏦 MDL/t", f"L{result.max_buy_mdl:,.2f}")
                with col_res4:
                    st.metric("📊 Margin", f"{result.margin_pct:.2f}%")
            else:
                # Basic results
                with col_res1:
                    st.metric("💵 USD/t", f"${result.price_usd:,.2f}")
                with col_res2:
                    st.metric("💶 EUR/t", f"€{result.price_eur:,.2f}")
                with col_res3:
                    st.metric("🏦 MDL/t", f"L{result.price_mdl:,.2f}")
                with col_res4:
                    st.metric("📊 Margin", f"{result.margin_pct:.2f}%")
        else:
            if enhanced:
                with col_res1:
                    st.metric("💵 USD/t", f"${result.min_sell_usd:,.2f}")
                with col_res2:
                    st.metric("💶 EUR/t", f"€{result.min_sell_eur:,.2f}")
                with col_res3:
                    st.metric("🏦 MDL/t", f"L{result.min_sell_mdl:,.2f}")
                with col_res4:
                    st.metric("📊 Margin", f"{result.margin_pct:.2f}%")
            else:
                with col_res1:
                    st.metric("💵 USD/t", f"${result.price_usd:,.2f}")
                with col_res2:
                    st.metric("💶 EUR/t", f"€{result.price_eur:,.2f}")
                with col_res3:
                    st.metric("🏦 MDL/t", f"L{result.price_mdl:,.2f}")
                with col_res4:
                    st.metric("📊 Margin", f"{result.margin_pct:.2f}%")

        # Profit metrics
        st.markdown("### 💰 Profit Analysis")
        col_profit1, col_profit2, col_profit3 = st.columns(3)

        with col_profit1:
            st.metric("Per Ton", f"€{result.profit_per_ton:,.2f}")
        with col_profit2:
            st.metric("Per Truck (24t)", f"€{result.profit_per_truck:,.2f}")
        with col_profit3:
            st.metric("Total Contract", f"€{result.total_profit:,.2f}")

        # Enhanced features
        if enhanced and ENHANCED_MODE:

            # Cost breakdown
            if show_breakdown and hasattr(result, 'cost_breakdown'):
                with st.expander("📋 Detailed Cost Breakdown"):
                    breakdown = result.cost_breakdown
                    col_b1, col_b2 = st.columns(2)

                    with col_b1:
                        st.write("**Transport:** €{:.2f}/t".format(breakdown.get('transport_eur_per_ton', 0)))
                        st.write("**Broker:** €{:.2f}/t".format(breakdown.get('broker_eur_per_ton', 0)))
                        st.write("**Customs:** €{:.2f}/t".format(breakdown.get('customs_eur_per_ton', 0)))

                    with col_b2:
                        st.write("**Loss:** {:.1f}%".format(breakdown.get('loss_percentage', 0)))
                        st.write("**Effective Qty:** {:.1f}t".format(result.effective_quantity_tons))
                        st.write("**Breakeven:** €{:.2f}/t".format(result.breakeven_price_eur))

            # Sensitivity analysis
            if show_sensitivity:
                with st.expander("📊 Price Sensitivity Analysis"):
                    sensitivity = enhanced_calculator.sensitivity_analysis(result)

                    st.write("**Impact of price changes on profitability:**")

                    # Create a simple table
                    sens_data = sensitivity['price_sensitivity']
                    for item in sens_data[::2]:  # Show every other item to avoid clutter
                        col_s1, col_s2, col_s3 = st.columns(3)
                        with col_s1:
                            st.write(f"**{item['price_change']:+.0f} EUR/t**")
                        with col_s2:
                            st.write(f"€{item['profit_per_ton']:.2f}/t profit")
                        with col_s3:
                            st.write(f"{item['margin_pct']:.1f}% margin")

        # Deal Tracking Section (Enhanced Mode)
        if enhanced and ENHANCED_MODE:
            st.markdown("---")
            st.markdown(f"### 💼 {t['deal_tracking']}")

            # Render deal tracking interface
            render_deal_tracking_section(result.to_dict(), st.session_state.last_params, t)

    # Recent Deals Log (Always show if HubSpot is available)
    if ENHANCED_MODE:
        st.markdown("---")
        st.markdown(f"### 📊 {t['recent_deals']}")
        render_deals_log(StreamlitHubSpotIntegration(), t)

if __name__ == "__main__":
    main()