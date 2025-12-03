import streamlit as st
import requests
from dataclasses import dataclass
from typing import Optional

# Page config
st.set_page_config(
    page_title="DARALEX P&L Calculator",
    page_icon="🌻",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Translations
TRANSLATIONS = {
    "en": {
        "title": "🌻 DARALEX P&L Calculator",
        "mode": "Calculation Mode",
        "buying": "BUYING (Backwardation)",
        "selling": "SELLING (Forwardation)",
        "market_price": "Market Price (EUR/t)",
        "supplier_price": "Supplier Price (USD/t)",
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
    },
    "ro": {
        "title": "🌻 DARALEX Calculator P&L",
        "mode": "Mod Calcul",
        "buying": "CUMPĂRARE (Backwardation)",
        "selling": "VÂNZARE (Forwardation)",
        "market_price": "Preț Piață (EUR/t)",
        "supplier_price": "Preț Furnizor (USD/t)",
        "target_profit": "Profit Țintă (EUR/t)",
        "quantity": "Cantitate (tone)",
        "transport": "Transport (USD/t)",
        "loss": "Pierdere (kg/camion)",
        "broker": "Comision Broker (EUR/t)",
        "customs": "Cost Vamă (EUR/t)",
        "vat": "TVA %",
        "eur_usd": "Curs EUR/USD",
        "eur_mdl": "Curs EUR/MDL",
        "calculate": "🧮 CALCULEAZĂ",
        "results": "✅ REZULTATE",
        "max_buy": "Preț Max Cumpărare",
        "min_sell": "Preț Min Vânzare",
        "profit_truck": "Profit per Camion (24t)",
        "total_profit": "Profit Total Contract",
        "margin": "Marjă",
        "copy": "📋 Copiază",
        "auto_rates": "↻ Rate Auto",
        "rates": "Cursuri Valutare",
        "inputs": "Parametri Tranzacție",
        "costs": "Costuri",
        "your_offer": "Oferta Ta Reală",
        "your_price": "Prețul Tău (EUR/t)",
        "your_profit": "Profitul Tău/t",
        "price_truck": "Preț per Camion (24t)",
    },
    "ua": {
        "title": "🌻 DARALEX Калькулятор P&L",
        "mode": "Режим Розрахунку",
        "buying": "КУПІВЛЯ (Backwardation)",
        "selling": "ПРОДАЖ (Forwardation)",
        "market_price": "Ринкова Ціна (EUR/т)",
        "supplier_price": "Ціна Постачальника (USD/т)",
        "target_profit": "Цільовий Прибуток (EUR/т)",
        "quantity": "Кількість (тонн)",
        "transport": "Транспорт (USD/т)",
        "loss": "Втрати (кг/вантажівка)",
        "broker": "Комісія Брокера (EUR/т)",
        "customs": "Митні Витрати (EUR/т)",
        "vat": "ПДВ %",
        "eur_usd": "Курс EUR/USD",
        "eur_mdl": "Курс EUR/MDL",
        "calculate": "🧮 РОЗРАХУВАТИ",
        "results": "✅ РЕЗУЛЬТАТИ",
        "max_buy": "Макс Ціна Купівлі",
        "min_sell": "Мін Ціна Продажу",
        "profit_truck": "Прибуток за Вантажівку (24т)",
        "total_profit": "Загальний Прибуток Контракту",
        "margin": "Маржа",
        "copy": "📋 Копіювати",
        "auto_rates": "↻ Авто Курси",
        "rates": "Курси Валют",
        "inputs": "Параметри Угоди",
        "costs": "Витрати",
        "your_offer": "Твоя Реальна Пропозиція",
        "your_price": "Твоя Ціна (EUR/т)",
        "your_profit": "Твій Прибуток/т",
        "price_truck": "Ціна за Вантажівку (24т)",
    }
}

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

def calculate_backwardation(
    market_price_eur: float,
    target_profit_eur: float,
    eur_usd: float,
    eur_mdl: float,
    transport_usd: float,
    loss_kg: float,
    broker_eur: float,
    customs_eur: float,
    quantity_t: float,
    vat_rate: float
) -> PnLResult:
    """Calculate max buying price given market sell price (BACKWARDATION)"""
    
    # Total costs in EUR
    total_costs_eur = target_profit_eur + broker_eur + customs_eur
    
    # Convert to USD
    total_costs_usd = market_price_eur * eur_usd
    
    # Subtract transport
    after_transport = total_costs_usd - transport_usd
    
    # Adjust for loss (loss_kg per 24t truck)
    loss_factor = 1 - (loss_kg / 24000)
    max_buy_usd = after_transport * loss_factor
    
    # Subtract costs
    max_buy_usd = max_buy_usd - (total_costs_eur * eur_usd) + (target_profit_eur * eur_usd)
    
    # Simpler calculation matching Excel logic
    cost_total_eur = market_price_eur - target_profit_eur
    cost_usd = cost_total_eur * eur_usd
    minus_transport = cost_usd - transport_usd
    adjusted_for_loss = minus_transport * loss_factor
    max_buy_usd = adjusted_for_loss - (broker_eur * eur_usd) - (customs_eur * eur_usd)
    
    # Convert to other currencies
    max_buy_eur = max_buy_usd / eur_usd
    max_buy_mdl = max_buy_eur * eur_mdl
    max_buy_mdl_vat = max_buy_mdl * (1 + vat_rate)
    
    # Profit calculations
    profit_per_truck = target_profit_eur * 24
    total_profit = target_profit_eur * quantity_t
    margin_pct = target_profit_eur / cost_total_eur if cost_total_eur > 0 else 0
    
    return PnLResult(
        price_usd=max_buy_usd,
        price_eur=max_buy_eur,
        price_mdl=max_buy_mdl,
        price_mdl_vat=max_buy_mdl_vat,
        profit_per_ton=target_profit_eur,
        profit_per_truck=profit_per_truck,
        total_profit=total_profit,
        margin_pct=margin_pct
    )

def calculate_forwardation(
    supplier_price_usd: float,
    target_profit_eur: float,
    eur_usd: float,
    eur_mdl: float,
    transport_usd: float,
    loss_kg: float,
    broker_eur: float,
    customs_eur: float,
    quantity_t: float,
    vat_rate: float
) -> PnLResult:
    """Calculate min selling price given supplier offer (FORWARDATION)"""
    
    # Adjust supplier price for loss
    loss_factor = 1 + (loss_kg / 24000)
    adjusted_price = supplier_price_usd * loss_factor
    
    # Add transport
    with_transport = adjusted_price + transport_usd
    
    # Convert to EUR
    price_eur = with_transport / eur_usd
    
    # Add costs
    total_cost_eur = price_eur + broker_eur + customs_eur
    
    # Add profit for min sell price
    min_sell_eur = total_cost_eur + target_profit_eur
    min_sell_usd = min_sell_eur * eur_usd
    min_sell_mdl = min_sell_eur * eur_mdl
    min_sell_mdl_vat = min_sell_mdl * (1 + vat_rate)
    
    # Profit calculations
    profit_per_truck = target_profit_eur * 24
    total_profit = target_profit_eur * quantity_t
    margin_pct = target_profit_eur / total_cost_eur if total_cost_eur > 0 else 0
    
    return PnLResult(
        price_usd=min_sell_usd,
        price_eur=min_sell_eur,
        price_mdl=min_sell_mdl,
        price_mdl_vat=min_sell_mdl_vat,
        profit_per_ton=target_profit_eur,
        profit_per_truck=profit_per_truck,
        total_profit=total_profit,
        margin_pct=margin_pct
    )

def fetch_exchange_rates():
    """Fetch current exchange rates"""
    try:
        # Try to get EUR/USD from exchangerate-api
        response = requests.get(
            "https://api.exchangerate-api.com/v4/latest/EUR",
            timeout=5
        )
        data = response.json()
        eur_usd = data["rates"]["USD"]
        eur_mdl = data["rates"].get("MDL", 19.74)
        return eur_usd, eur_mdl
    except:
        return 1.08, 19.74  # Default fallback

def format_number(num: float, decimals: int = 2) -> str:
    """Format number with thousand separators"""
    return f"{num:,.{decimals}f}"

# Initialize session state
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "eur_usd" not in st.session_state:
    st.session_state.eur_usd = 1.08
if "eur_mdl" not in st.session_state:
    st.session_state.eur_mdl = 19.74

# Get translations
t = TRANSLATIONS[st.session_state.lang]

# Custom CSS
st.markdown("""
<style>
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    .result-box {
        background: linear-gradient(135deg, #1a5f2a 0%, #2d8f4a 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .result-value {
        font-size: 24px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
    }
</style>
""", unsafe_allow_html=True)

# Header with language selector
col_title, col_lang = st.columns([4, 1])
with col_title:
    st.title(t["title"])
with col_lang:
    lang = st.selectbox(
        "🌐",
        options=["en", "ro", "ua"],
        format_func=lambda x: {"en": "EN", "ro": "RO", "ua": "UA"}[x],
        index=["en", "ro", "ua"].index(st.session_state.lang),
        label_visibility="collapsed"
    )
    if lang != st.session_state.lang:
        st.session_state.lang = lang
        st.rerun()

# Mode selection
mode = st.radio(
    t["mode"],
    options=["buying", "selling"],
    format_func=lambda x: t[x],
    horizontal=True
)

st.divider()

# Exchange rates section
with st.expander(t["rates"], expanded=False):
    col_rates1, col_rates2, col_auto = st.columns([2, 2, 1])
    
    with col_rates1:
        eur_usd = st.number_input(
            t["eur_usd"],
            value=st.session_state.eur_usd,
            min_value=0.5,
            max_value=2.0,
            step=0.001,
            format="%.4f"
        )
    
    with col_rates2:
        eur_mdl = st.number_input(
            t["eur_mdl"],
            value=st.session_state.eur_mdl,
            min_value=10.0,
            max_value=30.0,
            step=0.01,
            format="%.2f"
        )
    
    with col_auto:
        st.write("")
        st.write("")
        if st.button(t["auto_rates"]):
            with st.spinner("..."):
                new_eur_usd, new_eur_mdl = fetch_exchange_rates()
                st.session_state.eur_usd = new_eur_usd
                st.session_state.eur_mdl = new_eur_mdl
                st.rerun()

# Main inputs
st.subheader(t["inputs"])

col1, col2 = st.columns(2)

with col1:
    if mode == "buying":
        price_input = st.number_input(
            t["market_price"],
            value=1310.0,
            min_value=0.0,
            max_value=5000.0,
            step=5.0
        )
    else:
        price_input = st.number_input(
            t["supplier_price"],
            value=1170.0,
            min_value=0.0,
            max_value=5000.0,
            step=5.0
        )
    
    quantity = st.number_input(
        t["quantity"],
        value=100.0,
        min_value=1.0,
        max_value=10000.0,
        step=10.0
    )

with col2:
    target_profit = st.number_input(
        t["target_profit"],
        value=35.0 if mode == "selling" else 85.0,
        min_value=0.0,
        max_value=500.0,
        step=5.0
    )
    
    transport = st.number_input(
        t["transport"],
        value=85.0 if mode == "selling" else 125.0,
        min_value=0.0,
        max_value=500.0,
        step=5.0
    )

# Costs section
with st.expander(t["costs"], expanded=False):
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        loss_kg = st.number_input(
            t["loss"],
            value=10.0 if mode == "buying" else 100.0,
            min_value=0.0,
            max_value=500.0,
            step=5.0
        )
        broker = st.number_input(
            t["broker"],
            value=30.0 if mode == "buying" else 0.0,
            min_value=0.0,
            max_value=100.0,
            step=1.0
        )
    
    with col_c2:
        customs = st.number_input(
            t["customs"],
            value=2.0,
            min_value=0.0,
            max_value=50.0,
            step=0.5
        )
        vat = st.number_input(
            t["vat"],
            value=20.0,
            min_value=0.0,
            max_value=30.0,
            step=1.0
        ) / 100

st.divider()

# Calculate button
if st.button(t["calculate"], type="primary", use_container_width=True):
    
    if mode == "buying":
        result = calculate_backwardation(
            market_price_eur=price_input,
            target_profit_eur=target_profit,
            eur_usd=eur_usd,
            eur_mdl=eur_mdl,
            transport_usd=transport,
            loss_kg=loss_kg,
            broker_eur=broker,
            customs_eur=customs,
            quantity_t=quantity,
            vat_rate=vat
        )
        price_label = t["max_buy"]
    else:
        result = calculate_forwardation(
            supplier_price_usd=price_input,
            target_profit_eur=target_profit,
            eur_usd=eur_usd,
            eur_mdl=eur_mdl,
            transport_usd=transport,
            loss_kg=loss_kg,
            broker_eur=broker,
            customs_eur=customs,
            quantity_t=quantity,
            vat_rate=vat
        )
        price_label = t["min_sell"]
    
    st.subheader(t["results"])
    
    # Main result metrics
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        st.metric(
            f"{price_label} (USD)",
            f"${format_number(result.price_usd)}"
        )
    with col_r2:
        st.metric(
            f"{price_label} (EUR)",
            f"€{format_number(result.price_eur)}"
        )
    with col_r3:
        st.metric(
            f"{price_label} (MDL)",
            f"{format_number(result.price_mdl)} MDL"
        )
    
    # Additional metrics
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.metric(
            t["profit_truck"],
            f"€{format_number(result.profit_per_truck, 0)}"
        )
    with col_p2:
        st.metric(
            t["total_profit"],
            f"€{format_number(result.total_profit, 0)}"
        )
    with col_p3:
        st.metric(
            t["margin"],
            f"{result.margin_pct * 100:.1f}%"
        )
    
    # MDL with VAT
    st.info(f"MDL + TVA: **{format_number(result.price_mdl_vat)} MDL**")
    
    # Copy text
    copy_text = f"""
{price_label}: {format_number(result.price_usd)} USD | {format_number(result.price_eur)} EUR | {format_number(result.price_mdl)} MDL
Profit/Truck: €{format_number(result.profit_per_truck, 0)} | Total: €{format_number(result.total_profit, 0)} | Margin: {result.margin_pct * 100:.1f}%
Rates: EUR/USD {eur_usd} | EUR/MDL {eur_mdl}
    """.strip()
    
    st.code(copy_text, language=None)

# Footer
st.divider()
st.caption("© 2024 DARALEX AGRO | Vegetable Oil Trading")
