#!/usr/bin/env python3
"""
Enhanced P&L Calculator for Vegetable Oil Trading
Integrates with existing Streamlit app
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class EnhancedPnLResult:
    """Enhanced P&L calculation result with more detailed metrics"""
    calculation_type: str

    # Primary outputs
    max_buy_usd: Optional[float] = None
    max_buy_eur: Optional[float] = None
    max_buy_mdl: Optional[float] = None
    max_buy_mdl_vat: Optional[float] = None

    min_sell_usd: Optional[float] = None
    min_sell_eur: Optional[float] = None
    min_sell_mdl: Optional[float] = None
    min_sell_mdl_vat: Optional[float] = None

    # Profit calculations
    profit_per_ton: float = 0.0
    profit_per_truck: float = 0.0
    total_profit: float = 0.0
    margin_pct: float = 0.0

    # Detailed breakdown
    transport_cost_eur: float = 0.0
    total_costs_per_ton: float = 0.0
    loss_adjustment_factor: float = 1.0
    effective_quantity_tons: float = 0.0

    # Additional metrics
    breakeven_price_eur: Optional[float] = None
    profit_margin_usd: Optional[float] = None
    cost_breakdown: Dict[str, float] = None

    def __post_init__(self):
        if self.cost_breakdown is None:
            self.cost_breakdown = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/JSON serialization"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

class EnhancedVegetableOilCalculator:
    """
    Enhanced P&L Calculator with improved accuracy and detailed breakdowns
    """

    def __init__(self):
        self.truck_capacity_tons = 24.0

    def calculate_enhanced_backwardation(self,
                                       market_price_eur: float,
                                       target_profit_eur: float,
                                       eur_usd: float,
                                       eur_mdl: float,
                                       transport_usd: float,
                                       loss_kg: float,
                                       broker_eur: float,
                                       customs_eur: float,
                                       quantity_t: float,
                                       vat_rate: float = 0.20) -> EnhancedPnLResult:
        """
        Enhanced backwardation calculation with detailed cost breakdown
        """
        # Convert transport cost to EUR
        transport_eur = transport_usd / eur_usd

        # Calculate loss adjustment factor
        loss_factor = 1 - (loss_kg / (self.truck_capacity_tons * 1000))
        effective_quantity = quantity_t * loss_factor

        # Build detailed cost breakdown
        cost_breakdown = {
            "transport_eur_per_ton": transport_eur,
            "broker_eur_per_ton": broker_eur,
            "customs_eur_per_ton": customs_eur,
            "target_profit_eur_per_ton": target_profit_eur,
            "loss_kg_per_truck": loss_kg,
            "loss_percentage": ((1 - loss_factor) * 100)
        }

        # Total costs per ton (excluding purchase price)
        total_costs_per_ton = transport_eur + broker_eur + customs_eur

        # Calculate max purchase price
        # Formula: Max Buy = (Market Price - Profit - Costs) / Loss Factor
        max_buy_eur_base = market_price_eur - target_profit_eur - total_costs_per_ton
        max_buy_eur = max_buy_eur_base / loss_factor if loss_factor > 0 else max_buy_eur_base

        # Convert to other currencies
        max_buy_usd = max_buy_eur * eur_usd
        max_buy_mdl = max_buy_eur * eur_mdl
        max_buy_mdl_vat = max_buy_mdl * (1 + vat_rate)

        # Calculate profits
        profit_per_ton = target_profit_eur
        profit_per_truck = profit_per_ton * self.truck_capacity_tons
        total_profit = profit_per_ton * quantity_t  # Use original quantity for total

        # Calculate margin (profit / total cost basis)
        total_cost_basis = max_buy_eur + total_costs_per_ton
        margin_pct = (profit_per_ton / total_cost_basis * 100) if total_cost_basis > 0 else 0

        # Breakeven price (price where profit = 0)
        breakeven_price_eur = max_buy_eur + total_costs_per_ton

        return EnhancedPnLResult(
            calculation_type="backwardation",
            max_buy_usd=round(max_buy_usd, 2),
            max_buy_eur=round(max_buy_eur, 2),
            max_buy_mdl=round(max_buy_mdl, 2),
            max_buy_mdl_vat=round(max_buy_mdl_vat, 2),
            profit_per_ton=round(profit_per_ton, 2),
            profit_per_truck=round(profit_per_truck, 2),
            total_profit=round(total_profit, 2),
            margin_pct=round(margin_pct, 2),
            transport_cost_eur=round(transport_eur, 2),
            total_costs_per_ton=round(total_costs_per_ton, 2),
            loss_adjustment_factor=round(loss_factor, 4),
            effective_quantity_tons=round(effective_quantity, 2),
            breakeven_price_eur=round(breakeven_price_eur, 2),
            cost_breakdown=cost_breakdown
        )

    def calculate_enhanced_forwardation(self,
                                      supplier_price_usd: float,
                                      target_profit_eur: float,
                                      eur_usd: float,
                                      eur_mdl: float,
                                      transport_usd: float,
                                      loss_kg: float,
                                      broker_eur: float,
                                      customs_eur: float,
                                      quantity_t: float,
                                      vat_rate: float = 0.20) -> EnhancedPnLResult:
        """
        Enhanced forwardation calculation with detailed cost breakdown
        """
        # Convert supplier price to EUR
        supplier_price_eur = supplier_price_usd / eur_usd
        transport_eur = transport_usd / eur_usd

        # Calculate loss adjustment factor
        loss_factor = 1 + (loss_kg / (self.truck_capacity_tons * 1000))
        effective_quantity = quantity_t / loss_factor

        # Build detailed cost breakdown
        cost_breakdown = {
            "supplier_price_eur_per_ton": supplier_price_eur,
            "transport_eur_per_ton": transport_eur,
            "broker_eur_per_ton": broker_eur,
            "customs_eur_per_ton": customs_eur,
            "target_profit_eur_per_ton": target_profit_eur,
            "loss_kg_per_truck": loss_kg,
            "loss_percentage": ((loss_factor - 1) * 100)
        }

        # Total costs per ton
        total_costs_per_ton = supplier_price_eur + transport_eur + broker_eur + customs_eur

        # Apply loss adjustment and add profit
        loss_adjusted_cost = total_costs_per_ton * loss_factor
        min_sell_eur = loss_adjusted_cost + target_profit_eur

        # Convert to other currencies
        min_sell_usd = min_sell_eur * eur_usd
        min_sell_mdl = min_sell_eur * eur_mdl
        min_sell_mdl_vat = min_sell_mdl * (1 + vat_rate)

        # Calculate profits
        profit_per_ton = target_profit_eur
        profit_per_truck = profit_per_ton * self.truck_capacity_tons
        total_profit = profit_per_ton * quantity_t  # Use original quantity

        # Calculate margin (profit / total cost basis)
        margin_pct = (profit_per_ton / loss_adjusted_cost * 100) if loss_adjusted_cost > 0 else 0

        # Breakeven price (price where profit = 0)
        breakeven_price_eur = loss_adjusted_cost

        return EnhancedPnLResult(
            calculation_type="forwardation",
            min_sell_usd=round(min_sell_usd, 2),
            min_sell_eur=round(min_sell_eur, 2),
            min_sell_mdl=round(min_sell_mdl, 2),
            min_sell_mdl_vat=round(min_sell_mdl_vat, 2),
            profit_per_ton=round(profit_per_ton, 2),
            profit_per_truck=round(profit_per_truck, 2),
            total_profit=round(total_profit, 2),
            margin_pct=round(margin_pct, 2),
            transport_cost_eur=round(transport_eur, 2),
            total_costs_per_ton=round(total_costs_per_ton, 2),
            loss_adjustment_factor=round(loss_factor, 4),
            effective_quantity_tons=round(effective_quantity, 2),
            breakeven_price_eur=round(breakeven_price_eur, 2),
            cost_breakdown=cost_breakdown
        )

    def quick_comparison(self, buy_price_eur: float, sell_price_eur: float,
                        transport_eur: float, broker_eur: float, customs_eur: float,
                        loss_kg: float = 0) -> Dict[str, float]:
        """
        Quick comparison of buy vs sell prices
        """
        total_costs = buy_price_eur + transport_eur + broker_eur + customs_eur

        # Apply loss adjustment if specified
        if loss_kg > 0:
            loss_factor = 1 + (loss_kg / (self.truck_capacity_tons * 1000))
            effective_sell_price = sell_price_eur / loss_factor
        else:
            effective_sell_price = sell_price_eur

        profit_per_ton = effective_sell_price - total_costs
        margin_pct = (profit_per_ton / total_costs * 100) if total_costs > 0 else 0

        return {
            'profit_per_ton': round(profit_per_ton, 2),
            'profit_per_truck': round(profit_per_ton * self.truck_capacity_tons, 2),
            'margin_pct': round(margin_pct, 2),
            'total_costs_per_ton': round(total_costs, 2),
            'effective_sell_price': round(effective_sell_price, 2),
            'breakeven_sell_price': round(total_costs, 2)
        }

    def sensitivity_analysis(self, base_calculation: EnhancedPnLResult,
                           price_variations: list = None) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on key parameters
        """
        if price_variations is None:
            price_variations = [-50, -25, -10, 0, 10, 25, 50]

        analysis = {
            'price_sensitivity': [],
            'profit_range': {'min': 0, 'max': 0},
            'margin_range': {'min': 0, 'max': 0}
        }

        base_price = (base_calculation.max_buy_eur or
                     base_calculation.min_sell_eur or 0)

        for variation in price_variations:
            adjusted_price = base_price + variation

            # Simplified sensitivity calculation
            profit_impact = variation if base_calculation.calculation_type == "backwardation" else -variation
            adjusted_profit = base_calculation.profit_per_ton + profit_impact
            adjusted_margin = (adjusted_profit / base_calculation.total_costs_per_ton * 100
                             if base_calculation.total_costs_per_ton > 0 else 0)

            analysis['price_sensitivity'].append({
                'price_change': variation,
                'adjusted_price': round(adjusted_price, 2),
                'profit_per_ton': round(adjusted_profit, 2),
                'margin_pct': round(adjusted_margin, 2)
            })

        # Calculate ranges
        profits = [item['profit_per_ton'] for item in analysis['price_sensitivity']]
        margins = [item['margin_pct'] for item in analysis['price_sensitivity']]

        analysis['profit_range'] = {'min': min(profits), 'max': max(profits)}
        analysis['margin_range'] = {'min': min(margins), 'max': max(margins)}

        return analysis