#!/usr/bin/env python3
"""
HubSpot Integration for Streamlit P&L Calculator
"""

import os
import requests
import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime
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
                "properties": "dealname,amount,dealstage,pipeline,price_per_ton,quantity_tons",
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

def add_hubspot_save_option(calculation_result: Dict[str, Any],
                           calculation_params: Dict[str, Any]):
    """
    Add option to save calculation to HubSpot
    """
    hubspot = StreamlitHubSpotIntegration()

    if not hubspot.is_connected:
        return

    with st.expander("💾 Save to HubSpot"):
        deal_name = st.text_input(
            "Deal Name",
            value=f"PnL Calculation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            key="hubspot_deal_name"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save to HubSpot", key="save_hubspot"):
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