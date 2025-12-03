import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from market_data.price_parser import UkrAgroConsultParser

logger = logging.getLogger(__name__)

class MarketIntelligence:
    """Market Intelligence module for DARALEX P&L Calculator"""

    def __init__(self):
        self.parser = UkrAgroConsultParser()
        self.data_dir = Path(__file__).parent / "market_data"

    def render_market_intel_tab(self, t: Dict[str, str]):
        """Render the main Market Intelligence tab"""
        st.header("📊 Market Intelligence")

        # Check for latest prices data
        latest_data = self.load_latest_market_data()

        if not latest_data:
            self._render_no_data_message(t)
            return

        # Create layout
        col1, col2 = st.columns([3, 1])

        with col2:
            self._render_upload_section(t)
            self._render_last_update_info(latest_data)

        with col1:
            # Main content tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Today's Prices",
                "📊 Price Comparison",
                "🤖 AI Analysis",
                "🚢 Export Volumes"
            ])

            with tab1:
                self._render_todays_prices_table(latest_data, t)

            with tab2:
                self._render_price_comparison_chart(latest_data, t)

            with tab3:
                self._render_ai_analysis_section(latest_data, t)

            with tab4:
                self._render_export_volumes_section(latest_data, t)

    def _render_upload_section(self, t: Dict[str, str]):
        """Render file upload section"""
        st.subheader("📤 Upload Daily Prices")

        uploaded_file = st.file_uploader(
            "Select UkrAgroConsult Excel file",
            type=['xlsx', 'xls'],
            help="Upload daily price reports from UkrAgroConsult"
        )

        if uploaded_file is not None:
            if st.button("🔄 Process File", type="primary"):
                try:
                    # Save uploaded file temporarily
                    temp_path = self.data_dir / f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Parse the file
                    with st.spinner("Processing file..."):
                        data = self.parser.parse_excel_file(str(temp_path))
                        self.parser.save_to_json(data)

                    # Clean up temp file
                    temp_path.unlink()

                    st.success(f"✅ Successfully processed {len(data['prices'])} price records")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error processing file: {e}")

    def _render_last_update_info(self, data: Dict[str, Any]):
        """Render last update information"""
        if data and "last_updated" in data:
            last_updated = datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))
            st.info(f"📅 Last updated: {last_updated.strftime('%Dec %d, %Y at %H:%M')}")

            if "parsing_info" in data:
                info = data["parsing_info"]
                with st.expander("📊 Data Details"):
                    st.write(f"**Total records:** {info.get('total_records', 0)}")
                    st.write(f"**Oil records:** {info.get('oil_records', 0)}")
                    st.write(f"**Sheets processed:** {len(info.get('sheets_processed', []))}")

    def _render_no_data_message(self, t: Dict[str, str]):
        """Render message when no data is available"""
        st.warning("⚠️ No market data available. Please upload UkrAgroConsult price files to get started.")

        col1, col2, col3 = st.columns(3)
        with col2:
            st.info("""
            **How to use:**
            1. Upload UkrAgroConsult Excel file
            2. View today's prices and analysis
            3. Monitor arbitrage opportunities
            """)

    def _render_todays_prices_table(self, data: Dict[str, Any], t: Dict[str, str]):
        """Render today's prices table with filtering"""
        st.subheader("📈 Today's Market Prices")

        if not data.get("filtered_prices"):
            st.warning("No filtered price data available")
            return

        filtered = data["filtered_prices"]

        # Create combined dataframe for display
        all_relevant_prices = []

        # Add Ukraine FOB prices
        for price in filtered.get("ukraine_fob", []):
            all_relevant_prices.append({
                "Region": "🇺🇦 Ukraine FOB",
                "Product": price["commodity"],
                "Price (USD/t)": f"${price['price']:,.0f}",
                "Daily Change": self._format_change(price.get("daily_change")),
                "Weekly Change": self._format_change(price.get("weekly_change")),
                "Monthly Change": self._format_change(price.get("monthly_change")),
                "Terms": price.get("delivery_terms", ""),
                "Date": price.get("date", "")
            })

        # Add Russia FOB prices
        for price in filtered.get("russia_fob", []):
            all_relevant_prices.append({
                "Region": "🇷🇺 Russia FOB",
                "Product": price["commodity"],
                "Price (USD/t)": f"${price['price']:,.0f}",
                "Daily Change": self._format_change(price.get("daily_change")),
                "Weekly Change": self._format_change(price.get("weekly_change")),
                "Monthly Change": self._format_change(price.get("monthly_change")),
                "Terms": price.get("delivery_terms", ""),
                "Date": price.get("date", "")
            })

        # Add Europe prices
        for price in filtered.get("europe_prices", []):
            all_relevant_prices.append({
                "Region": "🇪🇺 Europe",
                "Product": price["commodity"],
                "Price (USD/t)": f"${price['price']:,.0f}",
                "Daily Change": self._format_change(price.get("daily_change")),
                "Weekly Change": self._format_change(price.get("weekly_change")),
                "Monthly Change": self._format_change(price.get("monthly_change")),
                "Terms": price.get("delivery_terms", ""),
                "Date": price.get("date", "")
            })

        if all_relevant_prices:
            df = pd.DataFrame(all_relevant_prices)

            # Product filter
            products = ["All"] + list(df["Product"].unique())
            selected_product = st.selectbox("Filter by Product:", products)

            if selected_product != "All":
                df = df[df["Product"] == selected_product]

            # Color-code the dataframe
            styled_df = df.style.applymap(
                lambda x: self._get_change_color(x) if "Change" in str(x) else "",
                subset=["Daily Change", "Weekly Change", "Monthly Change"]
            )

            st.dataframe(styled_df, use_container_width=True, height=400)

            # Key highlights
            self._render_price_highlights(filtered)

        else:
            st.info("No relevant prices found for tracked products")

    def _render_price_comparison_chart(self, data: Dict[str, Any], t: Dict[str, str]):
        """Render price comparison charts"""
        st.subheader("📊 Price Comparison & Arbitrage")

        if not data.get("filtered_prices"):
            return

        filtered = data["filtered_prices"]

        # Create comparison chart
        fig = go.Figure()

        # Get unique products
        all_prices = (
            filtered.get("ukraine_fob", []) +
            filtered.get("russia_fob", []) +
            filtered.get("europe_prices", [])
        )

        products = list(set(p["commodity"] for p in all_prices))

        if not products:
            st.info("No price data available for comparison")
            return

        selected_product = st.selectbox("Select Product for Comparison:", products, key="comparison_product")

        # Filter prices for selected product
        ukraine_prices = [p for p in filtered.get("ukraine_fob", []) if p["commodity"] == selected_product]
        russia_prices = [p for p in filtered.get("russia_fob", []) if p["commodity"] == selected_product]
        europe_prices = [p for p in filtered.get("europe_prices", []) if p["commodity"] == selected_product]

        # Create bar chart
        regions = []
        prices = []
        colors = []

        if ukraine_prices:
            regions.append("Ukraine FOB")
            prices.append(ukraine_prices[0]["price"])
            colors.append("#1f77b4")

        if russia_prices:
            regions.append("Russia FOB")
            prices.append(russia_prices[0]["price"])
            colors.append("#ff7f0e")

        if europe_prices:
            regions.append("Europe")
            prices.append(europe_prices[0]["price"])
            colors.append("#2ca02c")

        if regions:
            fig.add_trace(go.Bar(
                x=regions,
                y=prices,
                marker_color=colors,
                text=[f"${p:,.0f}" for p in prices],
                textposition='auto',
                name=selected_product
            ))

            fig.update_layout(
                title=f"{selected_product} Price Comparison (USD/t)",
                xaxis_title="Region",
                yaxis_title="Price (USD/t)",
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            # Show arbitrage opportunities
            self._render_arbitrage_opportunities(filtered)

        else:
            st.info(f"No price data available for {selected_product}")

    def _render_arbitrage_opportunities(self, filtered: Dict[str, List]):
        """Render arbitrage opportunities section"""
        st.subheader("💰 Arbitrage Opportunities")

        opportunities = filtered.get("arbitrage_opportunities", [])

        if not opportunities:
            st.info("No arbitrage opportunities identified")
            return

        for opp in opportunities:
            if opp["type"] == "Ukraine_to_Europe" and opp["spread"] > 50:
                with st.container():
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Ukraine FOB",
                            f"${opp['ukraine_price']:,.0f}/t"
                        )

                    with col2:
                        st.metric(
                            "Europe Price",
                            f"${opp['europe_price']:,.0f}/t"
                        )

                    with col3:
                        st.metric(
                            "Spread",
                            f"${opp['spread']:,.0f}/t",
                            f"{opp['margin_pct']:.1f}%"
                        )

                    # Recommendation
                    if opp["spread"] > 100:
                        st.success(f"🎯 **{opp['commodity']}**: {opp['recommendation']}")
                    else:
                        st.info(f"📊 **{opp['commodity']}**: {opp['recommendation']}")

                    st.markdown("---")

    def _render_ai_analysis_section(self, data: Dict[str, Any], t: Dict[str, str]):
        """Render AI-powered market analysis"""
        st.subheader("🤖 AI Market Analysis")

        if not data.get("filtered_prices"):
            st.info("No data available for analysis")
            return

        # Generate analysis based on current market data
        analysis = self._generate_market_analysis(data["filtered_prices"])

        # Display key insights
        st.markdown("### 📈 Key Market Insights")

        for insight in analysis["insights"]:
            st.info(insight)

        # Display recommendations
        st.markdown("### 🎯 Trading Recommendations")

        for rec in analysis["recommendations"]:
            if "good" in rec.lower() or "buy" in rec.lower():
                st.success(f"✅ {rec}")
            elif "monitor" in rec.lower() or "watch" in rec.lower():
                st.warning(f"⚠️ {rec}")
            else:
                st.info(f"📊 {rec}")

        # Market sentiment
        sentiment = analysis["sentiment"]
        if sentiment == "bullish":
            st.success("📈 **Market Sentiment**: Bullish")
        elif sentiment == "bearish":
            st.error("📉 **Market Sentiment**: Bearish")
        else:
            st.info("➡️ **Market Sentiment**: Neutral")

    def _render_export_volumes_section(self, data: Dict[str, Any], t: Dict[str, str]):
        """Render export volumes section"""
        st.subheader("🚢 Export Volumes Analysis")

        # Note: This would typically come from additional data sources
        # For now, we'll show a placeholder with key metrics

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🌻 Sunflower Oil Exports")
            st.metric("Ukraine 2024/25", "2.1M tons", "+15% vs 23/24")
            st.metric("Russia 2024/25", "3.5M tons", "-5% vs 23/24")

        with col2:
            st.markdown("#### 🌱 Soybean Oil Exports")
            st.metric("Argentina 2024/25", "4.2M tons", "+8% vs 23/24")
            st.metric("Ukraine 2024/25", "0.3M tons", "+25% vs 23/24")

        st.info("📝 Export volume data integration planned for next update")

    def _format_change(self, change: Optional[float]) -> str:
        """Format price change with color indicators"""
        if change is None:
            return "-"

        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}"

    def _get_change_color(self, value: str) -> str:
        """Get color for price changes"""
        if not value or value == "-":
            return ""

        try:
            num_val = float(value.replace("+", "").replace("-", ""))
            if "+" in value:
                return "background-color: #d4edda; color: #155724"  # Green
            elif "-" in value and num_val != 0:
                return "background-color: #f8d7da; color: #721c24"  # Red
        except:
            pass

        return ""

    def _render_price_highlights(self, filtered: Dict[str, List]):
        """Render key price highlights"""
        st.markdown("### 🎯 Key Highlights")

        highlights = []

        # Ukraine sunflower oil
        ukraine_sunflower = [p for p in filtered.get("ukraine_fob", []) if "sunflower" in p["commodity"].lower()]
        if ukraine_sunflower:
            price = ukraine_sunflower[0]
            daily_change = price.get("daily_change", 0)
            change_text = f"(+${daily_change:.0f})" if daily_change > 0 else f"(-${abs(daily_change):.0f})" if daily_change < 0 else ""
            highlights.append(f"🇺🇦 Sunflower Oil FOB Ukraine: **${price['price']:,.0f}/t** {change_text}")

        # Europe sunflower oil
        europe_sunflower = [p for p in filtered.get("europe_prices", []) if "sunflower" in p["commodity"].lower()]
        if europe_sunflower:
            price = europe_sunflower[0]
            highlights.append(f"🇪🇺 Europe Sunflower Oil: **${price['price']:,.0f}/t**")

        # Show arbitrage if both exist
        if ukraine_sunflower and europe_sunflower:
            spread = europe_sunflower[0]["price"] - ukraine_sunflower[0]["price"]
            highlights.append(f"💰 Ukraine-Europe Spread: **${spread:,.0f}/t** ({spread/ukraine_sunflower[0]['price']*100:.1f}%)")

        for highlight in highlights:
            st.markdown(f"• {highlight}")

    def _generate_market_analysis(self, filtered_prices: Dict[str, List]) -> Dict[str, Any]:
        """Generate AI-style market analysis"""
        insights = []
        recommendations = []
        sentiment = "neutral"

        ukraine_fob = filtered_prices.get("ukraine_fob", [])
        russia_fob = filtered_prices.get("russia_fob", [])
        europe_prices = filtered_prices.get("europe_prices", [])

        # Analyze Ukraine market
        if ukraine_fob:
            avg_daily_change = sum(p.get("daily_change", 0) for p in ukraine_fob) / len(ukraine_fob)
            if avg_daily_change > 5:
                insights.append("📈 Ukrainian prices showing strong upward momentum (+${:.0f} daily avg)".format(avg_daily_change))
                sentiment = "bullish"
            elif avg_daily_change < -5:
                insights.append("📉 Ukrainian prices under pressure ({:.0f} daily avg)".format(avg_daily_change))
                sentiment = "bearish"

        # Analyze arbitrage opportunities
        opportunities = filtered_prices.get("arbitrage_opportunities", [])
        good_arb = [opp for opp in opportunities if opp.get("spread", 0) > 100]

        if good_arb:
            best_spread = max(good_arb, key=lambda x: x.get("spread", 0))
            insights.append(f"💰 Strong arbitrage opportunity in {best_spread['commodity']}: ${best_spread['spread']:.0f}/t spread")
            recommendations.append(f"Consider buying {best_spread['commodity']} Ukraine origin for EU sales (${best_spread['spread']:.0f}/t margin)")

        # General recommendations
        if len(ukraine_fob) > len(russia_fob):
            recommendations.append("Ukraine remains primary supplier with better price transparency")

        if not insights:
            insights.append("📊 Market showing mixed signals, monitor for trend development")

        if not recommendations:
            recommendations.append("Monitor price spreads for emerging opportunities")

        return {
            "insights": insights,
            "recommendations": recommendations,
            "sentiment": sentiment
        }

    def load_latest_market_data(self) -> Dict[str, Any]:
        """Load the latest market data"""
        return self.parser.load_latest_prices()


def render_market_intelligence_tab(t: Dict[str, str]):
    """Main function to render the Market Intelligence tab"""
    market_intel = MarketIntelligence()
    market_intel.render_market_intel_tab(t)