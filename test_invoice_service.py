from invoice_service import Order, render_invoice


def test_invoice_total_is_visible_for_order_lines():
    order = Order("DT-7", "Test Buyer", "buyer@example.com", (("Compiler seat", 2, 1250), ("Support", 1, 500)))
    html = render_invoice(order)
    assert "Total: $30.00" in html
    assert "Compiler seat" in html
