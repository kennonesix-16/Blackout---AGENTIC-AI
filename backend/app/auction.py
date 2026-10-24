from __future__ import annotations

from .models import Order, TradeProposal, now_iso


def clear_market(orders: list[Order], tick: int) -> list[TradeProposal]:
    buys = sorted((o for o in orders if o.side == "buy"), key=lambda o: o.price_per_kwh, reverse=True)
    sells = sorted((o for o in orders if o.side == "sell"), key=lambda o: o.price_per_kwh)
    proposals: list[TradeProposal] = []
    buy_remaining = {order.id: order.quantity_kw for order in buys}
    sell_remaining = {order.id: order.quantity_kw for order in sells}
    for buy in buys:
        for sell in sells:
            remaining = sell_remaining[sell.id]
            buyer_remaining = buy_remaining[buy.id]
            if remaining <= 0 or buyer_remaining <= 0 or buy.price_per_kwh < sell.price_per_kwh:
                continue
            quantity = min(buyer_remaining, remaining)
            if quantity <= 0:
                continue
            # Transparent midpoint rule; this is a modeled clearing price, not a tariff.
            price = round((buy.price_per_kwh + sell.price_per_kwh) / 2, 3)
            proposals.append(
                TradeProposal(
                    trade_id=f"trade-{tick}-{len(proposals) + 1}",
                    buyer_id=buy.agent_type,
                    seller_id=sell.agent_type,
                    quantity_kw=quantity,
                    clearing_price=price,
                    buyer_node_id=buy.node_id,
                    seller_node_id=sell.node_id,
                    timestamp=now_iso(),
                )
            )
            buy_remaining[buy.id] -= quantity
            sell_remaining[sell.id] -= quantity
            if buy_remaining[buy.id] <= 0:
                break
    return proposals
