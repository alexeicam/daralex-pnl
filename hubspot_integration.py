#!/usr/bin/env python3
"""
HubSpot Integration for Streamlit P&L Calculator
"""

import os
import requests
import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from pnl_calculator import EnhancedVegetableOilCalculator

class StreamlitHubSpotIntegration:
    """
    HubSpot integration optimized for Streamlit apps
    Uses Streamlit secrets for secure token management
    """

    def __init__(self):
        # Try to get token from Streamlit secrets first, then environment
        try:
            self.access_token = st.secrets.get("HUBSPOT_ACCESS_TOKEN")
        except:
            self.access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")

        if not self.access_token:
            self.access_token = None

        self.base_url = "https://api.hubapi.com"
        self.calculator = EnhancedVegetableOilCalculator()

    @property
    def is_connected(self) -> bool:
        """Check if HubSpot connection is available"""
        return self.access_token is not None

    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test HubSpot API connection
        Returns status and basic account info
        """
        if not self.is_connected:
            return {
                "status": "error",
                "message": "No access token available",
                "connected": False
            }

        try:
            url = f"{self.base_url}/crm/v3/objects/deals"
            params = {"limit": 1}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "status": "success",
                "message": "Connected successfully",
                "connected": True,
                "total_deals": data.get("total", 0)
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "connected": False
            }

    def get_companies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch companies from HubSpot for buyer/seller selection
        """
        if not self.is_connected:
            return []

        try:
            url = f"{self.base_url}/crm/v3/objects/companies"
            params = {
                "limit": limit,
                "properties": "name,domain,country,industry,hs_object_id",
                "sorts": [{"propertyName": "name", "direction": "ASCENDING"}]
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            companies = data.get("results", [])

            # Format companies for display
            formatted_companies = []
            for company in companies:
                props = company.get("properties", {})
                formatted_companies.append({
                    "id": company.get("id"),
                    "name": props.get("name", "Unnamed Company"),
                    "domain": props.get("domain", ""),
                    "country": props.get("country", ""),
                    "industry": props.get("industry", "")
                })

            return formatted_companies

        except Exception as e:
            st.error(f"Error fetching companies: {str(e)}")
            return []

    def create_company(self, company_name: str, country: str = "Unknown") -> Optional[str]:
        """
        Create a new company in HubSpot
        """
        if not self.is_connected:
            st.warning("HubSpot not connected. Cannot create company.")
            return None

        try:
            url = f"{self.base_url}/crm/v3/objects/companies"

            # Prepare company properties
            company_properties = {
                "name": company_name,
                "country": country,
                "industry": "FOOD_PRODUCTION",
                "type": "PROSPECT",
                "hs_lead_status": "NEW",
                "created_by": "DARALEX_PnL_Calculator",
                "created_date": datetime.now().isoformat()
            }

            payload = {"properties": company_properties}

            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()

            company = response.json()
            company_id = company.get("id")

            st.success(f"✅ Company '{company_name}' created successfully!")
            return company_id

        except Exception as e:
            st.error(f"❌ Error creating company: {str(e)}")
            return None

    def create_deal_with_associations(self,
                                    deal_name: str,
                                    product: str,
                                    calculation_result: Dict[str, Any],
                                    calculation_params: Dict[str, Any],
                                    buyer_company_id: str = None,
                                    seller_company_id: str = None) -> Optional[str]:
        """
        Create a deal with buyer/seller associations
        """
        if not self.is_connected:
            st.warning("HubSpot not connected. Cannot create deal.")
            return None

        try:
            url = f"{self.base_url}/crm/v3/objects/deals"

            # Determine deal type and calculate contract value
            deal_type = "purchase" if "max_buy" in str(calculation_result) else "sale"
            quantity = calculation_params.get("quantity_t", 0)

            if deal_type == "purchase":
                price_per_ton = calculation_result.get("max_buy_eur", 0)
            else:
                price_per_ton = calculation_result.get("min_sell_eur", 0)

            contract_value = price_per_ton * quantity

            # Create detailed description
            description = self._create_deal_description(
                product, calculation_result, calculation_params, deal_type
            )

            # Prepare deal properties - using only essential HubSpot properties
            deal_properties = {
                "dealname": deal_name,
                "amount": str(int(contract_value))  # Ensure integer amount
            }

            # Add description with all our custom data
            if description:
                deal_properties["description"] = description

            payload = {"properties": deal_properties}

            response = requests.post(url, headers=self.headers, json=payload, timeout=15)

            if response.status_code != 201:
                # Show detailed error for debugging
                error_detail = ""
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_detail = f": {error_data['message']}"
                    elif "errors" in error_data:
                        error_detail = f": {error_data['errors']}"
                except:
                    error_detail = f": {response.text}"
                st.error(f"❌ Error creating deal (Status {response.status_code}){error_detail}")
                return None

            deal = response.json()
            deal_id = deal.get("id")

            # Associate with companies if provided
            if buyer_company_id:
                self._associate_deal_with_company(deal_id, buyer_company_id, "buyer")

            if seller_company_id:
                self._associate_deal_with_company(deal_id, seller_company_id, "seller")

            st.success(f"✅ Deal created successfully! ID: {deal_id}")
            return deal_id

        except Exception as e:
            st.error(f"❌ Error creating deal: {str(e)}")
            return None

    def _create_deal_description(self, product: str, result: Dict, params: Dict, deal_type: str) -> str:
        """Create detailed deal description"""

        description_parts = [
            f"Product: {product}",
            f"Type: {deal_type.title()}",
            f"Quantity: {params.get('quantity_t', 0):.0f} tons",
            "",
            "=== P&L SUMMARY ===",
        ]

        if deal_type == "purchase":
            description_parts.extend([
                f"Market Price: €{params.get('market_price_eur', 0):,.2f}/t",
                f"Max Buy Price: €{result.get('max_buy_eur', 0):,.2f}/t",
                f"Max Buy Price (USD): ${result.get('max_buy_usd', 0):,.2f}/t",
            ])
        else:
            description_parts.extend([
                f"Supplier Price: ${params.get('supplier_price_usd', 0):,.2f}/t",
                f"Min Sell Price: €{result.get('min_sell_eur', 0):,.2f}/t",
                f"Min Sell Price (USD): ${result.get('min_sell_usd', 0):,.2f}/t",
            ])

        description_parts.extend([
            "",
            "=== PROFITABILITY ===",
            f"Target Profit: €{result.get('profit_per_ton', 0):,.2f}/t",
            f"Total Profit: €{result.get('total_profit', 0):,.2f}",
            f"Margin: {result.get('margin_pct', 0):.2f}%",
            "",
            "=== COSTS ===",
            f"Transport: ${params.get('transport_usd', 0):.2f}/t",
            f"Broker: €{params.get('broker_eur', 0):.2f}/t",
            f"Customs: €{params.get('customs_eur', 0):.2f}/t",
            f"Expected Loss: {params.get('loss_kg', 0):.0f} kg/truck",
            "",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Generated by DARALEX P&L Calculator"
        ])

        return "\n".join(description_parts)

    def _associate_deal_with_company(self, deal_id: str, company_id: str, role: str):
        """Associate deal with company"""
        try:
            url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}/associations/companies/{company_id}/deal_to_company"
            response = requests.put(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            st.warning(f"Could not associate deal with {role} company: {str(e)}")

    def get_recent_deals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent deals for display in Streamlit
        """
        if not self.is_connected:
            return []

        try:
            url = f"{self.base_url}/crm/v3/objects/deals"
            params = {
                "limit": limit,
                "properties": "dealname,amount,dealstage,pipeline,createdate,description",
                "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}]
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("results", [])

        except Exception as e:
            st.error(f"Error fetching deals: {str(e)}")
            return []

    def create_deal_from_calculation(self,
                                   deal_name: str,
                                   calculation_result: Dict[str, Any],
                                   calculation_params: Dict[str, Any]) -> Optional[str]:
        """
        Create a new HubSpot deal from P&L calculation
        """
        if not self.is_connected:
            st.warning("HubSpot not connected. Cannot create deal.")
            return None

        try:
            url = f"{self.base_url}/crm/v3/objects/deals"

            # Determine deal type
            deal_type = "purchase" if "max_buy" in str(calculation_result) else "sale"

            # Prepare deal properties
            deal_properties = {
                "dealname": deal_name,
                "deal_type": deal_type,
                "quantity_tons": str(calculation_params.get("quantity_t", 0)),
                "target_profit": str(calculation_params.get("target_profit_eur", 0)),
                "calculated_margin": str(calculation_result.get("margin_pct", 0)),
                "calculated_profit": str(calculation_result.get("total_profit", 0)),
                "eur_usd_rate": str(calculation_params.get("eur_usd", 0)),
                "eur_mdl_rate": str(calculation_params.get("eur_mdl", 0)),
                "transport_cost": str(calculation_params.get("transport_usd", 0)),
                "broker_commission": str(calculation_params.get("broker_eur", 0)),
                "customs_cost": str(calculation_params.get("customs_eur", 0)),
                "calculation_timestamp": datetime.now().isoformat(),
                "source": "DARALEX_PNL_Calculator"
            }

            # Add calculation-specific properties
            if deal_type == "purchase":
                deal_properties.update({
                    "market_price_eur": str(calculation_params.get("market_price_eur", 0)),
                    "max_buy_price_eur": str(calculation_result.get("max_buy_eur", 0)),
                    "max_buy_price_usd": str(calculation_result.get("max_buy_usd", 0))
                })
            else:
                deal_properties.update({
                    "supplier_price_usd": str(calculation_params.get("supplier_price_usd", 0)),
                    "min_sell_price_eur": str(calculation_result.get("min_sell_eur", 0)),
                    "min_sell_price_usd": str(calculation_result.get("min_sell_usd", 0))
                })

            payload = {"properties": deal_properties}

            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()

            deal = response.json()
            deal_id = deal.get("id")

            st.success(f"✅ Deal created successfully! ID: {deal_id}")
            return deal_id

        except Exception as e:
            st.error(f"❌ Error creating deal: {str(e)}")
            return None

    def save_calculation_to_hubspot(self,
                                   calculation_result: Dict[str, Any],
                                   calculation_params: Dict[str, Any],
                                   deal_name: str = None) -> bool:
        """
        Save current P&L calculation to HubSpot
        """
        if not deal_name:
            calculation_type = calculation_params.get("calculation_type", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            deal_name = f"PnL_{calculation_type}_{timestamp}"

        deal_id = self.create_deal_from_calculation(deal_name, calculation_result, calculation_params)
        return deal_id is not None

def display_hubspot_status():
    """
    Display HubSpot connection status in Streamlit sidebar
    """
    hubspot = StreamlitHubSpotIntegration()

    with st.sidebar:
        st.markdown("---")
        st.subheader("🔗 HubSpot Integration")

        if hubspot.is_connected:
            # Test connection
            with st.spinner("Testing HubSpot connection..."):
                status = hubspot.test_connection()

            if status["connected"]:
                st.success("✅ Connected")
                st.metric("Total Deals", status.get("total_deals", "Unknown"))

                # Show recent deals
                if st.checkbox("Show Recent Deals"):
                    deals = hubspot.get_recent_deals(5)
                    if deals:
                        st.write("**Recent Deals:**")
                        for deal in deals[:3]:
                            props = deal.get("properties", {})
                            deal_name = props.get("dealname", "Unnamed Deal")
                            amount = props.get("amount", "No amount")
                            st.write(f"• {deal_name[:30]}...")
                    else:
                        st.write("No deals found")

                return True
            else:
                st.error(f"❌ {status['message']}")
                return False
        else:
            st.warning("⚠️ Not Connected")
            st.info("Add HUBSPOT_ACCESS_TOKEN to secrets")
            return False

def render_company_selector(label: str, key_prefix: str, hubspot: StreamlitHubSpotIntegration, t: Dict[str, str] = None) -> Optional[str]:
    """
    Render company selector with 'Add New' option
    """
    if not hubspot.is_connected:
        st.warning("HubSpot not connected")
        return None

    # Load companies
    if f"{key_prefix}_companies" not in st.session_state:
        with st.spinner(f"Loading {label.lower()}s..."):
            companies = hubspot.get_companies()
            st.session_state[f"{key_prefix}_companies"] = companies

    companies = st.session_state[f"{key_prefix}_companies"]

    # Use translations if available
    if not t:
        t = {"add_new_company": "➕ Add New Company", "country": "Country"}

    # Prepare options
    company_options = [t.get("add_new_company", "➕ Add New Company")] + [f"{comp['name']} ({comp['country']})" for comp in companies]

    selected = st.selectbox(
        label,
        options=company_options,
        key=f"{key_prefix}_selector"
    )

    if selected == t.get("add_new_company", "➕ Add New Company"):
        # Show input for new company
        new_company_name = st.text_input(
            t.get(f"new_{key_prefix}_name", f"New {label} Name"),
            key=f"{key_prefix}_new_name",
            placeholder="Enter company name..."
        )

        new_company_country = st.selectbox(
            t.get("country", "Country"),
            ["Ukraine", "Romania", "Moldova", "Greece", "Poland", "Bulgaria", "Serbia", "Other"],
            key=f"{key_prefix}_country"
        )

        if new_company_name:
            if st.button(t.get(f"create_{key_prefix}", f"Create {label}"), key=f"{key_prefix}_create"):
                company_id = hubspot.create_company(new_company_name, new_company_country)
                if company_id:
                    # Refresh companies list
                    del st.session_state[f"{key_prefix}_companies"]
                    st.rerun()
                return company_id
        return None
    else:
        # Find selected company ID
        company_name = selected.split(" (")[0]  # Remove country part
        for comp in companies:
            if comp['name'] == company_name:
                return comp['id']
        return None

def render_product_selector(t: Dict[str, str] = None) -> str:
    """
    Render product dropdown selector
    """
    products = [
        "Sunflower Oil (SFO)",
        "Soybean Oil (SBO)",
        "Rapeseed Oil (RSO)",
        "Sunflower Oil Crude",
        "Soybean Oil Crude"
    ]

    if not t:
        t = {"product_type": "🌻 Product Type"}

    return st.selectbox(
        t.get("product_type", "🌻 Product Type"),
        products,
        key="product_selector"
    )

def render_deal_tracking_section(calculation_result: Dict[str, Any],
                                calculation_params: Dict[str, Any],
                                t: Dict[str, str] = None):
    """
    Render the enhanced deal tracking section
    """
    hubspot = StreamlitHubSpotIntegration()

    if not t:
        t = {
            "deal_tracking": "Deal Tracking",
            "product_type": "🌻 Product Type",
            "select_buyer": "Select Buyer",
            "select_seller": "Select Seller",
            "deal_name": "Deal Name",
            "save_deal": "💾 Save Deal to HubSpot",
            "refresh_companies": "🔄 Refresh Companies"
        }

    if not hubspot.is_connected:
        st.info("💡 Connect HubSpot to enable deal tracking")
        return

    # Product selection
    product = render_product_selector(t)

    # Company selection
    col_buyer, col_seller = st.columns(2)

    with col_buyer:
        buyer_id = render_company_selector(t.get("select_buyer", "Select Buyer"), "buyer", hubspot, t)

    with col_seller:
        seller_id = render_company_selector(t.get("select_seller", "Select Seller"), "seller", hubspot, t)

    # Deal creation
    deal_name_default = ""
    if product and calculation_params.get("quantity_t"):
        quantity = calculation_params.get("quantity_t", 0)
        buyer_name = "TBD" if not buyer_id else "Buyer"
        seller_name = "TBD" if not seller_id else "Seller"
        deal_name_default = f"{product} - {seller_name} → {buyer_name} - {quantity:.0f}t"

    deal_name = st.text_input(
        t.get("deal_name", "Deal Name"),
        value=deal_name_default,
        key="deal_tracking_name"
    )

    col_save, col_refresh = st.columns(2)

    with col_save:
        if st.button(t.get("save_deal", "💾 Save Deal to HubSpot"), key="save_deal_tracking", type="primary"):
            if deal_name and product:
                deal_id = hubspot.create_deal_with_associations(
                    deal_name=deal_name,
                    product=product,
                    calculation_result=calculation_result,
                    calculation_params=calculation_params,
                    buyer_company_id=buyer_id,
                    seller_company_id=seller_id
                )
                if deal_id:
                    st.balloons()
                    # Refresh deals list
                    if "recent_deals" in st.session_state:
                        del st.session_state["recent_deals"]
            else:
                st.warning("Please select product and enter deal name")

    with col_refresh:
        if st.button(t.get("refresh_companies", "🔄 Refresh Companies"), key="refresh_companies"):
            # Clear cached companies
            keys_to_clear = [k for k in st.session_state.keys() if "_companies" in k]
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()

def render_deals_log(hubspot: StreamlitHubSpotIntegration, t: Dict[str, str] = None):
    """
    Render recent deals log table
    """
    if not hubspot.is_connected:
        return

    if not t:
        t = {
            "refresh_deals": "🔄 Refresh Deals",
            "no_deals": "No recent deals found.",
            "date": "Date",
            "product": "Product",
            "deal": "Deal",
            "quantity": "Quantity",
            "profit": "Profit",
            "margin": "Margin",
            "stage": "Stage"
        }

    # Load deals if not cached
    if "recent_deals" not in st.session_state:
        with st.spinner("Loading recent deals..."):
            deals = hubspot.get_recent_deals(20)
            st.session_state["recent_deals"] = deals

    deals = st.session_state["recent_deals"]

    if not deals:
        st.info(t.get("no_deals", "No recent deals found."))
        return

    # Prepare table data
    table_data = []
    for deal in deals:
        props = deal.get("properties", {})

        # Parse date
        created_date = props.get("createdate", "")
        if created_date:
            try:
                date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                date_str = date_obj.strftime("%Y-%m-%d")
            except:
                date_str = created_date[:10]
        else:
            date_str = "Unknown"

        # Extract data from description if available
        description = props.get("description", "") or ""
        product = "N/A"
        quantity = "N/A"
        profit = "N/A"

        # Simple parsing of description for display
        if description and "Product:" in description:
            try:
                product = description.split("Product: ")[1].split("\n")[0]
            except:
                pass

        if description and "Quantity:" in description:
            try:
                quantity = description.split("Quantity: ")[1].split(" tons")[0] + "t"
            except:
                pass

        if description and "Total Profit:" in description:
            try:
                profit = description.split("Total Profit: ")[1].split("\n")[0]
            except:
                pass

        table_data.append({
            t.get("date", "Date"): date_str,
            t.get("product", "Product"): product,
            t.get("deal", "Deal"): (props.get("dealname", "Unnamed Deal") or "Unnamed Deal")[:40] + ("..." if len(props.get("dealname", "") or "") > 40 else ""),
            t.get("quantity", "Quantity"): quantity,
            t.get("profit", "Profit"): profit,
            t.get("margin", "Margin"): f"€{float(props.get('amount', 0) or 0):,.0f}",
            t.get("stage", "Stage"): (props.get("dealstage", "unknown") or "unknown").replace("_", " ").title()
        })

    # Display table
    if table_data:
        import pandas as pd
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button(t.get("refresh_deals", "🔄 Refresh Deals"), key="refresh_deals"):
            del st.session_state["recent_deals"]
            st.rerun()

def add_hubspot_save_option(calculation_result: Dict[str, Any],
                           calculation_params: Dict[str, Any]):
    """
    Add option to save calculation to HubSpot (legacy function - replaced by deal tracking)
    """
    hubspot = StreamlitHubSpotIntegration()

    if not hubspot.is_connected:
        return

    with st.expander("💾 Quick Save to HubSpot"):
        deal_name = st.text_input(
            "Deal Name",
            value=f"PnL Calculation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            key="hubspot_deal_name"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Quick Save", key="save_hubspot"):
                if deal_name:
                    success = hubspot.save_calculation_to_hubspot(
                        calculation_result,
                        calculation_params,
                        deal_name
                    )
                    if success:
                        st.balloons()
                else:
                    st.warning("Please enter a deal name")

        with col2:
            if st.button("🔄 Refresh Connection", key="refresh_hubspot"):
                st.rerun()