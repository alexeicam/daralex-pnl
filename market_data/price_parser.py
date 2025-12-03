import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UkrAgroConsultParser:
    """Parser for UkrAgroConsult Excel price reports"""

    # Products we track for DARALEX
    TRACKED_PRODUCTS = {
        "Sunflower Oil": ["Sunflower Oil", "Sunflower oil", "SUNFLOWER OIL", "SUN OIL"],
        "Soybean Oil": ["Soybean Oil", "Soybean oil", "SOYBEAN OIL", "SOY OIL"],
        "Rapeseed Oil": ["Rapeseed Oil", "Rapeseed oil", "RAPESEED OIL", "CANOLA OIL"],
        "Palm Oil": ["Palm Oil", "Palm oil", "PALM OIL"],
        "Rapeseed": ["Rapeseed", "RAPESEED", "Canola"]
    }

    # Key delivery terms and countries we monitor
    KEY_TERMS = {
        "Ukraine": ["Ukraine", "UA", "Ukrainian", "Odesa", "Chornomorsk", "Yuzhny"],
        "Russia": ["Russia", "RU", "Russian", "Novorossiysk", "Rostov"],
        "Europe": ["Europe", "EU", "Six ports", "ARA", "Rotterdam", "Hamburg"],
        "Argentina": ["Argentina", "AR", "Argentine", "Buenos Aires", "Up river"],
        "Malaysia": ["Malaysia", "MY", "Malaysian", "Peninsular Malaysia"]
    }

    DELIVERY_TERMS = ["FOB", "CPT", "CFR", "CIF", "EXW", "POC"]

    def __init__(self):
        self.data_dir = Path(__file__).parent
        self.latest_prices_file = self.data_dir / "latest_prices.json"

    def parse_excel_file(self, file_path: str) -> Dict[str, Any]:
        """Parse UkrAgroConsult Excel file and extract vegetable oil prices"""
        try:
            excel_file = pd.ExcelFile(file_path)
            all_prices = []
            parsing_info = {
                "file_path": file_path,
                "parsed_at": datetime.now().isoformat(),
                "sheets_processed": [],
                "total_records": 0,
                "oil_records": 0
            }

            logger.info(f"Processing Excel file: {file_path}")
            logger.info(f"Found sheets: {excel_file.sheet_names}")

            # Process each sheet (usually by date)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    sheet_prices = self._parse_sheet(df, sheet_name)
                    all_prices.extend(sheet_prices)

                    parsing_info["sheets_processed"].append({
                        "sheet": sheet_name,
                        "records": len(sheet_prices)
                    })

                    logger.info(f"Sheet '{sheet_name}': {len(sheet_prices)} oil price records")

                except Exception as e:
                    logger.warning(f"Failed to process sheet '{sheet_name}': {e}")
                    continue

            parsing_info["total_records"] = len(all_prices)
            parsing_info["oil_records"] = len([p for p in all_prices if self._is_tracked_oil(p["commodity"])])

            return {
                "prices": all_prices,
                "parsing_info": parsing_info,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {e}")
            raise

    def _parse_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
        """Parse individual sheet and extract price data"""
        prices = []

        # Try to infer date from sheet name
        sheet_date = self._extract_date_from_sheet_name(sheet_name)

        # Common column patterns in UkrAgroConsult files
        possible_columns = {
            "date": ["Date", "DATE", "date", "Дата"],
            "commodity": ["Commodity", "COMMODITY", "Product", "PRODUCT", "Товар"],
            "country": ["Country", "COUNTRY", "Origin", "ORIGIN", "Країна"],
            "delivery_terms": ["Delivery Terms", "DELIVERY TERMS", "Terms", "TERMS", "Умови поставки"],
            "price": ["Price", "PRICE", "USD/t", "USD/MT", "Ціна"],
            "change_daily": ["Change day", "Daily", "Day", "Зміна день"],
            "change_weekly": ["Change week", "Weekly", "Week", "Зміна тиждень"],
            "change_monthly": ["Change month", "Monthly", "Month", "Зміна місяць"],
            "change_yearly": ["Change year", "Yearly", "Year", "Зміна рік"]
        }

        # Map columns
        column_mapping = {}
        for col_type, possible_names in possible_columns.items():
            for col in df.columns:
                if any(name.lower() in str(col).lower() for name in possible_names):
                    column_mapping[col_type] = col
                    break

        logger.info(f"Column mapping for sheet '{sheet_name}': {column_mapping}")

        # Process each row
        for idx, row in df.iterrows():
            try:
                # Extract commodity name
                commodity = str(row.get(column_mapping.get("commodity", ""), "")).strip()
                if not commodity or commodity in ["nan", "None", ""]:
                    continue

                # Only process if it's a tracked oil product
                if not self._is_tracked_oil(commodity):
                    continue

                # Extract price
                price_col = column_mapping.get("price")
                if price_col is None:
                    continue

                price = row.get(price_col)
                if pd.isna(price) or price == 0:
                    continue

                # Clean and convert price
                try:
                    if isinstance(price, str):
                        price = price.replace(",", "").replace("$", "").replace("€", "").strip()
                    price = float(price)
                except (ValueError, TypeError):
                    continue

                # Extract other fields
                country = self._clean_text(row.get(column_mapping.get("country", ""), ""))
                delivery_terms = self._clean_text(row.get(column_mapping.get("delivery_terms", ""), ""))

                # Extract date
                date_value = row.get(column_mapping.get("date"))
                if pd.isna(date_value):
                    date_value = sheet_date

                if isinstance(date_value, str):
                    try:
                        date_value = pd.to_datetime(date_value).date()
                    except:
                        date_value = sheet_date
                elif hasattr(date_value, 'date'):
                    date_value = date_value.date()
                else:
                    date_value = sheet_date

                # Extract price changes
                changes = {}
                for period in ["daily", "weekly", "monthly", "yearly"]:
                    change_col = column_mapping.get(f"change_{period}")
                    if change_col:
                        try:
                            change = row.get(change_col)
                            if not pd.isna(change):
                                if isinstance(change, str):
                                    change = change.replace("+", "").replace("$", "").replace(",", "").strip()
                                changes[f"{period}_change"] = float(change)
                        except (ValueError, TypeError):
                            pass

                # Create price record
                price_record = {
                    "date": date_value.isoformat() if date_value else None,
                    "commodity": self._normalize_commodity_name(commodity),
                    "country": country,
                    "delivery_terms": delivery_terms,
                    "price": price,
                    "currency": "USD",  # UkrAgroConsult usually quotes in USD
                    **changes,
                    "source_sheet": sheet_name,
                    "source_row": idx + 1
                }

                prices.append(price_record)

            except Exception as e:
                logger.warning(f"Failed to process row {idx} in sheet '{sheet_name}': {e}")
                continue

        return prices

    def _extract_date_from_sheet_name(self, sheet_name: str) -> Optional[datetime]:
        """Try to extract date from sheet name"""
        import re

        # Common date patterns in sheet names
        date_patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # DD.MM.YYYY
            r"(\d{4})-(\d{1,2})-(\d{1,2})",   # YYYY-MM-DD
            r"(\d{1,2})/(\d{1,2})/(\d{4})",   # MM/DD/YYYY
            r"(\d{1,2})-(\d{1,2})-(\d{4})",   # DD-MM-YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, sheet_name)
            if match:
                try:
                    if "." in pattern or "-" in pattern and len(match.group(1)) <= 2:
                        # DD.MM.YYYY or DD-MM-YYYY
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    elif "/" in pattern:
                        # MM/DD/YYYY
                        month, day, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    else:
                        # YYYY-MM-DD
                        year, month, day = match.groups()
                        return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue

        return datetime.now().date()

    def _is_tracked_oil(self, commodity: str) -> bool:
        """Check if commodity is one of our tracked oil products"""
        commodity_lower = commodity.lower()
        for product_group in self.TRACKED_PRODUCTS.values():
            if any(tracked.lower() in commodity_lower for tracked in product_group):
                return True
        return False

    def _normalize_commodity_name(self, commodity: str) -> str:
        """Normalize commodity name to standard format"""
        commodity_lower = commodity.lower()

        for standard_name, variations in self.TRACKED_PRODUCTS.items():
            if any(var.lower() in commodity_lower for var in variations):
                return standard_name

        return commodity

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text fields"""
        if pd.isna(text):
            return ""
        return str(text).strip()

    def filter_relevant_prices(self, all_prices: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Filter prices by relevance for DARALEX business"""

        filtered = {
            "ukraine_fob": [],
            "russia_fob": [],
            "europe_prices": [],
            "argentina_prices": [],
            "malaysia_palm": [],
            "arbitrage_opportunities": []
        }

        for price in all_prices:
            commodity = price["commodity"]
            country = price["country"].lower()
            terms = price["delivery_terms"].lower()

            # Ukraine FOB prices
            if any(term in country for term in ["ukraine", "ua", "odesa", "chornomorsk"]) and "fob" in terms:
                filtered["ukraine_fob"].append(price)

            # Russia FOB prices
            elif any(term in country for term in ["russia", "ru", "novorossiysk"]) and "fob" in terms:
                filtered["russia_fob"].append(price)

            # Europe prices
            elif any(term in country for term in ["europe", "eu", "rotterdam", "hamburg", "six ports"]):
                filtered["europe_prices"].append(price)

            # Argentina prices
            elif any(term in country for term in ["argentina", "ar", "buenos aires"]):
                filtered["argentina_prices"].append(price)

            # Malaysia palm oil
            elif "malaysia" in country and "palm oil" in commodity.lower():
                filtered["malaysia_palm"].append(price)

        # Calculate arbitrage opportunities
        filtered["arbitrage_opportunities"] = self._calculate_arbitrage_opportunities(
            filtered["ukraine_fob"],
            filtered["russia_fob"],
            filtered["europe_prices"]
        )

        return filtered

    def _calculate_arbitrage_opportunities(self, ukraine_prices: List[Dict],
                                        russia_prices: List[Dict],
                                        europe_prices: List[Dict]) -> List[Dict[str, Any]]:
        """Calculate potential arbitrage opportunities"""
        opportunities = []

        # Ukraine vs Europe spreads
        for ua_price in ukraine_prices:
            for eu_price in europe_prices:
                if ua_price["commodity"] == eu_price["commodity"]:
                    spread = eu_price["price"] - ua_price["price"]
                    if spread > 50:  # Minimum viable spread
                        opportunities.append({
                            "type": "Ukraine_to_Europe",
                            "commodity": ua_price["commodity"],
                            "ukraine_price": ua_price["price"],
                            "europe_price": eu_price["price"],
                            "spread": spread,
                            "margin_pct": (spread / ua_price["price"]) * 100,
                            "recommendation": "Consider buying Ukraine origin for EU sales" if spread > 100 else "Monitor spread"
                        })

        # Ukraine vs Russia comparison
        for ua_price in ukraine_prices:
            for ru_price in russia_prices:
                if ua_price["commodity"] == ru_price["commodity"]:
                    spread = ua_price["price"] - ru_price["price"]
                    opportunities.append({
                        "type": "Ukraine_vs_Russia",
                        "commodity": ua_price["commodity"],
                        "ukraine_price": ua_price["price"],
                        "russia_price": ru_price["price"],
                        "ukraine_premium": spread,
                        "competitive_status": "Competitive" if abs(spread) < 25 else "Premium" if spread > 0 else "Discount"
                    })

        return opportunities

    def save_to_json(self, data: Dict[str, Any], file_path: Optional[str] = None) -> None:
        """Save parsed data to JSON file"""
        if file_path is None:
            file_path = self.latest_prices_file

        # Create summary for the JSON file
        output_data = {
            "last_updated": data["last_updated"],
            "parsing_info": data["parsing_info"],
            "filtered_prices": self.filter_relevant_prices(data["prices"]),
            "raw_prices": data["prices"],
            "summary": self._create_summary(data["prices"])
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Saved parsed data to {file_path}")

    def _create_summary(self, prices: List[Dict]) -> Dict[str, Any]:
        """Create summary statistics"""
        if not prices:
            return {}

        summary = {
            "total_records": len(prices),
            "unique_commodities": len(set(p["commodity"] for p in prices)),
            "unique_countries": len(set(p["country"] for p in prices if p["country"])),
            "date_range": {
                "earliest": min(p["date"] for p in prices if p["date"]),
                "latest": max(p["date"] for p in prices if p["date"])
            },
            "commodities": {}
        }

        # Commodity breakdown
        for commodity in set(p["commodity"] for p in prices):
            commodity_prices = [p for p in prices if p["commodity"] == commodity]
            if commodity_prices:
                prices_values = [p["price"] for p in commodity_prices if p["price"]]
                if prices_values:
                    summary["commodities"][commodity] = {
                        "count": len(commodity_prices),
                        "price_range": {
                            "min": min(prices_values),
                            "max": max(prices_values),
                            "avg": sum(prices_values) / len(prices_values)
                        }
                    }

        return summary

    def load_latest_prices(self) -> Dict[str, Any]:
        """Load the latest prices from JSON file"""
        if self.latest_prices_file.exists():
            with open(self.latest_prices_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


# Example usage
if __name__ == "__main__":
    parser = UkrAgroConsultParser()

    # Example: Parse an Excel file
    # data = parser.parse_excel_file("path/to/ukragroconsult_prices.xlsx")
    # parser.save_to_json(data)

    print("UkrAgroConsult Parser initialized successfully")
    print(f"Data directory: {parser.data_dir}")
    print(f"Tracked products: {list(parser.TRACKED_PRODUCTS.keys())}")