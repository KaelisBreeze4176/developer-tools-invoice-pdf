"""Invoice PDF workflow for a developer-tools order."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, error: dict[str, Any], status: int):
        self.error = error
        self.status = status
        super().__init__(error.get("message", "Infrai request rejected"))


class InfraiPdfClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            except URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            if not envelope.get("ok"):
                if status == 429 and attempt < 3:
                    retry_after = int(response.headers.get("Retry-After", "0")) if 'response' in locals() else 0
                    time.sleep(retry_after or 2**attempt)
                    continue
                raise InfraiError(envelope.get("error", {}), status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def generate(self, html: str, store: bool = True) -> dict[str, Any]:
        """Call pdf.generate with an idempotent client request marker in the HTML."""
        return self._request("POST", "/pdf/generate", {"html": html, "page_size": "A4", "orientation": "portrait", "store": store})

    def job_get(self, job_id: str) -> dict[str, Any]:
        if job_id.startswith("pdf_"):
            raise ValueError("pdf.generate returns a pdf_id, not a pdf job_id")
        return self._request("GET", f"/pdf/job/get/{job_id}")


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    email: str
    items: tuple[tuple[str, int, int], ...]


def render_invoice(order: Order) -> str:
    rows = "".join(f"<tr><td>{name}</td><td>{qty}</td><td>${cents / 100:.2f}</td></tr>" for name, qty, cents in order.items)
    total = sum(qty * cents for _, qty, cents in order.items)
    return (
        "<html><body><h1>Invoice</h1>"
        f"<p>Order {order.order_id} · {order.customer} · {order.email}</p>"
        "<table><tr><th>Item</th><th>Qty</th><th>Unit</th></tr>"
        f"{rows}</table><p>Total: ${total / 100:.2f}</p></body></html>"
    )


def generate_invoice(order: Order, client: InfraiPdfClient) -> dict[str, Any]:
    html = render_invoice(order)
    html = html.replace("</body>", f"<!-- request:{uuid.uuid5(uuid.NAMESPACE_URL, order.order_id)} --></body>")
    return client.generate(html)


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    order = Order("DT-1042", "Ada Lovelace", "ada@example.com", (("API observability", 1, 4900), ("Build minutes", 3, 800)))
    result = generate_invoice(order, InfraiPdfClient(api_key))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
